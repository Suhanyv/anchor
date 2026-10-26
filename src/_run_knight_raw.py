"""骑士那条，原样输出（不做任何美化）——看新加的打斗知识能不能进提示词"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

node = N.LocalStyleHint()
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

JOBS = [
    ("A 原话 · 整段", "一个骑士手握一把长剑，和一群人交战", "即梦 Seedance 2.5 · 整段（中文）"),
    ("B 点了打击感 · 整段", "用即梦，打击感要够，一个骑士手握一把长剑，和一群人交战",
     "即梦 Seedance 2.5 · 整段（中文）"),
    ("C 报出具体毛病 · 整段", "用即梦，打击感不够，接触那一下没有停住，一个骑士手握一把长剑，和一群人交战",
     "即梦 Seedance 2.5 · 整段（中文）"),
]

for tag, q, fmt in JOBS:
    items, _m, subj, _d, craft, mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    out, dbg = node.run(q, M, C, S, K, MT, True, "文生视频", False, fmt,
                        "cpu", "视频", "导演/风格聚合", 1, "", False)
    print(f"########## {tag} ##########")
    print(f"风格 {it.get('director_zh')} {float(it.get('score') or 0):.2f} | "
          f"主体 {(subj or {}).get('zh', '-')} | "
          f"工艺 {(craft or {}).get('zh', '-')} | 材质 {(mat or {}).get('zh', '-')}")
    print(out)
    print()
    print("--- 调试 ---")
    for l in dbg.split("\n"):
        if l.startswith(("最终", "工艺:", "材质:", "主体:", "【格式】")):
            print("  " + l[:130])
    print()

print("### RAW_KNIGHT_V2")
