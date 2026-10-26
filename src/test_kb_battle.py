"""
打斗知识的验收：新条目命中 + 老条目对照不变（老规矩，两组数）

新条目：查询里逐字写了新词（札甲 / 护腕 / 剑首 / 碎盾 / 顿帧 / 反作用 / 锻打铁…）
对照：上一批（剑与盔甲）和更早的条目，必须保持原样
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")
M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(RAW, "corpus_v21.jsonl")

NEW = dict(
    subjects="subjects_v14.jsonl", crafts="crafts_v7.jsonl",
    materials="materials_v12.jsonl")
OLD = dict(
    subjects="subjects_v13.jsonl", crafts="crafts_v6.jsonl",
    materials="materials_v11.jsonl")

# (查询, 期望命中的实体, 期望落在哪个渠道)
CASES = [
    ("札甲上的甲片", "札甲", "subjects"),
    ("护腕扣着两道皮带", "护腕", "subjects"),
    ("剑首被掌心磨亮", "剑首", "subjects"),
    ("一面碎盾立在土里", "碎盾", "subjects"),
    ("断矛斜插在地上", "断矛", "subjects"),
    ("军旗被风横着扯起来", "军旗", "subjects"),
    ("披风下摆拖在土里", "披风", "subjects"),
    ("钝器的打击感不够", "顿帧", "crafts"),
    ("接触那一下要停住", "顿帧", "crafts"),
    ("被打的人要往后退", "反作用", "crafts"),
    ("挥出去要由慢到快", "速度斜坡", "crafts"),
    ("切到接触点的近景", "接触特写", "crafts"),
    ("锻打铁上的锤痕", "锻打铁", "materials"),
    ("皮革用久了发软", "旧皮革", "materials"),
    ("铜绿长在凹处", "铜绿", "materials"),
]

# 对照：更早的批次，改动前后都必须命中
CONTROLS = [
    ("拿起一把剑", "长剑"),
    ("头盔", "板甲"),
    ("举盾", "圆盾"),
    ("竹简", "简牍"),
    ("一只猫坐在窗台上", "猫"),
    ("在太空中拍摄太阳的黑子", "太阳黑子"),
    ("蓝晒印相", "蓝晒"),
]


def run(paths, cases):
    S = os.path.join(RAW, paths["subjects"])
    K = os.path.join(RAW, paths["crafts"])
    MT = os.path.join(RAW, paths["materials"])
    hit = 0
    detail = []
    for case in cases:
        q, want = case[0], case[1]
        channel = case[2] if len(case) > 2 else "subjects"
        items, _m, subj, _d, craft, mat = N._rank(
            q, M, C, "cpu", 1, "导演/风格聚合", "不限", S, K, MT, True)
        got = ""
        if channel == "subjects":
            got = (subj or {}).get("zh", "")
        elif channel == "crafts":
            got = (craft or {}).get("zh", "")
        else:
            got = (mat or {}).get("zh", "")
        ok = (want in got) or (got in want)
        hit += ok
        detail.append((q, want, got, ok))
    return hit, detail


print("=== 新条目（v14 / v7 / v12）===")
new_hit, new_detail = run(NEW, CASES)
for q, want, got, ok in new_detail:
    print(f"  [{'OK' if ok else '--'}] {q[:20]:<22} 期望 {want:<6} 实得 {got or '（无）'}")
print(f"  命中 {new_hit}/{len(CASES)}")

print("\n=== 对照（老条目，改动前后应当相同）===")
old_hit, old_detail = run(OLD, CONTROLS)
new_chit, new_cdetail = run(NEW, CONTROLS)
same = 0
for (q, want, g_old, ok_old), (_, _, g_new, ok_new) in zip(old_detail, new_cdetail):
    flag = "不变" if ok_old == ok_new else "变了"
    same += (ok_old == ok_new)
    print(f"  [{flag}] {q[:20]:<22} 改前 {g_old or '（无）':<8} 改后 {g_new or '（无）'}")
print(f"  对照命中 {old_hit}/{len(CONTROLS)} -> {new_chit}/{len(CONTROLS)}；结果一致 {same}/{len(CONTROLS)}")

print("\n### BATTLE_KB_VERIFY_DONE")
