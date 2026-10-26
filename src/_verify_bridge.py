"""验桥接进来的条目：新条目能查到，老条目不变"""
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


def craft_hit(q, crafts_file):
    K = os.path.join(RAW, crafts_file)
    _i, _m, _s, _d, craft, _mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "不限", S, K, MT, True)
    return (craft or {}).get("zh", ""), float((craft or {}).get("score") or 0)


print("=== 桥接进来的新条目（crafts_v8）===")
for q in ("银丝掐丝", "掐丝的花丝", "gilt silver and filigree"):
    got, sc = craft_hit(q, "crafts_v8.jsonl")
    print(f"  {q[:18]:<20} -> {got or '（无）':<8} {sc:.3f}")

print("\n=== 对照：老条目必须不变（v7 vs v8）===")
same = 0
for q in ("蓝晒印相", "接触那一下要停住", "丝绸刺绣", "影调要压暗"):
    a, sa = craft_hit(q, "crafts_v7.jsonl")
    b, sb = craft_hit(q, "crafts_v8.jsonl")
    ok = a == b
    same += ok
    print(f"  [{'不变' if ok else '变了'}] {q[:16]:<18} v7={a or '无':<8} v8={b or '无'}")
print(f"  一致 {same}/4")

print("\n### BRIDGE_VERIFY_DONE")
