"""
补人物与草：武士 / 剑客 / 浪人 / 武将 / 侠客 / 芒草

为什么
------
实测：查询「雪天，两个武士在长满狗尾巴草山上对决」
    主体找到的是「武侠竹林」0.3707（场景），武士完全没有。

库里 127 个实体里，人物只有 老人/工人/学生/新娘/军人/医生，
**没有一个"古代持械的人"**。而武侠、剑戟片是我们最常拍的东西。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "subjects_v14.jsonl")
OUT = os.path.join(RAW, "subjects_v15.jsonl")

ITEMS = [
    ("Samurai", "武士", "character",
     "a samurai in layered armour, sword held low at his side, snow on his shoulders",
     ["武士", "侍", "刀", "甲胄", "决斗"],
     "武士：层叠甲胄，刀垂在身侧，肩上落雪。"),
    ("Swordsman", "剑客", "character",
     "a swordsman standing still, the blade not yet drawn, coat moving in the wind",
     ["剑客", "剑", "侠客", "江湖", "对决"],
     "剑客：人不动，剑未出鞘，衣角在风里。"),
    ("Ronin", "浪人", "character",
     "a masterless ronin in a worn straw hat, dust on his hem, one hand on the hilt",
     ["浪人", "游侠", "斗笠", "落魄", "浪迹"],
     "浪人：无主的武士，旧斗笠，下摆沾泥，单手按着刀柄。"),
    ("Warlord", "武将", "character",
     "an armoured warlord on horseback, banner behind him, face weathered",
     ["武将", "将军", "主帅", "骑兵", "旗"],
     "武将：甲胄骑将，身后有旗，脸上带风霜。"),
    ("Knight Errant", "侠客", "character",
     "a lone wanderer in plain robes facing a crowd, unarmed until the last moment",
     ["侠客", "侠", "游侠", "独行", "义"],
     "侠客：粗布衣，独自面对一群人，最后一刻才出手。"),
    ("Silvergrass", "芒草", "object",
     "silvergrass covering a hillside in waves, seed heads catching the light",
     ["芒草", "狗尾巴草", "野草", "山坡", "草丛"],
     "芒草：漫山遍野的细穗，风一过整片倒伏，穗头接光。"),
]


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    have = {r.get("subject_zh") for r in rows}
    added = 0
    for en, zh, typ, phrase, kw, desc in ITEMS:
        if zh in have:
            print(f"  跳过（已存在）{zh}")
            continue
        rows.append({
            "doc_id": f"s{len(rows)+1:04d}",
            "kind": "subject",
            "subject_en": en,
            "subject_zh": zh,
            "phrase": phrase,
            "kw_zh": kw,
            "description": desc,
            "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
            "type": typ,
        })
        added += 1
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  subjects_v14 -> v15 : {len(rows)} 行（+{added}）")
    print("\n### WARRIOR_KB_DONE")


if __name__ == "__main__":
    main()
