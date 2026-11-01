"""再测六条日常句"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

CASES = [
    "一个女人在厨房里做饭",
    "一个人站在电梯口等电梯",
    "下雨了，一个男人撑着伞在路边等",
    "一个人在数钱",
    "一个小男孩蹲在地上看蚂蚁",
    "深夜，一个人坐在楼梯上抽烟",
]

for q in CASES:
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    seg = [x.strip() for x in out.split("。") if x.strip()]
    print(f"【{q[:18]}】{len(out)} 字")
    for x in seg:
        if x.startswith(("自然光", "<风格", "只使用<", "不要出现：<")):
            continue
        print("   " + x[:66])
    # 标出空位
    holes = []
    if "只使用<环境声>" in out:
        holes.append("声音空")
    if "不要出现：<" in out:
        holes.append("风险空")
    if "<风格：库中" in out:
        holes.append("风格空")
    if "<写：" in out:
        holes.append("节拍空")
    print("   ⚠ " + ("、".join(holes) if holes else "无空位"))
    print()

print("### E2E2_DONE")
