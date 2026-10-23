"""
语料 v11：补「具体物件 + 材质与光」

依据（实测，不是推测）
----------------------
1. 场景锚定评测 60%，失败的题集中在：
   - 东方日常系：放假空荡的学校 / 杂货铺货箱 / 人行道裂缝 / CRT 电视 / 窗边尘埃
   - 材质与光：钢甲反光 / 白丝绸 / 雪粒逆光 / 体积光里的金箔
   （兴趣评估里这几条 margin 只有 0.0039~0.0253，几乎完全不区分）

2. 查语料发现：小津/是枝/蔡明亮/杨德昌/侯孝贤/贾樟柯 **都在**，
   但 doc 全是抽象气氛（"a figure sitting alone in a bare room"），
   没有任何具体日常物件 —— 实体存在，描述不匹配。
   这与"缺实体"（如胡金铨、乌尔善）是两种不同的病。

做法
----
只加具体物件，不加通用气氛词。签名一律锚定到**物件本身**，
避免又造出"空旷磁铁"这类通用吸盘。

Batch A 东方日常物件（6 实体 x 3 条）
Batch B 材质与光（5 实体 x 2~3 条）

corpus_v10 (725) -> corpus_v11
"""
import json
import os

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "corpus_v10.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v11.jsonl")

# (director_en, director_zh, facet, 签名, [场景], kw)
BATCH_A = [
    ("Yasujiro Ozu", "小津安二郎", "base",
     "tatami-level camera, low angle from the floor, domestic stillness",
     ["a kettle whistling on a low table, sliding shoji half open behind it",
      "laundry drying on a balcony line, an aluminium window pushed open",
      "a shoe cabinet in a narrow genkan, slippers lined up on the floor"],
     ["低机位", "日常", "静"]),

    ("Hirokazu Kore-eda", "是枝裕和", "base",
     "natural domestic daylight, unforced handheld stillness at eye level",
     ["children walking home along a narrow street of low houses, aluminium shutters down",
      "a school corridor of fluorescent tubes and steel shoe lockers in the afternoon",
      "a mother and child at a kitchen table under one bare bulb"],
     ["家庭", "自然光", "细腻"]),

    ("Tsai Ming-liang", "蔡明亮", "base",
     "extreme long take, static frame, water damage on the tile floor",
     ["a water stain spreading on a ceiling, one fluorescent tube flickering",
      "an empty cinema of red seats, dust hanging in the projector beam",
      "a red plastic stool in a corridor, a puddle on the wet tile"],
     ["极慢", "水", "孤独"]),

    ("Edward Yang", "杨德昌", "base",
     "architectural framing, precise urban geometry, cool daylight",
     ["a glass office facade reflecting the skyline, air-conditioner units bolted beside it",
      "a family at a dining table in a Taipei apartment, sliding aluminium door open",
      "a wide crossroads seen from a high window at dusk, cars waiting"],
     ["现代性", "冷光", "都市"]),

    ("Hou Hsiao-hsien", "侯孝贤", "base",
     "very long static wide shot, depth of memory, muted green light",
     ["a covered arcade with parked motorcycles and shuttered shopfronts",
      "a temple entrance with red pillars and a smoking incense burner",
      "a railway crossing with a waiting crowd, dusty afternoon light"],
     ["长镜", "远景", "静默"]),

    ("Jia Zhangke", "贾樟柯", "base",
     "documentary immediacy, decaying urban China, natural available light",
     ["a video arcade with CRT televisions stacked on shelves, red plastic stools",
      "a billiard table under a bare bulb, cigarette smoke drifting",
      "a half-demolished brick wall with a sofa still standing in the exposed room"],
     ["纪实", "小城", "变迁"]),
]

