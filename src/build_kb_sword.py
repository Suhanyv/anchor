"""
补「剑」——用户指出我把"剑"写成了"简"

实测确认库里没有剑：
    「拿起一把剑」「长剑出鞘」「剑刃反光」三条查询全部只出风格，零内容命中。
而骑士镜头（用户正在测的那组）的核心道具就是剑。

顺带补同一场的其他道具：剑鞘 / 圆盾 / 板甲 / 剑刃钢 / 锁子甲。
刻意不写"血""劈中人体"这类——那是 Veo 审核会挡的方向，
而且描述道具本身比描述暴力更有用。

写法规矩同前：只写可被拍到的东西（刃口磨亮的一条线、鞘口磨白的皮革），
不写"锋利""威武"这类形容词。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

SUBJECTS = [
    ("Longsword", "长剑", "a straight double-edged blade held point down, the fuller running to the guard",
     ["剑", "长剑", "剑刃", "剑柄", "剑鞘", "佩剑"],
     ["a straight blade held point down, the fuller running the length of it",
      "a sword laid flat, the edge a bright line down one side",
      "a hand closing on a grip wrapped in worn leather"]),
    ("Scabbard", "剑鞘", "a scabbard at the belt, the leather worn pale at the throat",
     ["剑鞘", "鞘", "佩", "挂"],
     ["a scabbard hanging at a belt, the throat worn pale where the blade passes",
      "an empty scabbard lying across a table, the strap curled",
      "the scabbard tip dragging on stone as the wearer walks"]),
    ("Round Shield", "圆盾", "a round shield, the boss in the centre, the face split and re-nailed",
     ["盾", "圆盾", "盾牌", "挡"],
     ["a round shield, the boss raised at the centre, the face split and re-nailed",
      "paint worn off a shield in patches, the wood showing through",
      "a shield held edge-on so only its thickness reads"]),
    ("Plate Armour", "板甲", "plate armour articulated at the elbow, the surface dulled by use",
     ["板甲", "盔甲", "甲", "护手", "头盔"],
     ["plate articulated at the elbow, the surface dulled except where it rubs",
      "a helmet with the visor raised, the inside dark",
      "gauntlet plates overlapping across the back of the hand"]),
]

MATERIALS = [
    ("Polished Blade", "剑刃钢", "a blade edge ground to a bright line, the bevel visible its full length",
     ["剑刃", "刃口", "磨亮", "钢", "反光"],
     ["a ground edge catching one line of light its full length",
      "the bevel visible as a change of angle, not a highlight",
      "a blade dulled in patches where it has been used"]),
    ("Chainmail", "锁子甲", "rings closed one by one, the surface reading as texture rather than shine",
     ["锁子甲", "链甲", "环", "铁环"],
     ["closed rings covering a surface, reading as texture not shine",
      "mail hanging heavy from a stand, the hem uneven",
      "one ring opened and re-closed, sitting proud of the rest"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    # 题材
    src = os.path.join(RAW, "subjects_v11.jsonl")
    out = os.path.join(RAW, "subjects_v12.jsonl")
    rows = load(src)
    k_en = next(k for k in rows[0] if k.endswith("_en"))
    k_zh = next(k for k in rows[0] if k.endswith("_zh"))
    n = len(rows)
    added = []
    for en, zh, phrase, kw, variants in SUBJECTS:
        for v in variants:
            n += 1
            added.append({"doc_id": f"s{n:04d}", "kind": "subject", k_en: en, k_zh: zh,
                          "phrase": phrase, "kw_zh": kw, "type": "object",
                          "description": v, "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"})
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  subjects: {len(rows)} -> {len(rows)+len(added)} (+{len(added)} / {len(SUBJECTS)} 项)")

    # 材质
    src2 = os.path.join(RAW, "materials_v10.jsonl")
    out2 = os.path.join(RAW, "materials_v11.jsonl")
    rows2 = load(src2)
    k_en2 = next(k for k in rows2[0] if k.endswith("_en"))
    k_zh2 = next(k for k in rows2[0] if k.endswith("_zh"))
    n2 = len(rows2)
    added2 = []
    for en, zh, phrase, kw, variants in MATERIALS:
        for v in variants:
            n2 += 1
            added2.append({"doc_id": f"m{n2:04d}", "kind": "material", k_en2: en, k_zh2: zh,
                           "phrase": phrase, "kw_zh": kw, "description": v,
                           "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"})
    with open(out2, "w", encoding="utf-8") as f:
        for r in rows2 + added2:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  materials: {len(rows2)} -> {len(rows2)+len(added2)} (+{len(added2)} / {len(MATERIALS)} 项)")
    print("\n### SWORD_DONE")


if __name__ == "__main__":
    main()
