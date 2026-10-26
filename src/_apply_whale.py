"""
一步做完：修鲸的词表 -> 节点切 v13 -> 工作流切 v13 -> 复测
（PowerShell here-string 反复吃引号，所以这段全部放文件里）
"""
import ast
import json
import os
import sys

ROOT = r"F:\llm"
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
sys.path.insert(0, os.path.join(ROOT, "src"))

# 1) 生成 v13
import fix_whale_kw  # noqa: E402  （import 即执行）

# 2) 节点与工作流切过去
p = os.path.join(ROOT, "comfyui", "local_style_hint.py")
s = open(p, encoding="utf-8").read()
if "subjects_v13.jsonl" not in s:
    s = s.replace("subjects_v12.jsonl", "subjects_v13.jsonl")
    ast.parse(s)
    open(p, "w", encoding="utf-8").write(s)
    print("  节点 -> subjects_v13")

wp = os.path.join(ROOT, "comfyui", "workflow_style_hint.json")
w = json.load(open(wp, encoding="utf-8"))
wv = w["nodes"][0]["widgets_values"]
for i, v in enumerate(wv):
    if isinstance(v, str):
        wv[i] = v.replace("subjects_v12.jsonl", "subjects_v13.jsonl")
json.dump(w, open(wp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  工作流 -> subjects_v13")

# 3) 复测
import importlib
import local_style_hint as N
importlib.reload(N)
node = N.LocalStyleHint()
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])
print("\n=== 复测 ===")
for q in ("一个男孩和一个鲸鱼女孩在卧室里相拥", "鲸的背露出水面", "一只猫坐在窗台上"):
    out, dbg = node.run(q, M, C, S, K, MT, True, "文生视频", False,
                        "片段（英文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    fin = next((l for l in dbg.split("\n") if l.startswith("最终")), "")
    print(f"  [{q[:18]}] {fin[:44]}")
    print(f"      {out[:84]}")
print("\n### WHALE_FIXED")
