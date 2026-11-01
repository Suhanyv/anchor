"""
风格缺口清单：哪些句子现在拿不到可靠风格

为什么要这个工具
----------------
1A 的代价是**风格空变多**（套件里 36 条中有 20 条）。
"以后多收集风格"要有个抓手——不然补到哪、还差多少，全靠感觉。

用法
----
    python src/style_gaps.py              # 跑套件里的 36 条，列出风格空的
    python src/style_gaps.py "一句话" ...  # 只查你给的句子

输出每行：句子 / 当前最像的候选 / 分数 / 有没有关键词交集
「没有交集」的就是**需要补文档**的：给它写一条语料，把这句话的用词写进去。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402


def main(extra=None):
    qs = list(extra or [])
    if not qs:
        from e2e_suite import CASES
        qs = CASES

    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
    S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                d["材质文件"][1]["default"])

    empty, hit = [], 0
    for q in qs:
        items, _m, _s, _d, _c, _mt = N._rank(
            q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
        it = items[0] if items else {}
        sc = float(it.get("score") or 0)
        kws = list(it.get("kw_zh") or []) + [str(it.get("director_zh") or "")]
        inter = [k for k in kws if k and k in q]
        if N._style_untrusted(it, q):
            empty.append((q, it.get("director_zh") or "-", sc, inter))
        else:
            hit += 1

    print(f"\n  可靠 {hit}/{len(qs)}    风格空 {len(empty)}")
    if empty:
        print("\n  需要补文档的（按分数从高到低）：")
        for q, name, sc, inter in sorted(empty, key=lambda x: -x[2]):
            mark = "有交集" if inter else "无交集"
            print(f"    {sc:.3f}  {mark}  {q[:24]:<26} 最近候选: {name}")
    print("\n### STYLE_GAPS_DONE")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
