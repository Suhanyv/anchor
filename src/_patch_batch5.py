"""第五批缺口：太空舱/法庭/教室/手术室/山路 + 漂、发呆、缝合、背 四条节拍"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# 场景
V_IN, V_OUT = "subjects_v23.jsonl", "subjects_v24.jsonl"
SCENES = [
    ("Courtroom", "法庭", "a courtroom, a bench, a dock, papers stacked",
     ["法庭", "被告", "审判", "法官"], "法庭：审判台，被告席，案卷堆着。"),
    ("OR", "手术室", "an operating room, a lamp above the table, instruments laid out",
     ["手术室", "手术", "缝合", "麻醉"], "手术室：无影灯压在台面上，器械一排排摊开。"),
    ("MountainPath", "山路", "a mountain path of stone steps, brush at the edges",
     ["山路", "石阶", "挑夫", "盘山"], "山路：石头台阶，两边是草和灌木。"),
    ("Cabin", "太空舱", "a cramped spacecraft cabin, a round window, straps floating",
     ["太空舱", "舱内", "舷窗", "空间站"], "太空舱：狭小的舱室，圆形舷窗，束带浮着。"),
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
print(f"  场景 +{n} -> {V_OUT}")

# 声音
d = load("sound_ref.json")
before = set(d)
for k, v in {
    "法庭": {"kw": ["法庭", "审判", "被告"], "zh": "木槌一声，纸页翻动，很多人在很低的音量里清嗓子",
             "en": "a gavel, pages turned, a room of throats cleared quietly"},
    "手术室": {"kw": ["手术", "缝合", "无影灯"], "zh": "监护仪的规律提示音、金属器械放进托盘的一声",
               "en": "a monitor's steady tone, instruments set into a tray"},
    "山路": {"kw": ["山路", "石阶", "挑夫"], "zh": "风从坡上下来，扁担吱呀，脚步踩在石头上",
             "en": "wind down the slope, a carrying pole creaking, feet on stone"},
    "太空舱": {"kw": ["太空舱", "舷窗", "舱内"], "zh": "几乎没有声音，只有舱体的极低频和呼吸",
               "en": "almost nothing, a low hull resonance and breathing"},
}.items():
    if k not in d:
        d[k] = v
save("sound_ref.json", d)
print("  声音 +", sorted(set(d) - before))

# 风险
d2 = load("risk_ref.json")
before2 = set(d2)
for k, v in {
    "法庭": {"kw": ["法庭", "审判", "被告"], "risk": ["案卷上的字变成乱码", "人坐姿的比例不对",
                                                    "木槌和手的接触穿模"]},
    "手术室": {"kw": ["手术", "缝合", "无影灯"], "risk": ["器械穿进手里", "缝合线不跟针走",
                                                        "无菌布上的褶皱像塑料"]},
    "太空": {"kw": ["太空舱", "舷窗", "失重", "漂"], "risk": ["失重感不对、头发和衣角没浮起来",
                                                             "舱内透视歪斜", "舷窗外星空闪烁像噪点"]},
}.items():
    if k not in d2:
        d2[k] = v
save("risk_ref.json", d2)
print("  风险 +", sorted(set(d2) - before2))

# 节拍
d3 = load("beat_ref.json")
order = [k for k in d3 if not k.startswith("_")]
for k, v in {
    "漂": {"kw": ["漂", "失重", "浮着"], "mid": "身体缓慢转过去一点，头发和衣角先动，人后动",
           "end": "停在他伸手去够一个够不到的东西上"},
    "发呆": {"kw": ["发呆", "出神", "愣", "走神"], "mid": "视线不动，眼睛眨了一下，窗外的东西在动",
             "end": "停在有人叫了他、他还没回神的那一下"},
    "缝合": {"kw": ["缝合", "缝", "下针"], "mid": "镊子夹住，针进去又出来，线被拉直",
             "end": "停在剪线之前、线还绷着的那一帧"},
    "背": {"kw": ["背着", "挑", "扛", "扁担"], "mid": "上身前倾，重量往一边压，另一只手空出来调整",
           "end": "停在他换肩的那一刻，东西还压在背上"},
}.items():
    if k not in d3:
        d3[k] = v
        order.append(k)
for k in list(d3):
    if k.startswith("_"):
        order.append(k)
save("beat_ref.json", {k: d3[k] for k in order})
print("  节拍总数:", len([k for k in order if not k.startswith("_")]))
