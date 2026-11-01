"""
补两处（以及我自己补丁里的一个错：上一个脚本忘了 save 声音表）

① 声音表保存 —— 上一版只改了内存里的 dict，没落盘
② 法场要有声音和风险
③ 夜市要有一条节拍（逛）
"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# ① + ② 声音
d = load("sound_ref.json")
before = set(d)
for k, v in {
    "审讯室": {"kw": ["审讯", "审问"], "zh": "灯管的电流声，椅子一次挪动，纸页翻过去",
               "en": "a tube light humming, a chair shifting once, a page turned"},
    "法场": {"kw": ["法场", "刑场"], "zh": "很多人在低声说话，铁器碰在地上，风把旗子吹得响",
             "en": "a crowd murmuring, iron set down on stone, a banner snapping"},
    "夜市": {"kw": ["夜市", "大排档", "小吃街"], "zh": "铁板上的油爆，人声混在一起，塑料袋和铁签碰",
             "en": "oil spitting on a griddle, overlapping voices, bags and skewers"},
    "考场": {"kw": ["考场", "考试", "答题"], "zh": "笔尖刮纸的声音很多但很轻，偶尔一声椅子响",
             "en": "many pens on paper, quiet, an occasional chair"},
    "月台": {"kw": ["月台", "站台", "送别"], "zh": "列车怠速的低鸣、气刹放气、广播在头顶",
             "en": "a train idling, air brakes, an announcement overhead"},
}.items():
    if k not in d:
        d[k] = v
save("sound_ref.json", d)
print("① 声音表已保存，新增:", sorted(set(d) - before))

# ② 法场风险
d2 = load("risk_ref.json")
if "法场" not in d2:
    d2["法场"] = {"kw": ["法场", "刑场", "斩", "跪下"],
                  "risk": ["围观人群糊成一片、没有个体", "铁器的形制不像这个年代",
                           "跪姿的膝盖陷进地面"]}
    save("risk_ref.json", d2)
    print("② + risk·法场")

# ③ 夜市节拍：逛
d3 = load("beat_ref.json")
if "逛" not in d3:
    d3["逛"] = {"kw": ["夜市", "逛", "摊位前", "大排档"],
                "mid": "脚步放慢，在一个摊前停一下，又继续往前挪",
                "end": "停在人已经走开、油烟还留在原地的画面上"}
    order = [k for k in d3 if not k.startswith("_")]
    order.remove("逛")
    order.insert(order.index("走") + 1 if "走" in order else len(order), "逛")
    for k in list(d3):
        if k.startswith("_"):
            order.append(k)
    save("beat_ref.json", {k: d3[k] for k in order})
    print("③ + beat·逛")

import sys
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
dd = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = dd["模型目录"][1]["default"], dd["语料文件"][1]["default"]
S, K, MT = (dd["题材文件"][1]["default"], dd["工艺文件"][1]["default"],
            dd["材质文件"][1]["default"])
for q in ("审讯室里，一个人被问了三个小时", "古代法场，一个犯人跪着",
          "夜市里，油烟和灯泡底下全是人"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    snd = [x for x in out.split("。") if x.startswith("只使用")]
    bt = [x for x in out.split("。") if x.startswith(("2 到", "3 到"))]
    print(f"\n  {q[:16]}")
    print("    声 " + (snd[0][6:40] if snd else "<空>"))
    print("    节 " + (bt[0][:40] if bt else "<空>"))