BATCH_B = [
    ("Denis Villeneuve", "维伦纽瓦", "base",
     "brutalist monoliths, minimal fog, one hard shaft of light",
     ["a rusted steel plate catching a thin hard rim light, fog behind it",
      "a monumental concrete wall with a single shaft of light, dust suspended in it"],
     ["巨物", "雾霭", "极简"]),

    ("Ridley Scott", "雷德利·斯科特", "sunbaked_epic",
     "sun-baked historical epic, dust and gold, scratched steel",
     ["a scratched steel pauldron reflecting cold white sun through a haze of dust",
      "a white silk sleeve falling through a shaft of hard light, dust motes"],
     ["烈日史诗", "尘金", "古罗马"]),

    ("Akira Kurosawa", "黑泽明", "color_1980s",
     "vivid saturated colour, massed banners, ordered chaos",
     ["gold-leaf armour plates in rising dust, volumetric light through smoke",
      "a row of lacquered red spears catching a low sun, dust in the beam"],
     ["饱和", "旗帜", "群像"]),

    ("Tsui Hark", "徐克", "base",
     "wuxia wirework, floating motion, mountain mist",
     ["snow grains lit from behind, spinning through a backlit shaft",
      "a taut bowstring with a nocked arrow, breath misting in cold air"],
     ["武侠", "飘", "山雾"]),

    ("Guillermo del Toro", "德尔·托罗", "cold_industrial",
     "gothic hardware, cold industrial light, wet surfaces",
     ["a wet concrete floor under one fluorescent tube, cold steel reflection",
      "an iron grate with steam rising, a single blue-white tube above"],
     ["冷工业", "哥特", "潮湿"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new = []
    for batch, tag in ((BATCH_A, "A-日常物件"), (BATCH_B, "B-材质与光")):
        for en, zh, facet, sig, scenes, kws in batch:
            for scene in scenes:
                n += 1
                desc = f"{scene}, {sig}"
                new.append({
                    "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                    "director": en, "director_zh": zh, "facet": facet,
                    "style_tags": [x.strip() for x in sig.split(",")][:6],
                    "kw_zh": kws, "description": desc, "batch": tag,
                    "text_semantic": f"{desc}, in the style of {en}",
                    "params": {"ar": "2.35:1", "style": "raw"},
                    "prompt": f"cinematic still, {desc}, in the style of {en}, "
                              f"35mm film, --ar 2.35:1 --style raw",
                })

    # 每条给一个视频版本（只取第一条场景，控量）
    for batch in (BATCH_A, BATCH_B):
        for en, zh, facet, sig, scenes, kws in batch:
            n += 1
            desc = f"{scenes[0]}, {sig}, slow push-in, steady drift"
            new.append({
                "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
                "director": en, "director_zh": zh, "facet": facet, "motion": "SLOW",
                "style_tags": [x.strip() for x in sig.split(",")][:4] + ["slow"],
                "kw_zh": kws, "description": desc,
                "text_semantic": f"{desc}, in the style of {en}, shot as moving footage",
                "params": {"ar": "21:9", "duration": "6s", "camera": "slow"},
                "prompt": f"cinematic video, {desc}, in the style of {en}, "
                          f"35mm film, --ar 21:9 --duration 6s --style raw",
            })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    from collections import Counter
    img = [d for d in new if d["domain"] == "prompt_image"]
    vid = [d for d in new if d["domain"] == "prompt_video"]
    print(f"corpus_v10 -> v11 : {len(corpus)} -> {len(out)}  (+{len(new)}：图 {len(img)} / 视频 {len(vid)})")
    print()
    print("按实体统计新增：")
    c = Counter(d["director"] for d in new)
    for k, v in c.most_common():
        print(f"  {k:<28} +{v}")
    print()
    print("样例（检查是否够具体）：")
    for d in img[:5]:
        print(f"  [{d['batch']}] {d['text_semantic'][:96]}")
    print("  ...")
    for d in img[-4:]:
        print(f"  [{d['batch']}] {d['text_semantic'][:96]}")
    print()
    print("通用词自检（不该出现的抽象吸盘词）：")
    bad = ["emptiness", "vast blank", "almost nothing", "lone subject"]
    hits = [(d["doc_id"], w) for d in new for w in bad if w in d["text_semantic"].lower()]
    print(f"  {'无' if not hits else hits}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V11_DONE")


if __name__ == "__main__":
    main()
