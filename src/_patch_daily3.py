"""
补六条日常测试暴露的缺口

① 「纸箱穿模」写在"雨"的风险里——那是某一次具体场景的产物，
   打伞等车的镜头根本不该带"纸箱"。拆成独立的「道具」风险组。
② 声音缺：电梯、数钱、抽烟
③ 节拍缺：数、抽
④ 风险「现代室内」把货架和厨房混在一起——便利店才有货架
"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# ① 雨的风险拆出「纸箱」
d = load("risk_ref.json")
if "雨" in d:
    d["雨"]["risk"] = [r for r in d["雨"]["risk"] if "纸箱" not in r]
if "道具" not in d:
    d["道具"] = {
        "kw": ["纸箱", "箱子", "包裹", "手提箱", "塑料袋", "伞"],
        "risk": ["手提物件的边缘穿模", "拿东西的手指数量不对", "物件重量感不对、像飘着"],
    }
    save("risk_ref.json", d)
print("  雨的风险:", d["雨"]["risk"])
print("  + 道具风险组")

# ④ 现代室内拆开：便利店 / 厨房
if "现代室内" in d:
    d["现代室内"]["kw"] = ["便利店", "办公室", "教室", "医院", "公寓", "卧室", "走廊"]
    d["现代室内"]["risk"] = ["货架/桌面上的文字翻转", "日光灯频闪做成了闪烁故障",
                              "门与窗的透视在两镜间不一致"]
if "厨房" not in d:
    d["厨房"] = {
        "kw": ["厨房", "做饭", "灶台", "锅", "炒菜", "切菜"],
        "risk": ["锅里东西糊成一坨、分不出食材", "手上的刀和食材穿模",
                 "蒸汽方向和火的位置不一致"],
    }
save("risk_ref.json", d)
print("  现代室内/厨房已拆分")

# ② 声音
d = load("sound_ref.json")
adds = {
    "电梯": {"kw": ["电梯", "电梯口", "楼层"], "zh": "电机在头顶转，轿厢到站的提示音，门开的摩擦",
             "en": "a motor overhead, an arrival chime, doors sliding"},
    "数钱": {"kw": ["数钱", "点钞", "钱"], "zh": "纸币被手指捻开的声音，纸边互相摩擦，很轻但很清楚",
             "en": "paper money being counted, edges rubbing, quiet but distinct"},
    "抽烟": {"kw": ["抽烟", "点烟", "烟"], "zh": "打火机一声，吸气时的细响，烟灰落下的轻响",
             "en": "a lighter, a draw of breath, ash falling"},
}
for k, v in adds.items():
    if k not in d:
        d[k] = v
        print(f"  + sound·{k}")
save("sound_ref.json", d)

# ③ 节拍
d = load("beat_ref.json")
newb = {
    "数": {"kw": ["数钱", "点钞", "数"],
           "mid": "手指捻开一层，停一下，再往下数，嘴在动但没出声",
           "end": "停在他抬眼的那一下，手里的钱还没放下"},
    "抽": {"kw": ["抽烟", "点烟", "吸一口"],
           "mid": "抬手吸一口，烟嘘出来，眼睛看着某个没在看的东西",
           "end": "停在烟还在往上飘、人已经不动的那一刻"},
}
order = [k for k in d if not k.startswith("_")]
for k, v in newb.items():
    if k not in d:
        d[k] = v
        order.append(k)
        print(f"  + beat·{k}")
for k, v in d.items():
    if k.startswith("_"):
        order.append(k)
d2 = {k: d[k] for k in order}
save("beat_ref.json", d2)
print("  beat 顺序:", [k for k in d2 if not k.startswith("_")])
