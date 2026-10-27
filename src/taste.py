"""
品味采集：出三版，你挑一个，我记下你挑的那版用了什么

为什么这样设计
--------------
品味的原料是**判断**，不是打分表。所以只要能回答一个问题：哪个好？
其余全部自动记：
    这一版用了什么风格 / 什么光 / 什么运镜 / 几个占位符 / 什么格式
挑完就有一条"什么条件下人会选它"的记录。
攒够之后，report 会自己浮出规律（比如"你总选光更具体的"）。

用法
----
    python src/taste.py ask "一个道士和僵尸对打，六个镜头"     # 出三版
    python src/taste.py pick B --note "光对"                 # 记一条
    python src/taste.py report                               # 看规律
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
sys.path.insert(0, os.path.join(ROOT, "src"))

RAW = os.path.join(ROOT, "data", "raw")
PREFS = os.path.join(RAW, "prefs.jsonl")
PENDING = os.path.join(RAW, "taste_pending.json")

import agent as A  # noqa: E402


def _knobs(paths, q):
    """这一版用了什么：风格 / 光 / 运镜 / 数量。"""
    M, C, S, K, MT = paths
    items, _m, subj, _d, _c, _mat = N_rank(q, M, C, S, K, MT)
    top = items[0] if items else {}
    import local_style_hint as N
    lg = N._match_ref("light_ref.json", q, top.get("kw_zh") or [])
    mv = N._match_ref("motion_ref.json", q, top.get("kw_zh") or [])
    return {
        "style": top.get("director_zh") or top.get("director") or "",
        "score": round(float(top.get("score") or 0), 4),
        "light": (lg or {}).get("zh", "")[:24],
        "motion": (mv or {}).get("zh", "")[:20],
        "subject": (subj or {}).get("zh", ""),
        "kw": (top.get("kw_zh") or [])[:4],
    }


def N_rank(q, M, C, S, K, MT):
    import local_style_hint as N
    return N._rank(q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)


def cmd_ask(req):
    import re
    paths = A._paths()
    # 多镜头路径会让三版趋同（每镜都是空槽，洞数一样，差异被吃掉）。
    # 品味采集要的是"同一镜的三种写法"，所以先把镜头数去掉，按单镜出整段。
    # 注意原句常写成「，六个镜头」，不一定带"要/需要"。
    single = re.sub(r"[，,]?\s*(?:要|需要)?\s*[一二两三四五六七八九十\d]+\s*个\s*镜头",
                    "", req).strip("，, ")
    cands = []
    for name, q in A.draft_queries(single, paths):
        out, dbg = A._run(q, paths)
        m = A.critic(out, dbg)
        cands.append({"key": name[0], "name": name, "query": q,
                      "out": out, "m": m, "knobs": _knobs(paths, q)})
    cands.sort(key=lambda c: (c["m"]["holes"], -c["m"]["dims"]))
    with open(PENDING, "w", encoding="utf-8") as f:
        json.dump({"request": req, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "cands": cands}, f, ensure_ascii=False, indent=1)

    print(f"=== {req} ===\n")
    for c in cands:
        k = c["knobs"]
        print(f"[{c['key']}] {c['name']}   维 {c['m']['dims']}/6  洞 {c['m']['holes']}")
        print(f"     风格 {k['style']} {k['score']}   光 {k['light'] or '（无）'}   "
              f"运镜 {k['motion'] or '（无）'}")
        print("     " + c["out"][:150].replace("\n", " "))
        print()
    print("挑一个：python src/taste.py pick A|B|C --note \"为什么\"")
    print("\n### TASTE_ASK_DONE")


def cmd_pick(letter, note=""):
    if not os.path.exists(PENDING):
        print("  先跑 ask")
        return
    d = json.load(open(PENDING, encoding="utf-8"))
    chosen = next((c for c in d["cands"] if c["key"] == letter.upper()), None)
    if not chosen:
        print(f"  没有 {letter} 这一版")
        return
    rec = {
        "request": d["request"],
        "asked": d["ts"],
        "picked": letter.upper(),
        "picked_knobs": chosen["knobs"],
        "picked_metrics": chosen["m"],
        "picked_text": chosen["out"],
        "rejected": [{"key": c["key"], "knobs": c["knobs"],
                      "metrics": c["m"]} for c in d["cands"]
                     if c["key"] != chosen["key"]],
        "note": note,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(PREFS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n = sum(1 for _ in open(PREFS, encoding="utf-8"))
    print(f"  记下了：选 {letter.upper()}（{chosen['knobs']['style']}）。累计 {n} 条")
    os.remove(PENDING)


def cmd_report():
    if not os.path.exists(PREFS):
        print("  还没有记录")
        return
    rows = [json.loads(l) for l in open(PREFS, encoding="utf-8") if l.strip()]
    print(f"=== 偏好 {len(rows)} 条 ===")
    from collections import Counter
    st = Counter(r.get("picked_knobs", {}).get("style") or "（无）" for r in rows)
    lt = Counter((r.get("picked_knobs", {}).get("light") or "（无）")[:12]
                 for r in rows)
    for name, cnt in st.most_common():
        print(f"  风格 {name:<12} {cnt}")
    print()
    for name, cnt in lt.most_common():
        print(f"  光   {name:<14} {cnt}")
    # 一条最简单的规律：被选的那版平均维度是否高于被拒的
    # 老记录（早期手写的那条）没有 picked_metrics，跳过而不是崩
    have = [r for r in rows if "picked_metrics" in r]
    if have:
        win = sum(r["picked_metrics"]["dims"] for r in have) / len(have)
        lose = [c["metrics"]["dims"] for r in have for c in r.get("rejected", [])]
        lose_avg = sum(lose) / len(lose) if lose else 0
        print(f"\n  被选的版本平均 {win:.2f}/6 维，被拒的平均 {lose_avg:.2f}/6 维")
        print(f"  （有指标数据的记录 {len(have)}/{len(rows)} 条）")
    else:
        print("\n  还没有带指标的记录（老记录格式不同）")
    print("\n### TASTE_REPORT_DONE")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "ask":
        cmd_ask(sys.argv[2])
    elif cmd == "pick":
        note = ""
        if "--note" in sys.argv:
            note = sys.argv[sys.argv.index("--note") + 1]
        cmd_pick(sys.argv[2], note)
    else:
        cmd_report()
