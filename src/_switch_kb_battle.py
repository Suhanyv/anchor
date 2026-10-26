"""把节点与工作流切到打斗那一批：subjects_v14 / crafts_v7 / materials_v12"""
import ast
import json
import os

ROOT = r"F:\llm"
NODE = os.path.join(ROOT, "comfyui", "local_style_hint.py")
WF = os.path.join(ROOT, "comfyui", "workflow_style_hint.json")

PAIRS = [("subjects_v13.jsonl", "subjects_v14.jsonl"),
         ("crafts_v6.jsonl", "crafts_v7.jsonl"),
         ("materials_v11.jsonl", "materials_v12.jsonl")]

s = open(NODE, encoding="utf-8").read()
for old, new in PAIRS:
    if new not in s:
        s = s.replace(old, new)
ast.parse(s)
open(NODE, "w", encoding="utf-8").write(s)
print("  节点已更新")

w = json.load(open(WF, encoding="utf-8"))
wv = w["nodes"][0]["widgets_values"]
for i, v in enumerate(wv):
    if isinstance(v, str):
        for old, new in PAIRS:
            v = v.replace(old, new)
        wv[i] = v
json.dump(w, open(WF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  工作流已更新")

import sys
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as M  # noqa: E402
d = M.LocalStyleHint.INPUT_TYPES()["required"]
for k in ("题材文件", "工艺文件", "材质文件"):
    print(f"  {k}: {os.path.basename(d[k][1]['default'])}")
print("\n### SWITCH_DONE")
