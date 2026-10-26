"""验「用 ，」这个空壳句子有没有修掉"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

CASES = [
    "用即梦，打击感要够，一个骑士手握一把长剑，和一群人交战",
    "用 ，打击感要够，一个骑士手握一把长剑",
    "用可灵做一个骑士站在石地中央",
    "拿即梦生成，雪林里女子拉弓搭箭",
    "sd2.5 一个骑士站在石地中区",
]
print("=== _strip_cmd ===")
for q in CASES:
    print(f"  {q[:34]:<36} -> {N._strip_cmd(q)[:44]}")
    print(f"  {'':36}    bad={'用 ，' in N._strip_cmd(q) or N._strip_cmd(q).startswith('用')}")

print("\n=== 端到端 ===")
node = N.LocalStyleHint()
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])
q = "用即梦，打击感要够，一个骑士手握一把长剑，和一群人交战"
out, _ = node.run(q, M, C, S, K, MT, True, "文生视频", False,
                  "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频",
                  "导演/风格聚合", 1, "", False)
print("  " + out[:150])
print("  含'用 ，':", "用 ，" in out)
print("\n### SHELL_FIX_DONE")
