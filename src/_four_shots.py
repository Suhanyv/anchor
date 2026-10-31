"""四镜连拍：统一风格，统一偏长（每镜显式给秒数）"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

STYLE = "文人水墨"

SHOTS = [
    ("镜1 · 正面推进 · 12秒", f"用{STYLE}，12 秒，雨里，正面，一个女孩抱着纸箱朝镜头来"),
    ("镜2 · 背面跟拍 · 15秒", f"用{STYLE}，15 秒，雨里，背面跟拍，一个女孩抱着纸箱跑"),
    ("镜3 · 脚下特写 · 8秒", f"用{STYLE}，8 秒，雨里，只拍一个女孩跑过时的脚下水花"),
    ("镜4 · 空镜收尾 · 12秒", f"用{STYLE}，12 秒，雨里，空镜，只剩地面上的水痕和还没落完的雨"),
]

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])
node = N.LocalStyleHint()

for tag, q in SHOTS:
    out, _ = node.run(q, M, C, S, K, MT, True, "文生视频", False,
                      "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频",
                      "导演/风格聚合", 1, "", False)
    print(f"########## {tag} ##########")
    print(out)
    print()

print("### FOUR_LONG_DONE")
