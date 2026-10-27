"""
补港式僵尸片：类型风格 + 道士 / 僵尸 / 义庄 / 符纸 / 桃木剑

为什么
------
实测「一个道士，和僵尸对打，六个镜头」：
    风格 乌尔善 0.2802（弱匹配，直接说"没有"）
    主体 武侠竹林 0.3060（场景，不是人）

库里没有僵尸片这个类型，也没有道士、僵尸、符纸。
僵尸片是明确的视觉传统（1980 年代港片），和 废土 / 黑色电影 / 浮世绘 一样
按"类型实体"加，不挂在某个导演名下。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
CORPUS_SRC = os.path.join(RAW, "corpus_v25.jsonl")
CORPUS_OUT = os.path.join(RAW, "corpus_v26.jsonl")
SUBJ_SRC = os.path.join(RAW, "subjects_v18.jsonl")
SUBJ_OUT = os.path.join(RAW, "subjects_v19.jsonl")

# ---- 类型风格：港式僵尸片 ----
STYLE = {
    "director": "Hong Kong Jiangshi Film",
    "director_zh": "僵尸片",
    "country": "HK",
    "era": "1980s",
    "style_tags": ["green moonlight", "paper talismans", "candle smoke",
                   "cheap studio fog", "hand-painted backdrops"],
    "kw_zh": ["僵尸", "道士", "符纸", "义庄", "跳尸"],
    "docs": [
        ("a stiff figure in Qing dynasty robes hopping toward the camera, "
         "arms straight out, paper talisman on its forehead",
         ["僵尸", "跳尸", "清朝官服", "符纸"]),
        ("a taoist priest holding a wooden sword, yellow paper charms "
         "pinned between his fingers, altar candles behind him",
         ["道士", "桃木剑", "黄符", "法坛"]),
        ("a stone courtyard at night in green moonlight, incense smoke "
         "hanging in the air, doors painted with charms",
         ["义庄", "绿月光", "香火", "朱砂门"]),
    ],
}

# ---- 题材 ----
SUBJ = [
    ("Taoist Priest", "道士", "character",
     "a taoist priest in a worn robe, sleeves pinned back, a wooden sword "
     "in one hand and paper charms between the fingers of the other",
     ["道士", "法师", "道袍", "桃木剑", "符"],
     "道士：旧道袍，袖口扎起来，一手桃木剑，另一手夹着纸符。"),
    ("Jiangshi", "僵尸", "character_object",
     "a jiangshi in stiff Qing dynasty official robes, arms held straight "
     "out, a paper talisman on the forehead, joints moving in stops",
     ["僵尸", "跳尸", "清朝官服", "符纸", "尸"],
     "僵尸：僵直的清朝官服，双臂前伸，额头贴着符，动作一顿一顿。"),
    ("Charms Altar", "法坛", "scene",
     "a taoist altar with candles, a bowl of rice, red thread and stacked "
     "yellow charms",
     ["法坛", "道坛", "香案", "朱砂", "供桌"],
     "法坛：蜡烛、一碗米、红线、叠好的黄符。"),
    ("Paper Talisman", "符纸", "object",
     "a yellow paper talisman with red cinnabar strokes, edges curling",
     ["符纸", "黄符", "朱砂", "咒"],
     "符纸：黄纸朱砂画的符，边角卷起。"),
    ("Peachwood Sword", "桃木剑", "object",
     "a peachwood sword, the grain visible, worn smooth at the grip",
     ["桃木剑", "木剑", "法剑"],
     "桃木剑：木纹清楚，握的地方磨得发亮。"),
]


def main():
    # 风格
    rows = [json.loads(l) for l in open(CORPUS_SRC, encoding="utf-8") if l.strip()]
    n = 0
    for dom in ("prompt_video", "prompt_image"):
        for i, (desc, kw) in enumerate(STYLE["docs"], 1):
            if dom == "prompt_image" and i > 1:
                break        # 图片域只要一条，视频域要全
            rows.append({
                "doc_id": f"d9{n+1:03d}",
                "domain": dom,
                "lang": "en",
                "director": STYLE["director"],
                "director_zh": STYLE["director_zh"],
                "country": STYLE["country"],
                "era": STYLE["era"],
                "facet": "base",
                "style_tags": STYLE["style_tags"],
                "kw_zh": kw,
                "batch": "华语类型补充",
                "description": desc,
                "text_semantic": f"{desc}，{STYLE['director_zh']}，{'、'.join(kw)}",
            })
            n += 1
    with open(CORPUS_OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  语料 {len(rows)-n} -> {len(rows)}（+{n} 条风格文档：僵尸片）")

    # 题材
    srows = [json.loads(l) for l in open(SUBJ_SRC, encoding="utf-8") if l.strip()]
    have = {r.get("subject_zh") for r in srows}
    added = 0
    for en, zh, typ, phrase, kw, desc in SUBJ:
        if zh in have:
            print(f"  跳过（已存在）{zh}")
            continue
        srows.append({
            "doc_id": f"s{len(srows)+1:04d}",
            "kind": "subject", "subject_en": en, "subject_zh": zh,
            "phrase": phrase, "kw_zh": kw, "description": desc,
            "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}", "type": typ,
        })
        added += 1
    with open(SUBJ_OUT, "w", encoding="utf-8") as f:
        for r in srows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  题材 {len(srows)-added} -> {len(srows)}（+{added}）")
    print("\n### JIANGSHI_KB_DONE")


if __name__ == "__main__":
    main()
