"""
语料 v5：给「崩掉的 facet」补具体物件版文档

来源：mine_interesting.py 的实测结果（2100 条新句式）
    宋代院体 100% 失败 / 手卷 83.3% / 留白 75% / 工笔 50% / 黑白新写实 58.3%

诊断：这些 facet 的 doc 全用画论术语写（meticulous observation, extreme horizontal
      format, overwhelming empty space），而用户说的是具体东西。
      对照 misty_river 只失败 25% —— 因为它写了船、雾、江、老渔夫。

原则：**不删旧的，只加具体的**。每个 facet 同时保留画论版和物件版，
      这样两种说法都能命中。

corpus_v4 (525) -> corpus_v5 (+22 = 547)
"""
import json
import os

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "corpus_v4.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v5.jsonl")

# (director_en, director_zh, facet, 英文签名, [具体物件场景], [中文词——保持与原 facet 一致以可比])
ADD = [
    # ---- 宋代院体：100% 失败 ----
    ("Song Academy Realism", "宋代院体", "song_academy",
     "fine even brushwork, muted silk tones, quiet observation",
     ["two sparrows perched on a bare winter twig",
      "a hare crouched low in dry winter grass",
      "a lotus leaf with a single dragonfly above it",
      "a plum branch in early snow with two buds open"],
     ["院体", "工细", "绢本"]),

    # ---- 手卷长卷：83.3% 失败 ----
    ("Handscroll Panorama", "手卷长卷", "handscroll",
     "continuous unfolding landscape, sequential scenes along a low band",
     ["a river landscape unrolling continuously from left to right",
      "travellers and donkeys walking a long mountain road one after another",
      "inns, bridges and villages appearing in sequence along a river bank",
      "a market street unfolding across a narrow horizontal strip"],
     ["手卷", "长卷", "横向"]),

    # ---- 留白构图：75% 失败 ----
    ("Liubai Negative Space", "留白构图", "liubai",
     "almost blank pale field, one tiny subject at the edge",
     ["one small fishing boat at the extreme corner of an almost blank pale field",
      "a single bird alone in an enormous empty sky",
      "a tiny figure at the very base of a towering cliff",
      "one bare branch entering from the edge, nothing else in frame"],
     ["留白", "空旷", "一角"]),

    # ---- 工笔重彩：50% 失败 ----
    ("Gongbi Fine-Line Painting", "工笔重彩", "gongbi",
     "fine hairline outlines, flat saturated colour laid inside the lines",
     ["a peony in flat cinnabar red with a fine gold outline",
      "a court lady in vermilion robes with an ornate hairpin",
      "a phoenix with gold leaf applied over hairline line work",
      "a kingfisher on a lotus stem in saturated mineral blue and green"],
     ["工笔", "重彩", "白描"]),

    # ---- 黑白新写实（费里尼）：58.3% 失败 ----
    ("Federico Fellini", "费里尼", "neorealist",
     "black and white street realism, ordinary people, flat daylight",
     ["a father and son walking a bombed street in black and white",
      "a crowded outdoor market in flat monochrome daylight",
      "laundry hanging between tenement windows, shot in black and white"],
     ["黑白新写实", "战后废墟", "朴素"]),

    # ---- 冷峻黑白（哈内克）：41.7% 失败 ----
    ("Michael Haneke", "哈内克", "luminous_bw",
     "luminous black and white, plain village light, wide precise framing",
     ["children walking a village street in luminous black and white",
      "a pale face by a window in soft monochrome",
      "a wide field under a pale overcast sky, shot in black and white"],
     ["黑白", "冷峻村庄", "精准构图"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)
    new = []
    for en, zh, facet, sig, scenes, kws in ADD:
        for si, scene in enumerate(scenes):
            n += 1
            is_video = (si % 3 == 2)   # 每 3 条里第 3 条当视频
            ar = "21:9" if is_video else "2.35:1"
            desc = f"{scene}, {sig}"
            tail = "--v 6 --duration 5s" if is_video else "--v 6 --style raw"
            new.append({
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": "CN", "era": "traditional",
                "facet": facet,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws,
                "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": ar, "style": "raw"},
                "prompt": f"cinematic {'video' if is_video else 'still'}, {desc}, "
                          f"in the style of {en}, 35mm film, --ar {ar} {tail}",
            })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"corpus_v4 -> v5 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print("\n新增文档（按 facet）：")
    c = Counter(d["facet"] for d in new)
    for f, k in c.items():
        print(f"  {f:<16} +{k}")
    print("\n样例：")
    for d in new[:6]:
        print(f"  [{d['facet']:<14}] {d['text_semantic'][:88]}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V5_DONE")


if __name__ == "__main__":
    main()
