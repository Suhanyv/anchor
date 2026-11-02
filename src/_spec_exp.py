"""
实验二：风格空的那 43 条，其他维度是不是已经够了？

假设：风格空 ≠ 提示词不能用。
如果光、调色、焦段、构图、角度、空气这些**具体**维度都填上了，
导演名字只是锦上添花。

量法：对每条，数"具体填上了几维"（不是通用兜底、不是空）。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
from e2e_bulk import load_cases  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

GENERIC = ("只使用现场的环境声",
           "不要出现：手部畸形、面部漂移、道具穿模",
           "动作继续，幅度不变")

# 每个具体维度的识别前缀
DIMS = {
    "光": lambda s: s and not s.startswith("自然光") and "光" not in s[:2] is False,
    "构图": lambda s: s.startswith("构图"),
    "景别": lambda s: s.startswith("景别"),
    "角度": lambda s: s.startswith("角度"),
    "光位": lambda s: s.startswith("光位"),
    "色调": lambda s: s.startswith("色调"),
    "光学": lambda s: s.startswith("光学"),
    "空气": lambda s: s.startswith("空气"),
    "镜头": lambda s: s.startswith("镜头"),
    "视觉": lambda s: s.startswith("视觉"),
    "画面": lambda s: s.startswith("画面"),
    "机位": lambda s: s.startswith("机位"),
}

rows = []
for sec, q, split in load_cases():
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频",
        "导演/风格聚合", 1, "", False)
    segs = [x.strip() for x in out.split("。") if x.strip()]
    style_empty = any("<风格" in s for s in segs)
    n_spec = 0
    for s in segs:
        if any(s.startswith(g) for g in GENERIC):
            continue
        if any(f(s) for f in DIMS.values()):
            n_spec += 1
    # 声音/风险/节拍 是否具体
    if not any("只使用现场的环境声" in s for s in segs) and any(s.startswith("只使用") for s in segs):
        n_spec += 1
    if not any("不要出现：手部畸形、面部漂移、道具穿模" in s for s in segs) and any(s.startswith("不要出现") for s in segs):
        n_spec += 1
    if not any("动作继续，幅度不变" in s for s in segs):
        n_spec += 1
    rows.append({"q": q, "split": split, "style_empty": style_empty, "spec": n_spec})

empty = [r for r in rows if r["style_empty"]]
full = [r for r in rows if not r["style_empty"]]
print(f"\n  风格空 {len(empty)} 条 / 风格可信 {len(full)} 条")
for label, rs in (("风格空", empty), ("风格可信", full)):
    if not rs:
        continue
    dist = {}
    for r in rs:
        dist[r["spec"]] = dist.get(r["spec"], 0) + 1
    avg = sum(r["spec"] for r in rs) / len(rs)
    print(f"  {label:<6} 平均具体维度 {avg:.1f}  分布 {dict(sorted(dist.items()))}")

held = [r for r in rows if r["split"] == "heldout" and r["style_empty"]]
print(f"\n  留出集里风格空的 {len(held)} 条，其中：")
print(f"    具体维度 >= 4 的 {sum(1 for r in held if r['spec'] >= 4)} 条"
      f"（这些其实已经能拍）")
print(f"    具体维度 <= 2 的 {sum(1 for r in held if r['spec'] <= 2)} 条"
      f"（这些确实薄）")
print("\n### SPEC_DONE")
