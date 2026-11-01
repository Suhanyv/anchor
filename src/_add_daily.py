"""
补日常生活场景：菜市场、摊位、公交站、小饭馆、楼道、公园

为什么：测试里「一个女人在菜市场挑鱼」几乎全空——风格没匹配、
光=自然光、声音=占位符、风险=动物组。**类型片好办，日常难**，
因为日常没有视觉定式，全靠条目。
"""
import json
import os

RAW = r"F:\llm\data\raw"
V_IN, V_OUT = "subjects_v20.jsonl", "subjects_v21.jsonl"

# ---- 1) 场景 ----
SCENES = [
    ("Market", "菜市场", "a wet market aisle, produce stacked in crates, scales on the counters",
     ["菜市场", "市场", "摊位", "集市", "早市"],
     "菜市场：湿的地面，菜摊一层层堆着，秤和塑料袋在台面上。"),
    ("Stall", "鱼摊", "a fish stall, ice in a tray, a cleaver on the board",
     ["鱼摊", "鱼市", "卖鱼"], "鱼摊：冰上摆着鱼，砧板和刀就在旁边。"),
    ("Busstop", "公交车站", "a bus shelter at dusk, timetable glass, people standing apart",
     ["公交站", "车站", "站台", "等车"], "公交站：玻璃牌，几个人各自站着，车还没来。"),
    ("Diner", "小饭馆", "a small noodle shop, plastic stools, steam on the window",
     ["小饭馆", "面馆", "苍蝇馆子", "小吃店"], "小饭馆：塑料凳，窗上有雾气，灶台在角落。"),
    ("Stairwell", "楼道", "a stairwell of a walk-up, mailboxes, one bulb per landing",
     ["楼道", "楼梯间", "单元门"], "楼道：信箱一排，每层一盏灯。"),
    ("Park", "公园", "a park path, benches, trees and pigeons",
     ["公园", "长椅", "散步"], "公园：长椅、树、几只鸽子在脚边。"),
]

rows = [json.loads(l) for l in open(os.path.join(RAW, V_IN), encoding="utf-8") if l.strip()]
have = {r.get("subject_zh") for r in rows}
added = 0
for en, zh, phrase, kw, desc in SCENES:
    if zh in have:
        continue
    rows.append({"doc_id": f"s{len(rows)+1:04d}", "kind": "subject", "subject_en": en,
                 "subject_zh": zh, "phrase": phrase, "kw_zh": kw, "description": desc,
                 "text_semantic": f"{desc}，{zh}，" + "、".join(kw), "type": "scene"})
    added += 1
with open(os.path.join(RAW, V_OUT), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  subjects {V_IN} -> {V_OUT}: {len(rows)} 行（+{added} 场景）")


def add(fn, key, row):
    p = os.path.join(RAW, fn)
    d = json.load(open(p, encoding="utf-8"))
    if key in d:
        print(f"  跳过 {fn}·{key}")
        return
    d[key] = row
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  + {fn}·{key}")


# ---- 2) 声音 ----
add("sound_ref.json", "菜市场", {
    "kw": ["菜市场", "市场", "摊位", "集市", "早市", "鱼摊"],
    "zh": "周围全是人声和叫卖，秤砣落下的脆响，塑料袋被抖开",
    "en": "voices and calling, a scale weight dropping, plastic bags shaken open"})
add("sound_ref.json", "公园", {
    "kw": ["公园", "长椅", "鸽子", "散步"],
    "zh": "鸟叫、远处孩子、喷泉的水声，脚踩在落叶或砂石上",
    "en": "birds, children somewhere, a fountain, feet on leaves or gravel"})
add("sound_ref.json", "公交站", {
    "kw": ["公交站", "站台", "等车"],
    "zh": "发动机怠速、气刹放气、报站的女声从远处传来",
    "en": "an idling engine, air brakes releasing, a stop announcement far off"})

# ---- 3) 风险 ----
add("risk_ref.json", "菜市场", {
    "kw": ["菜市场", "市场", "摊位", "鱼摊", "集市"],
    "risk": ["摊上的菜糊成一片、分不出品种", "秤和价签上的字变成乱码",
             "手伸进东西里穿模"]})
add("risk_ref.json", "日常室内", {
    "kw": ["小饭馆", "楼道", "面馆", "厨房", "出租屋"],
    "risk": ["墙面和桌面上的字翻转", "灯光在镜头内跳动",
             "桌椅的透视与地面不接"]})

# ---- 4) 节拍：挑 / 递 ----
p = os.path.join(RAW, "beat_ref.json")
d = json.load(open(p, encoding="utf-8"))
if "挑" not in d:
    d["挑"] = {"kw": ["挑", "挑选", "翻看", "拣"],
               "mid": "手指拨开上面一层，拎起来看一眼，再放下或放进袋子",
               "end": "停在他手里还拿着的那件东西上"}
if "递" not in d:
    d["递"] = {"kw": ["递", "交给", "塞给"],
               "mid": "手伸过去，对方接住，两只手在画面中间碰一下",
               "end": "停在东西已经换了手、两边都还没收回的瞬间"}
order = [k for k in d if not k.startswith("_")]
for k in ("挑", "递"):
    order.remove(k)
    order.insert(order.index("拿") + 1 if "拿" in order else len(order), k)
d2 = {k: d[k] for k in (list(d.keys())[:0] + order)}
for k, v in d.items():
    if k.startswith("_"):
        d2[k] = v
json.dump(d2, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  beat 顺序:", [k for k in d2 if not k.startswith("_")][:10])
