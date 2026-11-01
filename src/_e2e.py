"""端到端测试：六条没写进库的自然句"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

CASES = [
    "一个女人在菜市场挑鱼",
    "深夜，一辆出租车停在桥上",
    "一个老人坐在公园长椅上喂鸽子",
    "雪天，一个猎人蹲在树后",
    "海上，一艘渔船在暴风雨里",
    "赛博朋克，一个女孩在巷子里走",
]

for i, q in enumerate(CASES, 1):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    print(f"########## {i}. {q}  ({len(out)} 字) ##########")
    print(out)
    print()

print("### E2E_DONE")
