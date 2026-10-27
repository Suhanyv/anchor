"""验收：武士/剑客/芒草能不能查到，老条目是否不变"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(RAW, "corpus_v21.jsonl")
K = os.path.join(RAW, "crafts_v8.jsonl")
MT = os.path.join(RAW, "materials_v12.jsonl")


def subj_of(q, file):
    S = os.path.join(RAW, file)
    _i, _m, s, _d, _c, _mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "不限", S, K, MT, True)
    return (s or {}).get("zh", ""), float((s or {}).get("score") or 0)


NEW = "subjects_v15.jsonl"
OLD = "subjects_v14.jsonl"

print("=== 新条目（v15）===")
for q, want in (("雪天，两个武士在长满狗尾巴草山上对决", "武士"),
                ("一个剑客站在雪里", "剑客"),
                ("浪人戴着斗笠", "浪人"),
                ("武将骑着马，后面有旗", "武将"),
                ("侠客独自面对一群人", "侠客"),
                ("长满芒草的山坡", "芒草")):
    got, sc = subj_of(q, NEW)
    print(f"  [{'OK' if got == want else '--'}] {q[:22]:<24} 期望 {want:<5} 实得 {got or '（无）'} {sc:.3f}")

print("\n=== 对照（老条目）===")
same = 0
for q, want in (("拿起一把剑", "长剑"), ("头盔", "板甲"), ("竹简", "简牍"),
                ("一只猫坐在窗台上", "猫"), ("举盾", "圆盾"), ("沙滩", "沙滩")):
    a, _ = subj_of(q, OLD)
    b, _ = subj_of(q, NEW)
    same += (a == b)
    print(f"  [{'不变' if a == b else '变了'}] {q[:18]:<20} {a or '无':<8} -> {b or '无'}")
print(f"  一致 {same}/6")

print("\n### WARRIOR_VERIFY_DONE")
