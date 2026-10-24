"""
语料 v17：补 5 个中国商业类型片实体

为什么补
--------
LIMITATIONS.md 第五节记着：实体覆盖偏影展正典，缺中国商业类型片代表人物。
后果是描述中国神话/武侠/玄幻时，检索会落到不相关的西方导演上
（实测：「金色佛掌压制巨眼」最高分是索伦蒂诺 0.28，正确答案根本不在库里）。

补谁、为什么
------------
    乌尔善 Wuershan     神话史诗工业化的代表（封神三部曲 / 寻龙诀 / 画皮2）
    郭帆   Frant Gwo    中国科幻的尺度与工业质感（流浪地球系列）
    胡金铨 King Hu      武侠片的祖师，客栈与竹林的空间美学（侠女 / 龙门客栈 / 空山灵雨）
    程小东 Ching Siu-tung  威亚与飘逸动作美学（倩女幽魂 / 东方不败）
    饺子   Jiaozi       中国三维动画的高光（哪吒之魔童降世）

写作原则（吸取前面的教训）
--------------------------
1. **只写有把握的视觉特征**，不写"构图精巧""意境深远"这类空话
2. 每条锚定**具体物件或表象**（青铜纹样、行星发动机、客栈楼梯、衣袂、红莲）
3. **不写评论**（不写"最好""开创性"），只写画面
4. 每位 6 条，base 面 3 条 + 1~2 个具体面 3 条，图像与视频混排

corpus_v16 (796) -> corpus_v17
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v17.jsonl")

STYLE = {
    "raw": {"ar": "2.35:1", "style": "raw"},
}

# (中文名, 英文名, 国家, 年代, 基础标签)
DIRECTORS = [
    ("乌尔善", "Wuershan", "CN", "2010s-2020s",
     ["mythic scale", "bronze ornament", "ritual choreography", "earth and ochre palette"]),
    ("郭帆", "Frant Gwo", "CN", "2010s-2020s",
     ["planetary scale machinery", "frozen surface", "industrial detail", "cold blue-grey"]),
    ("胡金铨", "King Hu", "TW", "1960s-1970s",
     ["inn interior standoff", "bamboo grove", "smoke and dust", "percussive editing"]),
    ("程小东", "Ching Siu-tung", "HK", "1980s-1990s",
     ["wire-work flight", "sleeves and ribbons", "drifting mist", "maple red"]),
    ("饺子", "Jiaozi", "CN", "2010s-2020s",
     ["3d animation", "exaggerated expression", "ink-brush effects", "lotus fire"]),
]

# 每位：[(facet, domain, 描述, kw_zh, 标签)]
DOCS = {
    "乌尔善": [
        ("base", "prompt_image",
         "a bronze-masked army standing in ranks on a wide earth plain, "
         "ornament cast in relief on the armour, low sun raking across dust",
         ["青铜", "铠甲", "军阵", "黄土", "低角度阳光"]),
        ("base", "prompt_image",
         "a colossal beast carved in bronze pattern rising behind a walled city, "
         "ochre and dull gold, smoke drifting at its feet",
         ["巨兽", "青铜纹", "城墙", "橙金", "烟"]),
        ("base", "prompt_video",
         "an army crossing an open earth plain at dusk, dust lifted by the march, "
         "low sun behind them, slow lateral drift",
         ["军阵", "黄昏", "尘土", "横移"]),
        ("ritual_dance", "prompt_image",
         "young warriors in heavy armour performing a synchronised war dance, "
         "torches, sweat, armour plates catching a hard orange light",
         ["战舞", "质子", "火把", "铠甲", "橙光"]),
        ("ritual_dance", "prompt_video",
         "a war dance in a torchlit courtyard, bodies moving in unison, "
         "ash in the air, slow circling camera",
         ["战舞", "火把", "庭院", "环形运镜"]),
        ("ritual_dance", "prompt_image",
         "a ritual altar of bronze vessels on stone steps, offered grain and wine, "
         "priests in layered robes, smoke rising",
         ["祭祀", "青铜器", "台阶", "烟"]),
    ],
    "郭帆": [
        ("base", "prompt_image",
         "a planetary engine rising above a frozen plain, ice and steel, "
         "cold blue-grey light, exhaust flaring into a dark sky",
         ["行星发动机", "冰原", "钢铁", "冷蓝灰"]),
        ("base", "prompt_image",
         "the interior of an underground city, tiers of housing stacked under a raw ceiling, "
         "warm lamps against cold concrete",
         ["地下城", "分层居住", "混凝土", "暖灯"]),
        ("base", "prompt_video",
         "a convoy of heavy transports crossing a frozen surface toward a distant engine, "
         "slow forward push, cold haze",
         ["车队", "冰封地表", "远景", "前推"]),
        ("mega_structure", "prompt_image",
         "a structure so large that clouds form under its overhang, tiny figures on a gantry, "
         "haze compressing the scale",
         ["巨构", "云层", "小人影", "雾霾"]),
        ("mega_structure", "prompt_image",
         "a space elevator cable disappearing into low cloud, ice on the guide rails, "
         "cold grey sky",
         ["太空电梯", "缆绳", "低云", "冰"]),
        ("mega_structure", "prompt_video",
         "camera tilting up the face of an engine until its top leaves frame, "
         "steam venting sideways",
         ["仰拍", "发动机", "蒸汽"]),
    ],
    "胡金铨": [
        ("base", "prompt_image",
         "the interior of an old inn, wooden stairs and lattice windows, "
         "dust in a shaft of light, figures held still on either side",
         ["客栈", "木楼梯", "格栅窗", "光柱", "对峙"]),
        ("base", "prompt_image",
         "a bamboo grove in fog, trunks repeating into the distance, "
         "a figure half hidden, smoke drifting low",
         ["竹林", "雾", "重复的竹干", "烟"]),
        ("base", "prompt_video",
         "two groups facing each other across a courtyard, then a sudden burst of movement, "
         "cut hard on the action",
         ["对峙", "庭院", "突然加速", "硬切"]),
        ("inn_standoff", "prompt_image",
         "a table in an inn, a sword laid on it, hands resting near, "
         "lantern light low and warm",
         ["客栈", "桌", "剑", "灯笼"]),
        ("inn_standoff", "prompt_image",
         "a corridor of the inn seen in depth, doors on both sides, "
         "one figure at the far end in silhouette",
         ["走廊", "纵深", "剪影"]),
        ("inn_standoff", "prompt_video",
         "a leap from a balcony landing on a table, dust rising, "
         "camera holding still through the move",
         ["跃下", "桌", "灰尘", "静止镜头"]),
    ],
    "程小东": [
        ("base", "prompt_image",
         "a figure in layered robes suspended mid-air on a wire, sleeves trailing, "
         "mist behind, pale cold light",
         ["威亚", "悬空", "衣袖", "薄雾", "冷光"]),
        ("base", "prompt_image",
         "a long white sleeve unrolling through the frame, the figure at its end blurred by motion",
         ["长袖", "飘动", "动态模糊"]),
        ("base", "prompt_video",
         "a figure drifting down through falling maple leaves, ribbons turning, "
         "slow vertical descent",
         ["飘落", "枫叶", "飘带", "下降"]),
        ("wire_flight", "prompt_image",
         "a swordsman launching across a courtyard, robe pulled straight by the speed, "
         "dust pushed out behind",
         ["轻功", "掠起", "衣袍", "尘土"]),
        ("wire_flight", "prompt_video",
         "two figures crossing in mid-air above a forest canopy, robes tangling, "
         "camera tracking with them",
         ["空中交错", "树冠", "跟拍"]),
        ("wire_flight", "prompt_image",
         "a pale ghost bride in drifting mist under a moon, red silk against grey",
         ["白衣", "薄雾", "月", "红绸"]),
    ],
    "饺子": [
        ("base", "prompt_image",
         "a 3d animated boy with an exaggerated grin, hair lifting in a hot updraft, "
         "stylised fire around him",
         ["三维动画", "夸张表情", "火焰", "热浪"]),
        ("base", "prompt_image",
         "ink-brush smoke bursting outward in a stylised shockwave, "
         "3d forms inside the ink, red and black",
         ["水墨", "冲击波", "红黑", "三维"]),
        ("base", "prompt_video",
         "a 3d animated figure leaping through a ring of flame, the camera whipping around, "
         "ink strokes trailing the motion",
         ["三维动画", "火环", "环绕运镜", "墨线"]),
        ("lotus_fire", "prompt_image",
         "a lotus of red flame opening around a standing figure, "
         "embers rising, dark ground",
         ["红莲", "火焰", "火星", "暗地"]),
        ("lotus_fire", "prompt_image",
         "a stylised sea of fire and cloud under a hanging sky, "
         "painted texture on the 3d surfaces",
         ["火海", "云", "贴图质感", "绘画感"]),
        ("lotus_fire", "prompt_video",
         "flame gathering into a ring then collapsing inward, "
         "stylised smoke, camera pushing in",
         ["火焰成形", "收拢", "推近"]),
    ],
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)
    print(f"corpus_v16: {len(corpus)} 条，最大 id d{n:04d}")

    added = []
    for zh, en, country, era, tags in DIRECTORS:
        for facet, domain, desc, kw in DOCS[zh]:
            n += 1
            doc = {
                "doc_id": f"d{n:04d}",
                "domain": domain,
                "lang": "en",
                "director": en,
                "director_zh": zh,
                "country": country,
                "era": era,
                "facet": facet,
                "style_tags": tags[:4],
                "kw_zh": kw,
                "batch": "中国类型片补充",
                "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": dict(STYLE["raw"]),
                "prompt": (f"cinematic {'video' if domain == 'prompt_video' else 'still'}, "
                           f"{desc}, in the style of {en}, --ar "
                           f"{'21:9' if domain == 'prompt_video' else '2.35:1'} --style raw"),
            }
            if domain == "prompt_video":
                doc["motion"] = "SLOW"
                doc["params"] = {"ar": "21:9", "duration": "5s", "camera": "slow"}
            added.append(doc)

    out = corpus + added
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"新增 {len(added)} 条（5 个实体 x 6 条）")
    print(f"corpus_v16 -> v17 : {len(corpus)} -> {len(out)}")
    print()
    for zh, en, *_ in DIRECTORS:
        rows = [a for a in added if a["director_zh"] == zh]
        print(f"  {zh:<6} {en:<16} {len(rows)} 条  {[a['facet'] for a in rows]}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V17_DONE")


if __name__ == "__main__":
    main()
