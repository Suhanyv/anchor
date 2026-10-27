"""
光表补一条：绿月光（类型片专用）

为什么
------
「道士和僵尸对打」风格已经能查到僵尸片，但光那一栏是空的。
僵尸片的光是有定式的：绿月亮、烛火、香火烟。
光表里只有中性的「月光」「烛光」，没有能对上"僵尸/义庄"的词。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "raw", "light_ref.json")

light = json.load(open(P, encoding="utf-8"))
if "绿月光" not in light:
    light["绿月光"] = {
        "zh": "绿月光的夜，冷绿从上方压下来，烛火是唯一的暖色，烟在光里悬着",
        "en": "green moonlight from above, a single warm candle as the only "
              "warm source, incense smoke suspended in the beam",
        "kw": ["僵尸", "义庄", "道观", "鬼", "灵堂", "夜路", "做法"],
    }
    json.dump(light, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("  光表 +1：绿月光")
print(f"  光表共 {len([k for k in light if not k.startswith('_')])} 条")
print("\n### GREEN_MOON_DONE")
