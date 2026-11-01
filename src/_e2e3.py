"""第三批：更难的日常与场所"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

CASES = [
    "医院的走廊里，一个护士推着车走过",
    "便利店夜班，一个店员在擦货架",
    "一个男人在理发店剃头",
    "一个女人在阳台上晾衣服",
    "一个修车工钻在车底下",
    "婚礼上，一桌人在敬酒",
]

for q in CASES:
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    holes = []
    if "只使用<环境声>" in out:
        holes.append("声音")
    if "不要出现：<" in out:
        holes.append("风险")
    if "<风格：库中" in out:
        holes.append("风格")
    if "<写：" in out:
        holes.append("节拍")
    seg = [x.strip() for x in out.split("。") if x.strip()]
    print(f"【{q[:20]}】{len(out)} 字  {'⚠ 空: ' + '、'.join(holes) if holes else '✓ 无空位'}")
    for x in seg[:7]:
        print("   " + x[:64])
    print()

print("### E2E3_DONE")
