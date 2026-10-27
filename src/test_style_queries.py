"""
查询侧扩写验收：自然句命中 + 模板式措辞对照

两组数：
    自然句       每个风格取一句，看能不能找回它
    模板式对照    以前能对的那些，不能因为这个改动变差
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
M = os.path.join(ROOT, "models/e5-director-c27")
S = os.path.join(RAW, "subjects_v14.jsonl")
K = os.path.join(RAW, "crafts_v8.jsonl")
MT = os.path.join(RAW, "materials_v12.jsonl")


def top_style(q, corpus_file):
    C = os.path.join(RAW, corpus_file)
    items, _m, _s, _d, _c, _mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0] if items else {}
    return (it.get("director_zh") or it.get("director") or "",
            float(it.get("score") or 0))


# 自然句：从扩写表里每个风格抽一句
rows = [json.loads(l) for l in open(os.path.join(RAW, "corpus_v24.jsonl"),
                                    encoding="utf-8") if l.strip()]
NATURAL = [(r["text_semantic"], r["director_zh"]) for r in rows
           if r.get("kind") == "style_query"]

# 模板式对照：这些以前就对，改动不该让它们变差
TEMPLATE = [
    ("希区柯克那种悬疑", "希区柯克"),
    ("库布里克式的对称构图", "库布里克"),
    ("韦斯·安德森的粉彩对称", "韦斯·安德森"),
    ("维伦纽瓦的巨物与雾霭", "维伦纽瓦"),
    ("黑泽明的雨和群像", "黑泽明"),
    ("蔡明亮的极慢长镜", "蔡明亮"),
    ("浮世绘的平涂轮廓线", "浮世绘"),
]

print("=== 自然句（v21 -> v24）===")
old_hit = new_hit = 0
bad = []
for q, want in NATURAL:
    o, _so = top_style(q, "corpus_v21.jsonl")
    n, sn = top_style(q, "corpus_v24.jsonl")
    old_hit += (o == want)
    new_hit += (n == want)
    if n != want:
        bad.append((q, want, n, sn))
print(f"  命中 v21 {old_hit}/{len(NATURAL)}  ->  v24 {new_hit}/{len(NATURAL)}")
for q, want, got, sc in bad[:6]:
    print(f"    [未中] {q[:22]:<24} 该是 {want:<8} 实得 {got or '（无）'} {sc:.3f}")

print("\n=== 模板式对照（两版都该对）===")
same = 0
for q, want in TEMPLATE:
    o, _ = top_style(q, "corpus_v21.jsonl")
    n, _ = top_style(q, "corpus_v24.jsonl")
    ok_o, ok_n = (o == want), (n == want)
    same += (ok_o == ok_n)
    flag = "不变" if ok_o == ok_n else "变了"
    print(f"  [{flag}] {q[:20]:<22} v21={o or '无':<8} v24={n or '无'}")
print(f"  结果一致 {same}/{len(TEMPLATE)}")

print("\n### STYLE_QUERY_VERIFY_DONE")
