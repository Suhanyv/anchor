"""
诊断：沙滩查询为什么被判给「雾江孤舟」

已知：
    我和妹妹在沙滩上奔跑  ->  雾江孤舟 0.334  >  瓦尔达 0.263

要看三件事：
    1. top-8 风格各多少分（是不是普遍都低——那说明就没匹配上）
    2. 雾江孤舟那条文档的原文是什么（为什么它更像"奔跑"）
    3. 瓦尔达那条文档的原文是什么（为什么它不够像）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(RAW, "corpus_v21.jsonl")
S = os.path.join(RAW, "subjects_v14.jsonl")
K = os.path.join(RAW, "crafts_v8.jsonl")
MT = os.path.join(RAW, "materials_v12.jsonl")

Q = "我和妹妹在沙滩上奔跑"

print(f"=== top-8 风格（{Q}）===")
items, mode, subj, dom, craft, mat = N._rank(
    Q, M, C, "cpu", 8, "导演/风格聚合", "视频", S, K, MT, True)
for i, it in enumerate(items, 1):
    print(f"  {i}. {it.get('director_zh') or it.get('director')} "
          f"{float(it.get('score') or 0):.4f}  kw={it.get('kw_zh')}")

print("\n=== 这两条的原文 ===")
rows = [json.loads(l) for l in open(C, encoding="utf-8") if l.strip()]
for want in ("雾江孤舟", "瓦尔达", "阿涅斯"):
    for r in rows:
        nm = f"{r.get('director')} {r.get('director_zh')}"
        if want in nm:
            print(f"  [{r.get('doc_id')}] {nm.strip()}")
            print(f"      text: {str(r.get('text_semantic'))[:150]}")
            print(f"      tags: {r.get('tags')}")
            break

print("\n=== 沙滩这条题材 ===")
srows = [json.loads(l) for l in open(S, encoding="utf-8") if l.strip()]
for r in srows:
    if (r.get("subject_zh") or "") == "沙滩":
        print(f"  {r.get('doc_id')}  {r.get('phrase')}")
        print(f"      desc: {str(r.get('description'))[:120]}")

print("\n### BEACH_DIAG_DONE")
