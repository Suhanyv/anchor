"""
把 gaps.jsonl 变成一份「现在到底还缺什么」的清单

为什么要复检
------------
gaps 是**当时**记的。之后加了武士、僵尸片、拉力赛车、场景→光…很多已经解决了。
直接拿旧清单去学，会重复学已经有的东西。

做法
----
1. 归一化：剥掉工具自己加的前后缀（"用顿帧，" / "光用X，" / "，手持" / "，N个镜头"）
2. 去重：同一句只留一条
3. **复检**：现在再跑一遍，看风格分有没有过 0.30
4. 输出：已解决 / 仍缺，仍缺的附上"缺哪一维、下一步怎么补"
"""
import json
import os
import re
import sys

ROOT = r"F:\llm"
RAW = os.path.join(ROOT, "data", "raw")
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

WEAK = 0.30


def normalize(q):
    """剥掉工具加的前后缀，得到人原本说的那句"""
    t = q or ""
    t = re.sub(r"^用[^，,]{1,6}[，,]\s*", "", t)
    t = re.sub(r"^光用[^，,]+[，,]\s*", "", t)
    t = re.sub(r"^\d{1,2}\s*(?:秒|s)[，,]\s*", "", t)
    t = re.sub(r"[，,]\s*(?:手持|横移|环绕|贴地|俯拍|侧逆光|暖金|柔散光|冷青灰|"
               r"锻打铁|旧皮革|粗麻|铜绿|剑刃钢)\s*$", "", t)
    t = re.sub(r"[，,]?\s*(?:要|需要)?\s*[一二两三四五六七八九十\d]+\s*个\s*镜头\s*$", "", t)
    return t.strip("，, ")


def main():
    rows = [json.loads(l) for l in open(os.path.join(RAW, "gaps.jsonl"),
                                        encoding="utf-8") if l.strip()]
    seen, bases = set(), []
    for r in rows:
        b = normalize(r.get("query", ""))
        if len(b) >= 4 and b not in seen:
            seen.add(b)
            bases.append(b)

    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
    S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                d["材质文件"][1]["default"])

    solved, open_ = [], []
    for b in bases:
        items, _m, subj, _dm, craft, mat = N._rank(
            b, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
        it = items[0] if items else {}
        sc = float(it.get("score") or 0)
        rec = {"base": b, "score": round(sc, 4),
               "style": it.get("director_zh") or it.get("director") or "",
               "subject": (subj or {}).get("zh", ""),
               "orig_n": 1}
        (solved if sc >= WEAK else open_).append(rec)

    print(f"  原始 {len(rows)} 条 -> 去重 {len(bases)} 条")
    print(f"  已解决 {len(solved)} 条（风格分 >= {WEAK}）")
    print(f"  仍缺   {len(open_)} 条\n")
    for r in open_:
        print(f"    {r['score']:.3f}  {r['base'][:30]:<32} 主体={r['subject'] or '无'}")

    lines = ["# 还缺什么（自动复检）", "",
             "> 由 `src/gaps_to_todo.py` 生成。gaps 是**当时**记的，",
             "> 所以每条都拿现在的库重跑一遍——已经能查到的就不再列进来。", "",
             f"原始 {len(rows)} 条 → 去重 {len(bases)} 条 → 已解决 {len(solved)} → 仍缺 {len(open_)}",
             "", "## 仍缺", ""]
    for r in open_:
        lines.append(f"- **{r['base']}**　风格分 {r['score']:.3f}　"
                     f"主体 {r['subject'] or '（无）'}")
    lines += ["", "## 已解决（不用再学）", ""]
    for r in solved:
        lines.append(f"- ~~{r['base']}~~　→ {r['style']} {r['score']:.3f}")
    lines += ["", "## 怎么补", "",
              "1. **有明确实体的**（骆驼队/长船/市集）：给「中文词 | 英文查词 | 渠道」",
              "   ```",
              "   python src/bridge.py learn \"骆驼商队|camel caravan|subjects|场景\"",
              "   ```",
              "2. **是风格问题的**（分低但没有可加的实体）：补一个风格实体，",
              "   或写几条「会用到它的中文自然句」——**注意留出测试，别自测**。",
              "3. **已经能用的**：从清单划掉，别再学。", ""]
    out = os.path.join(RAW, "learn_todo.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"\n  写了 {out}")
    print("\n### GAPS_TODO_DONE")


if __name__ == "__main__":
    main()
