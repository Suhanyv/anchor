"""
题材库 v2：加 type 字段，用于「分级去偏」

为什么需要
----------
全局去偏净亏 10pp（场景基准 55% -> 45%），但机制确实有效（#1 从第 8 升到第 1）。
逐题看是两类截然相反的情况：
    #1 主体=中世纪骑士  与 Villeneuve 运镜无关 -> 减掉纯赚（8 -> 1）
    #2 主体=雪原/荒原   与"史诗辽阔"高度重叠   -> 减掉把好东西也减了（1 -> 32）

所以按类型分流：
    character_object   具体的物 / 人 / 室内器物件 -> **与风格语义分离，可减**
    landscape_setting  地貌 / 街道 / 场地        -> **与"辽阔/空旷/自然光"等风格词重叠，不可减**
"""
import json
import os

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "subjects_v1.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "subjects_v2.jsonl")

# 题材英文名 -> 类型
TYPE = {
    # 具体的物 / 人 / 室内器物件
    "Medieval Knight": "character_object",
    "Wuxia Bamboo Grove": "character_object",
    "Spacecraft Interior": "character_object",
    "Hotel Corridor": "character_object",
    "Old Kitchen": "character_object",
    "Empty Classroom": "character_object",
    "Church Interior": "character_object",
    "Crowded Market": "character_object",
    "Old Man Close-Up": "character_object",
    "Galloping Horses": "character_object",
    # 地貌 / 街道 / 场地（本身就是风格信号）
    "Medieval Battlefield": "landscape_setting",
    "Tang Court": "landscape_setting",
    "Republican Shanghai": "landscape_setting",
    "Cyberpunk Street": "landscape_setting",
    "Underwater": "landscape_setting",
    "Snowfield": "landscape_setting",
    "Desert Caravan": "landscape_setting",
    "Ruined City": "landscape_setting",
    "Wheat Field": "landscape_setting",
    "Rainy Night Street": "landscape_setting",
}


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    out = []
    unknown = set()
    for r in rows:
        t = TYPE.get(r["subject_en"])
        if t is None:
            unknown.add(r["subject_en"])
            t = "landscape_setting"     # 保守：不认识的一律不减
        r2 = dict(r)
        r2["type"] = t
        out.append(r2)

    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(r["type"] for r in out)
    print(f"题材库 v1 -> v2 : {len(rows)} 条 -> {len(out)} 条")
    print(f"  类型分布: {dict(c)}")
    if unknown:
        print(f"  ⚠ 未定义类型的题材（已按 landscape_setting 处理，即不减）: {sorted(unknown)}")
    print()
    print("按类型列出：")
    for t in ("character_object", "landscape_setting"):
        names = sorted({r["subject_zh"] for r in out if r["type"] == t})
        print(f"  {t}（{len(names)} 个）: {' '.join(names)}")
    print(f"\n-> {OUT}")
    print("\n### SUBJECTS_V2_DONE")


if __name__ == "__main__":
    main()
