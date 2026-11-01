"""
第三批暴露的问题

① bug：光位为空时，把材质/工艺的 zh 当光填进去了。
   实测「修车工钻在车底下」的光写成「喷漆钢」——材质不是光。删掉这个兜底。
② 缺条目：理发店、阳台、婚礼
③ 缺声音：理发剪刀、晾衣抖布、婚宴碰杯
④ 缺风险：理发（镜子/反光）、晾衣（衣形）、婚宴（人多脸糊）
⑤ 缺节拍：擦、钻、晾、敬酒
"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# ---- ① 删掉"材质/工艺冒充光"的兜底 ----
P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()
old = '''        if mat and mat.get("hit"):
            zh_light.append(mat.get("zh") or "")
        if craft and craft.get("hit"):
            zh_light.append(craft.get("zh") or "")'''
new = '''        # 曾经在这里把材质/工艺的 zh 当光填，实测输出「喷漆钢」——
        # 材质不是光源，宁可空着让模板留占位符，也不能拿它冒充光。'''
assert old in s, "光兜底没匹配"
s = s.replace(old, new, 1)
import ast
ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("① 删掉材质冒充光的兜底")

# ---- ② 场景 ----
V_IN, V_OUT = "subjects_v21.jsonl", "subjects_v22.jsonl"
SCENES = [
    ("Barber", "理发店", "a barber chair facing a mirror, clippers and combs on the shelf",
     ["理发店", "剃头", "理发", "剪头发"], "理发店：转椅正对着镜子，架子上是推子和梳子。"),
    ("Balcony", "阳台", "a balcony at dusk, laundry line, brick wall, buildings beyond",
     ["阳台", "晾衣服", "晒被子"], "阳台：晾衣杆横着，砖墙，外面是别的楼。"),
    ("Banquet", "婚宴", "a banquet table, red tablecloth, glasses raised, faces around",
     ["婚礼", "婚宴", "敬酒", "酒席"], "婚宴：红桌布，一圈酒杯举起来，脸挤在一处。"),
]
rows = [json.loads(l) for l in open(os.path.join(RAW, V_IN), encoding="utf-8") if l.strip()]
have = {r.get("subject_zh") for r in rows}
n = 0
for en, zh, phrase, kw, desc in SCENES:
    if zh in have:
        continue
    rows.append({"doc_id": f"s{len(rows)+1:04d}", "kind": "subject", "subject_en": en,
                 "subject_zh": zh, "phrase": phrase, "kw_zh": kw, "description": desc,
                 "text_semantic": f"{desc}，{zh}，" + "、".join(kw), "type": "scene"})
    n += 1
with open(os.path.join(RAW, V_OUT), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"② subjects {V_IN} -> {V_OUT}（+{n}）")

# ---- ③ 声音 ----
d = load("sound_ref.json")
for k, v in {
    "理发店": {"kw": ["理发", "剃头", "推子", "剪刀"],
               "zh": "电推子的嗡鸣忽高忽低，剪刀在耳朵边合拢的脆响，椅子转轴一声",
               "en": "clippers rising and falling, scissors closing near an ear, a chair swivelling"},
    "阳台": {"kw": ["阳台", "晾衣", "晒"],
             "zh": "布被抖开的一声，衣架挂上杆子，楼下很远有人在说话",
             "en": "a sheet snapped open, a hanger set on the rail, voices far below"},
    "婚宴": {"kw": ["婚礼", "婚宴", "敬酒", "酒席"],
             "zh": "很多杯碰在一起，笑和说话叠着，椅子在地面上蹭",
             "en": "many glasses meeting at once, laughter over speech, chairs scraping"},
}.items():
    if k not in d:
        d[k] = v
        print(f"③ + sound·{k}")
save("sound_ref.json", d)

# ---- ④ 风险 ----
d = load("risk_ref.json")
for k, v in {
    "理发": {"kw": ["理发", "剃头", "推子", "剪刀"],
             "risk": ["镜子里的倒影与本人不同步", "推子和头发糊在一起",
                      "手指握着刀剪时数量不对"]},
    "晾衣": {"kw": ["晾衣", "晒", "衣架", "床单"],
             "risk": ["挂着的衣服形状不像布、像硬片", "布被风吹动时穿帮",
                      "晾衣杆的透视歪了"]},
    "婚宴": {"kw": ["婚宴", "婚礼", "敬酒", "酒席"],
             "risk": ["后排人脸糊成同一张", "所有人的动作同步得像复制",
                      "杯子与手的接触处穿模"]},
}.items():
    if k not in d:
        d[k] = v
        print(f"④ + risk·{k}")
save("risk_ref.json", d)

# ---- ⑤ 节拍 ----
d = load("beat_ref.json")
newb = {
    "擦": {"kw": ["擦", "擦拭", "抹"], "mid": "手在一块表面上反复推两三下，擦过的地方反光不一样",
           "end": "停在他收手看了一眼的那一下"},
    "钻": {"kw": ["钻", "钻到", "钻进"], "mid": "人往里挪，只剩半截身子在外面，工具声从里面传出来",
           "end": "停在只能看见鞋和腿的画面上"},
    "晾": {"kw": ["晾", "挂", "抖开"], "mid": "把布抖开，抬手挂上去，衣角还在晃",
           "end": "停在布已经挂好、还在轻微摆动的那一刻"},
    "敬酒": {"kw": ["敬酒", "举杯", "碰杯"], "mid": "杯子举起来，几只碰在一起，人往后仰一点喝下去",
             "end": "停在杯子放下、还没落桌的位置"},
}
order = [k for k in d if not k.startswith("_")]
for k, v in newb.items():
    if k not in d:
        d[k] = v
        order.append(k)
        print(f"⑤ + beat·{k}")
for k, v in d.items():
    if k.startswith("_"):
        order.append(k)
save("beat_ref.json", {k: d[k] for k in order})
print("   beat 总数:", len([k for k in order if not k.startswith("_")]))
