"""应用桥接结果并验证：新学到的能查到 + 老条目不变"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(RAW, "corpus_v21.jsonl")
S = os.path.join(RAW, "subjects_v14.jsonl")
MT = os.path.join(RAW, "materials_v12.jsonl")


def hit(q, crafts_file):
    K = os.path.join(RAW, crafts_file)
    _i, _m, _s, _d, craft, _mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "不限", S, K, MT, True)
    c = craft or {}
    return c.get("zh", ""), float(c.get("score") or 0)


NEW = "crafts_v9.jsonl"
OLD = "crafts_v8.jsonl"

print("=== 新学到的（crafts_v9）===")
for q in ("雕漆", "错金银的镶嵌", "蜡染的冰裂纹", "tie dye resist"):
    got, sc = hit(q, NEW)
    print(f"  {q[:18]:<20} -> {got or '（无）':<8} {sc:.3f}")

print("\n=== 对照（v8 -> v9 不变）===")
same = 0
qs = ("蓝晒印相", "银丝掐丝", "丝绸刺绣", "接触那一下要停住", "影调要压暗")
for q in qs:
    a, _ = hit(q, OLD)
    b, _ = hit(q, NEW)
    same += (a == b)
    print(f"  [{'不变' if a == b else '变了'}] {q[:16]:<18} {a or '无':<8} -> {b or '无'}")
print(f"  一致 {same}/{len(qs)}")

print("\n### BRIDGE_APPLY_VERIFY_DONE")
