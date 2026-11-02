"""
批量跑 120 条，只报统计和最差的例子（不刷全文）

为什么要到 120 条：36 条时每个类别只有几条，看得见个案看不见分布。
扩到 120 条，才能看出"哪一类整体没覆盖"，而不是"哪一句碰巧不行"。

统计口径（与 e2e_suite 一致）：
    硬错误   节拍错配 / 指令词泄漏 / 空镜+两人同框
    具体     声音、风险、节拍各有专门条目（不是通用兜底）
    风格     可信 or 空
"""
import os
import sys
from collections import Counter

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
from e2e_suite import check  # noqa: E402

CASES = r"F:\llm\data\eval\cases_120.txt"


def load_cases():
    """返回 [(区段, 句子, 'dev'|'heldout')]，单双号交替切分"""
    out, section = [], ""
    for line in open(CASES, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "、" in line:
                section = line.lstrip("# ").strip()
            continue
        out.append([section, line])
    for i, row in enumerate(out):
        row.append("dev" if i % 2 == 0 else "heldout")
    return [tuple(r) for r in out]


def main():
    cases = load_cases()
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
    S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                d["材质文件"][1]["default"])

    stat = {"n": 0, "hard": 0, "style_empty": 0,
            "sound_gen": 0, "risk_gen": 0, "beat_gen": 0}
    split_stat = {"dev": Counter(), "heldout": Counter()}
    split_n = Counter()
    by_sec = Counter()
    by_sec_hard = Counter()
    worst = []

    for sec, q, split in cases:
        out, _ = N.LocalStyleHint().run(
            q, M, C, S, K, MT, True, "文生视频", False,
            "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频",
            "导演/风格聚合", 1, "", False)
        hard, soft, beat = check(q, out)
        stat["n"] += 1
        by_sec[sec] += 1
        split_n[split] += 1
        split_stat[split]["hard"] += 1 if hard else 0
        split_stat[split]["style_empty"] += 1 if "风格空" in soft else 0
        split_stat[split]["beat_gen"] += 1 if "节拍通用" in soft else 0
        split_stat[split]["sound_gen"] += 1 if "声音通用" in soft else 0
        split_stat[split]["risk_gen"] += 1 if "风险通用" in soft else 0
        if hard:
            stat["hard"] += 1
            by_sec_hard[sec] += 1
            worst.append((q, hard, beat))
        for x in soft:
            if x == "风格空":
                stat["style_empty"] += 1
            elif x == "声音通用":
                stat["sound_gen"] += 1
            elif x == "风险通用":
                stat["risk_gen"] += 1
            elif x == "节拍通用":
                stat["beat_gen"] += 1

    n = stat["n"]
    print(f"\n=== 共 {n} 条 ===")
    print(f"  硬错误          {stat['hard']:>3}  ({stat['hard']/n:.0%})")
    print(f"  风格空          {stat['style_empty']:>3}  ({stat['style_empty']/n:.0%})")
    print(f"  节拍通用        {stat['beat_gen']:>3}  ({stat['beat_gen']/n:.0%})")
    print(f"  声音通用        {stat['sound_gen']:>3}  ({stat['sound_gen']/n:.0%})")
    print(f"  风险通用        {stat['risk_gen']:>3}  ({stat['risk_gen']/n:.0%})")
    print("\n  开发集 / 留出集：")
    for k in ("dev", "heldout"):
        n2 = split_n[k] or 1
        st = split_stat[k]
        print(f"    {k:<8} n={split_n[k]:>3}  硬错误 {st['hard']:>2}  "
              f"风格空 {st['style_empty']/n2:.0%}  "
              f"节拍通用 {st['beat_gen']/n2:.0%}  "
              f"声音通用 {st['sound_gen']/n2:.0%}  "
              f"风险通用 {st['risk_gen']/n2:.0%}")
    print("\n  分类看硬错误：")
    for sec, cnt in by_sec.items():
        h = by_sec_hard.get(sec, 0)
        print(f"    {sec[:18]:<20} {h}/{cnt}")
    if worst:
        print("\n  硬错误样例：")
        for q, hard, beat in worst[:8]:
            print(f"    [{ '、'.join(hard) }] {q[:22]}")
    print("\n### BULK_DONE")


if __name__ == "__main__":
    main()
