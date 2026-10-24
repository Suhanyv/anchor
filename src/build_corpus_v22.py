"""
语料 v22：修三个磁铁（数据驱动）

审计结论（src/magnet_audit.py，78 条用例）
-----------------------------------------
真磁铁=抢得多且自己从不正确：
    Street Photography     抢 4   正确 0
    Wasteland              抢 4   正确 0
    One-Corner Composition 抢 3   正确 0/1

被冤枉的（抢得多但自己也对得多，属正常竞争）：
    Wuershan 2/3、Hitchcock 4/6、Misty River 1/1
-> LIMITATIONS 第七节说「雾江孤舟是磁铁」**没有数据支持**，本条更正。

三个磁铁的病根（同一个老毛病）
------------------------------
用**通用属性词**描述，没有锚定到**独特物件**：

    Street Photography  「一个人跨过水坑」「两个陌生人擦肩」
                        -> 任何街头导演都成立；缺 35mm / 目测对焦 / 接触印相 / 决定性瞬间
    Wasteland           「裂地」「尘土」「死加油站」「锈」
                        -> 和塔可夫斯基 / 安东尼奥尼的空景撞；缺焊接装甲 / 油桶 / 滤罐 / 废胎
    One-Corner          5 条里 4 条重复同一句，且 d0912 与 d0916 完全相同
                        -> 重复文档等于权重翻倍；且 "frame bare" 与「留白」撞

修法（沿用已经在「中文锚点」上验证过的原则）
------------------------------------------
1. 每条都锚定到该实体**独有的物件或媒介**（rangefinder / jerrycan / album leaf）
2. 删掉与其它实体共享的属性词（candid、street、dust、dead、bare、untouched）
3. 去掉重复文档

corpus_v21 (1045) -> corpus_v22
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v21.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v22.jsonl")

# 重写后的描述：(facet, kind, desc, kw)
REWRITE = {
    "Street Photography": [
        ("base", "image",
         "a 35mm rangefinder raised to the eye, one frame as a man steps off the kerb, "
         "grain and the black edge of a contact sheet",
         ["旁轴相机", "胶片颗粒", "接触印相", "决定性瞬间"]),
        ("base", "image",
         "two strangers crossing in a single exposure, shot from the hip at waist level, "
         "slight motion blur across the near shoulder",
         ["腰平取景", "单张曝光", "轻微拖影"]),
        ("base", "image",
         "a face behind a bus window with the street reflected over it, "
         "exposed for the highlights, shutter speed just too slow",
         ["车窗", "反射", "按高光曝光", "慢门"]),
        ("facet", "image",
         "a hand and a cigarette cropped at the frame edge, the rest falling out of focus, "
         "shot wide open and zone-focused",
         ["画幅边缘", "大光圈", "目测对焦"]),
        ("base", "video",
         "handheld at chest height walking into the crowd, the shutter clicking, nothing staged",
         ["手持", "胸前高度", "快门声", "不摆拍"]),
    ],
    "Wasteland": [
        ("base", "image",
         "a car plated with welded scrap, jerrycans lashed to the roof rack, dust rolling behind it",
         ["焊接废铁", "油桶", "车顶行李架", "尘土"]),
        ("base", "image",
         "a figure in a gas mask with a filter canister, plate armour bolted over a leather coat, "
         "goggles taped at the strap",
         ["防毒面具", "滤罐", "螺栓装甲", "护目镜"]),
        ("base", "image",
         "a fuel station with the pumps stripped out, tyre stacks burning beside the forecourt",
         ["废弃加油站", "拆空的加油机", "废轮胎燃烧"]),
        ("facet", "image",
         "a water tank on a trailer guarded by two figures, jerrycans and a hand pump beside it",
         ["水罐拖车", "守卫", "手压泵", "油桶"]),
        ("base", "video",
         "long lens on a plated vehicle, heat shimmer, the dust plume held without cutting",
         ["长焦", "热浪", "尘柱", "不剪辑"]),
    ],
    "One-Corner Composition": [
        ("one_corner", "image",
         "a plum branch entering from the lower right of a hanging scroll, "
         "the rest left as unpainted silk with the mounting visible",
         ["一角", "梅花枝", "绢本", "装裱"]),
        ("one_corner", "image",
         "one sail touching the upper left corner of a fan-shaped leaf, "
         "the folded paper blank across the rest",
         ["一角", "帆", "扇面", "空白纸"]),
        ("one_corner", "image",
         "a scholar's sleeve entering from the bottom edge of an album leaf, "
         "the paper left as it was, only a seal added",
         ["一角", "衣袖", "册页", "印章"]),
        ("one_corner", "image",
         "a single roof eave cropping in at the top of a narrow vertical scroll, "
         "blank paper below it down to the roller",
         ["一角", "屋檐", "立轴", "卷轴下端"]),
        ("one_corner", "image",
         "a bird at the extreme upper right of a square album page, "
         "the silk beneath it left untouched, one colophon strip at the edge",
         ["一角", "鸟", "绢本", "题跋"]),
    ],
}

# 这些词是被判定为"共享属性"的，重写后应当消失（自检用）
BANNED_SHARED = ["candid", "dust everywhere", "dead ground", "frame otherwise bare",
                 "all else untouched", "nothing green"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    print(f"corpus_v21: {len(corpus)} 条，实体 {len({d['director'] for d in corpus})}")

    new_docs = []
    n = max(int(d["doc_id"][1:]) for d in corpus)
    for who, rows in REWRITE.items():
        old = [d for d in corpus if d["director"] == who]
        meta = old[0]
        print(f"  {who}: 重写 {len(old)} -> {len(rows)} 条")
        corpus = [d for d in corpus if d["director"] != who]
        for facet, kind, desc, kw in rows:
            n += 1
            is_video = (kind == "video")
            doc = {
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": who, "director_zh": meta.get("director_zh", ""),
                "country": meta.get("country", ""), "era": meta.get("era", ""),
                "facet": facet,
                "style_tags": (meta.get("style_tags") or [])[:4],
                "kw_zh": kw, "batch": "磁铁修复",
                "description": desc,
                "text_semantic": (f"{desc}, one continuous shot, in the style of {who}"
                                  if is_video else f"{desc}, in the style of {who}"),
                "params": ({"ar": "21:9", "duration": "5s", "camera": "slow"} if is_video
                           else dict(meta.get("params") or {"ar": "2.35:1", "style": "raw"})),
                "prompt": (f"cinematic {'video' if is_video else 'still'}, {desc}, "
                           f"in the style of {who}, --ar {'21:9' if is_video else '2.35:1'} --style raw"),
            }
            if is_video:
                doc["motion"] = "SLOW"
            new_docs.append(doc)

    out = corpus + new_docs
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\ncorpus_v21 -> v22 : {len(out)} 条，实体 {len({d['director'] for d in out})}")

    # 自检：共享属性词是否已从这三个实体里消失
    print("\n=== 自检：共享属性词 ===")
    blob = " ".join(d["text_semantic"].lower() for d in out
                    if d["director"] in REWRITE)
    for b in BANNED_SHARED:
        c = blob.count(b)
        print(f"  {b:<24} {c} 处 {'✅' if c == 0 else '❌'}")

    # 自检：还有没有完全重复的文档
    seen = {}
    dup = 0
    for d in out:
        k = d["text_semantic"].strip().lower()
        if k in seen:
            dup += 1
            print(f"  重复: {d['doc_id']} 与 {seen[k]} 相同")
        else:
            seen[k] = d["doc_id"]
    print(f"  完全重复的文档: {dup} 条 {'✅' if dup == 0 else '❌'}")

    print(f"\n-> {OUT}")
    print("\n### CORPUS_V22_DONE")


if __name__ == "__main__":
    main()
