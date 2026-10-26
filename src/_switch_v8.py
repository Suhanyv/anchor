"""把节点和工作流切到 crafts_v8"""
import ast
import json
import os
import sys

ROOT = r"F:\llm"
NODE = os.path.join(ROOT, "comfyui", "local_style_hint.py")
WF = os.path.join(ROOT, "comfyui", "workflow_style_hint.json")

s = open(NODE, encoding="utf-8").read()
if "crafts_v8.jsonl" not in s:
    s = s.replace("crafts_v7.jsonl", "crafts_v8.jsonl")
    ast.parse(s)
    open(NODE, "w", encoding="utf-8").write(s)
    print("  节点 -> crafts_v8")

w = json.load(open(WF, encoding="utf-8"))
wv = w["nodes"][0]["widgets_values"]
for i, v in enumerate(wv):
    if isinstance(v, str):
        wv[i] = v.replace("crafts_v7.jsonl", "crafts_v8.jsonl")
json.dump(w, open(WF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  工作流 -> crafts_v8")

sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as M  # noqa: E402
d = M.LocalStyleHint.INPUT_TYPES()["required"]
print("  工艺文件:", os.path.basename(d["工艺文件"][1]["default"]))
print("\n### SWITCH8_DONE")
