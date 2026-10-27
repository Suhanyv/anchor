"""
Agent：三版候选（C）＋ 定向修补（B）

为什么这样组合
--------------
C（多方案自评）单独用会变成"它给自己打分"——它没有品味，
本地 3B 那轮已经证明：模型给的"好/不好"是假的。
所以**自评只允许客观指标**：占位符几个、风格弱不弱、九维覆盖几维、
时长合不合规、平台禁词冲突几条。

B（定向修补）负责在过程中救火，但**只许改输入与查表，不许写内容**：
    风格弱       -> 用候选风格点名重跑
    缺光/运镜     -> 查表补（查表不是编）
    缺工艺/材质   -> 调 bridge 去学，学到再跑
    时长不合规     -> _plan_duration 修正
    还是不行      -> 标记"需人工"，不许硬写

输出：三版 + 指标表 + 按指标排的推荐（不是按好看排）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

FMT = "即梦 Seedance 2.5 · 整段（中文）"


def _paths():
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    return (d["模型目录"][1]["default"], d["语料文件"][1]["default"],
            d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])


def critic(out, dbg):
    """客观指标。一个美学判断都不许进这里。"""
    holes = len(re.findall(r"<[^>]*>", out))
    weak = "库中没有可靠匹配" in out
    m = {
        "holes": holes,
        "weak_style": 0 if not weak else 1,
        "style_ok": 0 if weak else 1,
        "light": 0,
        "motion": 0,
        "subject": 0,
        "craft": 0,
        "material": 0,
        "scene": 0,
    }
    # 光/运镜：正文里出现词表里的描述就算有
    for name, row in N._load_ref("light_ref.json").items():
        if row.get("zh", "")[:8] and row["zh"][:8] in out:
            m["light"] = 1
            break
    for name, row in N._load_ref("motion_ref.json").items():
        if row.get("zh", "")[:8] and row["zh"][:8] in out:
            m["motion"] = 1
            break
    # 正文里出现其他维度实体的名字（粗判）
    for line in dbg.split("\n"):
        if line.startswith("最终"):
            if "主体" in line:
                m["subject"] = 1
            if "风格" in line and "不拼内容" not in line:
                m["style_ok"] = max(m["style_ok"], 1)
        # 调试行形如： "材质: 剑刃钢 0.4070 (下限0.52) 未过"
        for key, field in (("工艺:", "craft"), ("材质:", "material")):
            if line.strip().startswith(key) and "未过" not in line:
                if "（无）" not in line and "-" != line.split(key)[1].strip()[:1]:
                    m[field] = 1
    # 点名来的技法/材质写在【技法】行里，也算这一维有了——
    # 它确实进了提示词，只是没走通道（通道赢不过风格，这是设计而非缺陷）
    if "技法：" in out:
        m["craft"] = 1
    # 材质：名字或它的描述进正文就算有（点名进来的是描述，不是名字）
    try:
        for r in N._load_index("材质文件"):
            nm = str(r.get("mat_zh") or "")
            desc = str(r.get("description") or "").split("：")[-1].strip()
            if (nm and nm in out) or (desc and desc[:10] in out):
                m["material"] = 1
                break
    except Exception:
        pass
    m["dims"] = sum(m[k] for k in
                    ("style_ok", "light", "motion", "subject", "craft", "material"))
    return m


def _run(q, paths):
    M, C, S, K, MT = paths
    return N.LocalStyleHint().run(q, M, C, S, K, MT, True, "文生视频", False,
                                  FMT, "cpu", "视频", "导演/风格聚合", 1, "", False)


def best_style_candidates(q, paths, n=3):
    """给修补用：这个查询最像的 n 个风格实体名。"""
    M, C, S, K, MT = paths
    items, _m, _s, _d, _c, _mat = N._rank(
        q, M, C, "cpu", n, "导演/风格聚合", "视频", S, K, MT, True)
    out = []
    for it in items:
        nm = it.get("director_zh") or it.get("director")
        if nm and nm not in out:
            out.append(nm)
    return out


def draft_queries(q, paths):
    """三版候选的三种输入。

    坑：第一版写的是"原话 / 原话+点名风格 / 原话+补光运镜"，
    结果三版输出**一模一样**——因为乌尔善本来就是最高分，
    "黄昏""横移"本来就在它的关键词里，改措辞不改变检索。
    所以差异必须来自**结构**：换风格实体、换技法、换详略。
    """
    out = [("A 原话", q)]
    cands = best_style_candidates(q, paths, 3)
    # B：换一个**次优**风格（不是最高分那个，否则和 A 一样）
    if len(cands) >= 2:
        out.append((f"B 换风格（{cands[1]}）", f"用{cands[1]}，{q}"))
    elif cands:
        out.append((f"B 点名风格（{cands[0]}）", f"用{cands[0]}，{q}"))
    # C：点名一个技法（从症状表拿，这是"开药方"那条路）
    _hit, means = N._symptom_means(q)
    if not means:
        # 没报症状，就用打击感这一组做默认——它是武戏最常见的缺口
        means = [m["zh"] for m in
                 (N._load_symptoms().get("打击感不够", {}).get("means") or [])]
    if means:
        out.append(("C 点名技法", f"用顿帧，{q}"))
    return out


def repair(q, m, paths, tried):
    """根据指标决定改什么。返回 (新查询, 动作说明) 或 (None, 原因)。

    只许改输入与查表，不许写内容。
    顺序按"能自己解决的程度"排：缺维度（可点名/可学） > 缺光运镜（查表）
    > 弱风格（点名） > 洞（放弃，交给人）。
    """
    # ① 缺工艺：找技法名点名；表里没有就什么都做不了
    if not m["craft"]:
        syn = N._load_symptoms()
        names = []
        for sym, body in syn.items():
            if sym in (q or ""):
                names += [x.get("craft") for x in (body.get("means") or [])]
        names += ["顿帧", "反作用", "速度斜坡", "接触特写"]
        for nm in dict.fromkeys([n for n in names if n]):
            if nm in (q or ""):          # 已经点过名了，别再叠一层
                continue
            nq = f"用{nm}，{q}"
            if nq not in tried:
                return nq, f"缺工艺：点名技法「{nm}」"
        return None, "缺工艺：技法名都试过了"

    # ② 缺材质：馆藏里材质词最全，先试在查询里点名材质方向
    if not m["material"]:
        for w in ("锻打铁", "旧皮革", "粗麻", "铜绿", "剑刃钢"):
            if w in (q or ""):       # 已经试过这个词，别再叠
                continue
            nq = f"{q}，{w}"
            if nq not in tried:
                return nq, f"缺材质：试「{w}」"
        return None, "缺材质：候选都试过了"

    # ③ 弱风格
    if m["weak_style"]:
        for cand in best_style_candidates(q, paths, 3):
            nq = f"用{cand}，{q}"
            if nq not in tried:
                return nq, f"风格弱：点名「{cand}」重跑"
        return None, "风格弱：候选都试过了"

    # ④ 缺光 / 缺运镜（查表）
    if not m["light"]:
        lg = N._match_ref("light_ref.json", q, [])
        if lg:
            return f"{q}，{lg['kw'][0]}", f"缺光线：查表补「{lg['kw'][0]}」"
    if not m["motion"]:
        mv = N._match_ref("motion_ref.json", q, [])
        if mv:
            return f"{q}，{mv['kw'][0]}", f"缺运镜：查表补「{mv['kw'][0]}」"

    return None, "已达标；剩下的洞是内容，交给人"


def main(req, rounds=2):
    paths = _paths()
    print(f"=== agent: {req} ===")
    print(f"    格式 {FMT}\n")

    results = []
    for name, q in draft_queries(req, paths):
        out, dbg = _run(q, paths)
        m = critic(out, dbg)
        trace = [(q, f"初版 {m['dims']}/6 维，洞 {m['holes']} 个")]
        tried = {q}
        for r in range(rounds):
            nq, why = repair(q, m, paths, tried)
            if not nq:
                trace.append((q, f"停止：{why}"))
                break
            tried.add(nq)
            out2, dbg2 = _run(nq, paths)
            m2 = critic(out2, dbg2)
            trace.append((nq, f"{why} -> {m2['dims']}/6 维，洞 {m2['holes']} 个"))
            # 无进展就停：维度没涨、洞没少，再试只是浪费
            if m2["dims"] <= m["dims"] and m2["holes"] >= m["holes"]:
                trace.append((nq, "无进展，停止"))
                q, out, dbg, m = nq, out2, dbg2, m2
                break
            q, out, dbg, m = nq, out2, dbg2, m2
        results.append({"name": name, "query": q, "out": out, "m": m,
                        "trace": trace})

    print("─" * 72)
    for r in results:
        print(f"\n【{r['name']}】  维 {r['m']['dims']}/6  洞 {r['m']['holes']}  "
              f"弱风格 {r['m']['weak_style']}")
        for q, why in r["trace"]:
            print(f"    · {why}")
        print("    " + r["out"][:210].replace("\n", " "))

    print("\n" + "─" * 72)
    # 按指标排：洞少优先，其次维度多，最后弱风格少
    ranked = sorted(results, key=lambda r: (r["m"]["holes"],
                                            -r["m"]["dims"],
                                            r["m"]["weak_style"]))
    print("按指标排序（不是按好看）：")
    for i, r in enumerate(ranked, 1):
        print(f"  {i}. {r['name']}  洞 {r['m']['holes']}  维 {r['m']['dims']}/6")

    # 洞是什么，必须说清：这些是内容，agent 不许填
    best = ranked[0]
    holes = re.findall(r"<([^>]*)>", best["out"])
    if holes:
        print(f"\n最好的那版还有 {len(holes)} 处要人写：")
        for h in dict.fromkeys(holes):
            print(f"    <{h[:56]}>")
        print("    这几处是内容——按规矩 agent 不填，交给人。")

    print("\n### AGENT_DONE")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "一个骑士手握一把长剑，和一群人交战")
