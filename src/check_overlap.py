"""量四句描述之间的重复：光 / 空气 / 视觉 / 色调

结论（2026-11-01）：**实测没有重复**。两字重叠率全部低于 15%。
光说"怎么表现"，空气说"空气里有什么"，是分工不是冗余。
看起来像问题，量了不是——所以不做去重。
以后再加维度时，先跑一遍这个再决定要不要合并。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

# 只看"内容词"（两字以上的名词片段），忽略"的、了、在"这类
STOP = set("的了在是和与也就都还很有被把从到对上下来去一个一种所有")


def words(s):
    return {s[i:i + 2] for i in range(len(s) - 1)
            if not (set(s[i:i + 2]) & STOP)}


CASES = [
    "雨里，一个女孩抱着纸箱跑",
    "雪天，两个武士在雪山对决",
    "赛博朋克，雨里，一个道士和僵尸对打",
    "深夜，便利店里只有一个人",
    "沙漠中一座废弃的加油站",
]

for q in CASES:
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    parts = {}
    for sx in out.split("。"):
        sx = sx.strip()
        for tag in ("视觉", "空气", "色调", "画面"):
            if sx.startswith(tag):
                parts[tag] = sx
    # 光那一句没有前缀，取第一句
    parts["光"] = out.split("。")[0].strip() if out else ""
    print(f"\n【{q[:16]}】")
    keys = [k for k in ("光", "空气", "视觉", "色调") if k in parts]
    for k in keys:
        print(f"  {k}: {parts[k][:44]}")
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            wa, wb = words(parts[a]), words(parts[b])
            if wa and wb:
                ov = len(wa & wb) / min(len(wa), len(wb))
                if ov > 0.15:
                    print(f"    ⚠ {a} vs {b} 重叠 {ov:.0%}  {sorted(wa & wb)[:5]}")

print("\n### OVERLAP_DONE")
