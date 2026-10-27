"""查：机器人 / 草地 / 星空 在不在库里"""
import json
import os

ROOT = r"F:\llm"
for f, key in (("subjects_v15.jsonl", "subject_zh"),
               ("materials_v12.jsonl", "mat_zh"),
               ("crafts_v8.jsonl", "craft_zh")):
    rows = [json.loads(l) for l in
            open(os.path.join(ROOT, "data/raw", f), encoding="utf-8")
            if l.strip()]
    names = sorted({r.get(key) or "" for r in rows})
    print(f"=== {f}  {len(names)} 个实体 ===")
    for w in ("机器人", "机甲", "草地", "草坪", "星空", "夜空", "银河", "田野"):
        hit = [n for n in names if w in n]
        print(f"  含「{w}」: {hit[:4] if hit else '无'}")
    print()

print("=== 光表 ===")
light = json.load(open(os.path.join(ROOT, "data/raw/light_ref.json"),
                      encoding="utf-8"))
for w in ("夜晚", "星空", "月", "夜"):
    hit = [k for k in light if w in k or any(w in x for x in (light[k].get("kw") or []))]
    print(f"  含「{w}」: {hit[:4] if hit else '无'}")

print("\n### CHECK2_DONE")
