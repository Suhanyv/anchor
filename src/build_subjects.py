"""
题材库（内容维度）：用户「画什么」，与「什么风格」正交

为什么独立建库、独立索引
------------------------
之前把 350 条视频文档塞进风格索引，导致风格精度掉 1.5pp（消融实测）。
题材词（骑士/唐代/赛博）和风格词（对称/深焦/自然光）如果混在同一个向量空间，
会互相抢 -> 两条平行通道，各自排序，最后拼接。

数据形状
--------
每个题材 2 条英文变体（提高措辞鲁棒性），字段：
    doc_id, kind="subject", subject_en, subject_zh, phrase(输出用), kw_zh, text_semantic

覆盖范围
--------
按用户实际用途（视频生成 + 游戏美术 + 历史题材）选，不求全，求具体。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "subjects_v1.jsonl")

# (英文名, 中文名, 输出短语, [英文变体描述], [中文关键词])
SUBJECTS = [
    ("Medieval Knight", "中世纪骑士",
     "a knight in plate armour on a horse, castle walls behind",
     ["a knight in full plate armour mounted on a horse",
      "an armoured rider with a lance before stone castle walls"],
     ["骑士", "盔甲", "城堡", "中世纪", "骑马"]),

    ("Medieval Battlefield", "中世纪战场",
     "a muddy battlefield with banners, spears and armoured men",
     ["armoured soldiers advancing across a churned muddy field",
      "banners and spears crowded on a smoking battlefield"],
     ["战场", "军队", "旗帜", "长矛", "厮杀"]),

    ("Tang Court", "唐代宫廷",
     "a Tang dynasty palace hall with red lacquered pillars and silk hangings",
     ["a wide Tang palace hall, vermilion pillars, silk drapery",
      "court ladies in Tang dress beneath painted beams"],
     ["唐代", "宫廷", "宫殿", "考究", "古装"]),

    ("Republican Shanghai", "民国上海",
     "a 1930s Shanghai street with rickshaws, qipao and neon signage",
     ["a narrow 1930s Shanghai lane with rickshaws and hanging signs",
      "a woman in a qipao on a wet Republican-era street"],
     ["民国", "上海", "旗袍", "老上海", "年代感"]),

    ("Wuxia Bamboo Grove", "武侠竹林",
     "two swordsmen facing each other in a dense bamboo grove",
     ["a swordsman standing among tall green bamboo",
      "two figures with drawn swords in wind-blown bamboo"],
     ["武侠", "竹林", "剑客", "江湖", "对决"]),

    ("Cyberpunk Street", "赛博朋克都市",
     "a rain-soaked cyberpunk street with holographic signs and steam",
     ["a cramped alley of neon signs and holograms in the rain",
      "a future street of stacked signage, cables and wet reflections"],
     ["赛博朋克", "霓虹", "未来都市", "科幻", "蒸汽"]),

    ("Spacecraft Interior", "太空船内",
     "the cramped interior of a spacecraft, panels and cold light",
     ["a narrow spacecraft corridor of metal panels",
      "a cockpit of switches and cold blue instrument light"],
     ["太空", "飞船", "飞船内部", "舱内", "科幻"]),

    ("Underwater", "水下",
     "a figure drifting underwater, shafts of light from above",
     ["a body suspended in deep blue water, light shafts",
      "a swimmer sinking through murky green water"],
     ["水下", "海底", "潜水", "深水"]),

    ("Snowfield", "雪原",
     "an empty snowfield with one small dark figure",
     ["a vast white snow plain under a pale sky",
      "a lone figure crossing a blank snowfield"],
     ["雪", "雪原", "雪地", "白茫茫"]),

    ("Desert Caravan", "沙漠商队",
     "a camel caravan crossing high dunes in heat haze",
     ["camels and robed riders on a ridgeline of dunes",
      "a caravan track across rippled sand"],
     ["沙漠", "骆驼", "商队", "沙丘"]),

    ("Ruined City", "废墟城市",
     "a ruined city of broken concrete, rebar and empty windows",
     ["collapsed concrete floors open to the sky",
      "a gutted building with rebar and rubble"],
     ["废墟", "破败", "断壁", "残垣"]),

    ("Wheat Field", "麦田",
     "a wheat field rippling in wind under a wide sky",
     ["golden wheat moving in waves of wind",
      "a path cut through tall ripe wheat"],
     ["麦田", "田野", "麦子", "金黄"]),

    ("Hotel Corridor", "旅馆走廊",
     "a long hotel corridor with numbered doors and carpet",
     ["an endless corridor of identical doors and wall lamps",
      "a dim hotel hallway with patterned carpet"],
     ["走廊", "旅馆", "酒店", "门"]),

    ("Rainy Night Street", "雨夜街道",
     "a wet street at night, signs reflecting in puddles",
     ["a rain-slicked road with smeared reflections of signs",
      "empty night street shining with rain"],
     ["雨夜", "街道", "下雨", "积水"]),

    ("Old Kitchen", "老式厨房",
     "a worn kitchen with enamel pots and tiled walls",
     ["a cramped kitchen of old enamel and chipped tile",
      "steam over a battered stove in a small kitchen"],
     ["厨房", "灶台", "锅", "老房子"]),

    ("Empty Classroom", "空教室",
     "an empty classroom with wooden desks and afternoon light",
     ["rows of worn wooden desks in a silent classroom",
      "sunlight across empty school desks"],
     ["教室", "课桌", "学校", "空荡"]),

    ("Church Interior", "教堂内部",
     "a vaulted church interior with stained glass and dust in the light",
     ["tall stone columns and coloured light from stained glass",
      "an empty nave with shafts of light through high windows"],
     ["教堂", "彩窗", "穹顶", "礼拜堂"]),

    ("Crowded Market", "集市人群",
     "a crowded market street of stalls, awnings and passing people",
     ["dense stalls under cloth awnings, buyers pressing through",
      "a narrow market lane packed with goods and people"],
     ["集市", "人群", "摊位", "热闹"]),

    ("Old Man Close-Up", "老人特写",
     "a close portrait of an old man's weathered face",
     ["the lined face of an elderly man filling the frame",
      "close on an old man's eyes and deep wrinkles"],
     ["老人", "特写", "脸", "皱纹"]),

    ("Galloping Horses", "奔马",
     "horses galloping, dust rising from the ground",
     ["a horse at full gallop throwing up dust",
      "several horses running hard across open ground"],
     ["马", "奔马", "奔跑", "疾驰"]),
]


def main():
    rows = []
    n = 0
    for en, zh, phrase, variants, kws in SUBJECTS:
        for v in variants:
            n += 1
            rows.append({
                "doc_id": f"s{n:04d}",
                "kind": "subject",
                "subject_en": en,
                "subject_zh": zh,
                "phrase": phrase,
                "kw_zh": kws,
                "description": v,
                "text_semantic": v,
            })
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"题材库: {len(SUBJECTS)} 个题材 / {len(rows)} 条文档 -> {OUT}")
    print()
    for en, zh, phrase, variants, kws in SUBJECTS[:6]:
        print(f"  {zh:<8} [{en}]")
        print(f"    输出短语: {phrase}")
        print(f"    中文词  : {kws}")
    print("  ...")
    # 检查中文关键词覆盖
    allkw = set()
    for _, _, _, _, kws in SUBJECTS:
        allkw |= set(kws)
    print(f"\n中文关键词共 {len(allkw)} 个，无重复检查：",
          "OK" if sum(len(k) for *_, k in SUBJECTS) == len(allkw) else "有重复（可接受）")
    print("\n### SUBJECTS_DONE")


if __name__ == "__main__":
    main()
