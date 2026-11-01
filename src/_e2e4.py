"""第四批：类型片与场所"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

CASES = [
    "夜里的追车，两辆车在桥上别",
    "审讯室里，一个人被问了三个小时",
    "古代法场，一个犯人跪着",
    "夜市里，油烟和灯泡底下全是人",
    "考场里，所有人都在低头写",
    "车站月台上，两个人告别",
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
    print(f"【{q[:20]}】{len(out)} 字  {'⚠ ' + '、'.join(holes) if holes else '✓'}")
    for x in seg[:6]:
        print("   " + x[:62])
    print()

print("### E2E4_DONE")
