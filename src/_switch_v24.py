"""把节点与工作流切到 corpus_v24（含查询侧扩写）"""
import ast
import json
import os
import sys

ROOT = r"F:\llm"
NODE = os.path.join(ROOT, "comfyui", "local_style_hint.py")
WF = os.path.join(ROOT, "comfyui", "workflow_style_hint.json")

s = open(NODE, encoding="utf-8").read()
if "corpus_v24.jsonl" not in s:
    s = s.replace("corpus_v21.jsonl", "corpus_v24.jsonl")
    ast.parse(s)
    open(NODE, "w", encoding="utf-8").write(s)
    print("  节点 -> corpus_v24")

w = json.load(open(WF, encoding="utf-8"))
wv = w["nodes"][0]["widgets_values"]
for i, v in enumerate(wv):
    if isinstance(v, str):
        wv[i] = v.replace("corpus_v21.jsonl", "corpus_v24.jsonl")
json.dump(w, open(WF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  工作流 -> corpus_v24")
