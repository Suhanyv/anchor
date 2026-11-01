"""
第四批的问题

① 「跑」节拍吃掉了「追车」：夜里两辆车在桥上别，却给了"跑出两三步、脚步留下痕迹"。
   车不是人跑。给 跑 加 not，并补一条 追车 节拍。
② 缺场景：审讯室、法场、夜市、考场、车站月台
③ 缺节拍：审、跪、写、告别
④ 空气「烟」把夜市说成房间（"房间的重量先于台词到达"）——加 not 排除露天
"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# ① 跑 不吃车；补 追车
d = load("beat_ref.json")
if "跑" in d:
    ns = list(d["跑"].get("not") or [])
    for w in ("追车", "飙车", "车上", "两辆车", "开车", "车在"):
        if w not in ns:
            ns.append(w)
    d["跑"]["not"] = ns
if "追车" not in d:
    d["追车"] = {"kw": ["追车", "飙车", "别车", "两辆车"],
                 "mid": "两辆车贴得很近，车头一偏，另一辆跟着偏，轮胎冒烟",
                 "end": "停在两车之间只剩一条缝的那一帧"}
order = [k for k in d if not k.startswith("_")]
for k in ("追车",):
    if k in order:
        order.remove(k)
        order.insert(0, k)
for k in ("审", "跪", "写", "告别"):
    pass
newb = {
    "审": {"kw": ["审讯", "审问", "问了", "被问"],
           "mid": "问的人把同一句话换个说法再问一遍，被问的人没有立刻回答",
           "end": "停在沉默中间，谁都没有动"},
    "跪": {"kw": ["跪", "跪下", "跪着"],
           "mid": "膝盖压下去，上身还撑着，手在地面上找支撑",
           "end": "停在他终于把重量全放下去的那一下"},
    "写": {"kw": ["写", "写字", "记笔记", "答题"],
           "mid": "笔尖在纸上走，抬手换行，再落笔",
           "end": "停在笔还压在纸上、没有抬起来的时候"},
    "告别": {"kw": ["告别", "送别", "再见", "离开"],
             "mid": "两个人站着没动，其中一个先伸手或先开口，另一个接住",
             "end": "停在其中一个转身、另一个还没转身的那一刻"},
}
for k, v in newb.items():
    if k not in d:
        d[k] = v
        order.append(k)
for k, v in d.items():
    if k.startswith("_"):
        order.append(k)
save("beat_ref.json", {k: d[k] for k in order})
print("① 跑 排除:", d["跑"].get("not"))
print("   beat 总数:", len([k for k in order if not k.startswith("_")]))

# ② 场景
V_IN, V_OUT = "subjects_v22.jsonl", "subjects_v23.jsonl"
SCENES = [
    ("Interrogation", "审讯室", "a bare room, one lamp over a table, two chairs facing",
     ["审讯", "审讯室", "审问"], "审讯室：一张桌子，一盏灯压在桌上，两把椅子对着。"),
    ("ExecutionGround", "法场", "an open ground, a kneeling figure, crowd kept back",
     ["法场", "刑场", "斩"], "法场：空地，跪着的人，围观被拦在外面。"),
    ("NightMarket", "夜市", "a night market street, bulbs strung overhead, smoke from griddles",
     ["夜市", "小吃街", "大排档"], "夜市：灯泡串在头顶，油烟从铁板上起来。"),
    ("ExamHall", "考场", "rows of desks, heads down, papers and pens",
     ["考场", "考试", "答题"], "考场：一排排桌子，全是低着的头和纸笔。"),
    ("Platform", "车站月台", "a station platform, a train waiting, two figures facing",
     ["月台", "站台", "车站", "送别"], "车站月台：车停着，两个人面对面站着。"),
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
print(f"② subjects -> {V_OUT}（+{n}）")

# 声音 / 风险
d = load("sound_ref.json")
for k, v in {
    "审讯室": {"kw": ["审讯", "审问"], "zh": "灯管的电流声，椅子一次挪动，纸页翻过去",
               "en": "a tube light humming, a chair shifting once, a page turned"},
    "夜市": {"kw": ["夜市", "大排档", "小吃街"], "zh": "铁板上的油爆，人声混在一起，塑料袋和铁签碰",
             "en": "oil spitting on a griddle, overlapping voices, bags and skewers"},
    "考场": {"kw": ["考场", "考试", "答题"], "zh": "笔尖刮纸的声音很多但很轻，偶尔一声椅子响",
             "en": "many pens on paper, quiet, an occasional chair"},
    "月台": {"kw": ["月台", "站台", "送别"], "zh": "列车怠速的低鸣、气刹放气、广播在头顶",
             "en": "a train idling, air brakes, an announcement overhead"},
}.items():
    if k not in d:
        d[k] = v
print("③ 声音已补")

d2 = load("risk_ref.json")
for k, v in {
    "审讯": {"kw": ["审讯", "审问"], "risk": ["灯下人脸过曝丢细节", "椅子和桌子比例不对",
                                              "两个人的视线不在同一高度"]},
    "夜市": {"kw": ["夜市", "大排档"], "risk": ["灯泡串成一条亮线、看不清个数", "油烟糊住整张脸",
                                                "人群后排糊成同一张脸"]},
    "考场": {"kw": ["考场", "考试"], "risk": ["纸上的字变成乱码", "一排排桌子透视歪斜",
                                              "所有人低头角度完全一致、像复制"]},
}.items():
    if k not in d2:
        d2[k] = v
save("risk_ref.json", d2)
print("④ 风险已补")

# 空气「烟」排除露天
d3 = load("atmosphere_ref.json")
if "烟" in d3:
    ns = list(d3["烟"].get("not") or [])
    for w in ("夜市", "街头", "露天", "外面", "街上"):
        if w not in ns:
            ns.append(w)
    d3["烟"]["not"] = ns
save("atmosphere_ref.json", d3)
print("⑤ 空气·烟 排除露天:", d3["烟"]["not"])
