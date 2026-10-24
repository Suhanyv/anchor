"""
语料 v12：按外部提示词词表补「具体」概念，刻意跳过通用质量词

依据
----
src/extract_external_vocab_v2.py 对比结果（69 概念：缺 25 / 少 3 / 有 41）
数据来源：水仙的AI提示词（署名使用协议，须保留出处）只做词频对照，未复制原文。

加入的（具体、能指物）
    景别   全身 / 半身 / 中景 / 手部特写
    光     highlight / specular / vignette / shallow DOF
    材质   parchment / tulle / ceramic / brushed steel / canvas / pencil

刻意不加的（通用质量词，会造磁铁）
    电影感 / 真实感 / 照片级 / 细节丰富 / 锐利 / 柔和
    理由：这些词能匹配一切，加进去只会稀释检索。之前 liubai 写成"纯空旷"
    变成通用磁铁、mech_hidden_observer 变成"遮挡"磁铁，都是同一个教训。

corpus_v11 (764) -> corpus_v12
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v11.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v12.jsonl")

# (director, zh, facet, 签名, [场景], kw)
GROUP_A_FRAMING = [
    ("Denis Villeneuve", "维伦纽瓦", "base",
     "brutalist monoliths, minimal fog, wide negative scale",
     ["a full body figure reduced to a silhouette against a concrete wall",
      "a half body figure at the edge of a flooded plain, breathing"],
     ["巨物", "雾霭", "极简"]),

    ("Ridley Scott", "雷德利·斯科特", "sunbaked_epic",
     "sun-baked historical epic, dust and gold, scratched steel",
     ["a full body rider on a dust plain, low horizon, sun behind",
      "a medium shot of gloved hands tightening a leather strap"],
     ["烈日史诗", "尘金", "古罗马"]),

    ("Akira Kurosawa", "黑泽明", "color_1980s",
     "vivid saturated colour, massed banners, ordered chaos",
     ["a full body warrior standing alone before ranked banners",
      "a close shot of a hand on a scabbard, dust settling"],
     ["饱和", "旗帜", "群像"]),

    ("Yasujiro Ozu", "小津安二郎", "base",
     "tatami-level camera, low angle from the floor, domestic stillness",
     ["a medium shot of two figures seated at a low table, seen from the floor",
      "a close shot of hands folding a cloth on a tatami mat"],
     ["低机位", "日常", "静"]),
]

GROUP_B_LIGHT = [
    ("Denis Villeneuve", "维伦纽瓦", "base",
     "brutalist monoliths, minimal fog, one hard shaft",
     ["a single highlight running along the edge of a steel plate, everything else dark",
      "a specular glint on wet concrete under one distant lamp"],
     ["巨物", "雾霭", "极简"]),

    ("Ridley Scott", "雷德利·斯科特", "sunbaked_epic",
     "sun-baked historical epic, dust and gold, scratched steel",
     ["a highlight travelling along the rim of a scratched pauldron as the light shifts",
      "specular flecks on chain mail under a low sun, deep shadow behind"],
     ["烈日史诗", "尘金", "古罗马"]),

    ("Michael Haneke", "哈内克", "luminous_bw",
     "luminous black and white, plain village light, wide precise framing",
     ["a vignette darkening the corners of a plain white room",
      "one highlight on a glass of water, the rest of the frame flat grey"],
     ["黑白", "冷峻村庄", "精准构图"]),

    ("Wong Kar-wai", "王家卫", "base",
     "saturated neon, step-printed motion blur, shallow depth",
     ["a highlight smeared across rain-streaked glass, shallow depth of field",
      "specular reflections breaking on a wet step, neon bleeding out of focus"],
     ["霓虹", "慢门", "暧昧"]),
]

GROUP_C_MATERIAL = [
    ("Song Academy Realism", "宋代院体", "song_academy",
     "imperial academy scroll, precise study on silk",
     ["a bird painted on aged parchment-toned silk, fine even brushwork",
      "a lotus leaf on vellum, colour laid thin and pale"],
     ["院体", "工细", "绢本"]),

    ("Gongbi Fine-Line Painting", "工笔重彩", "gongbi",
     "hairline outline filled with flat mineral colour, decorative",
     ["a peony in flat cinnabar on ceramic-white ground, gold outline",
      "a figure in sheer tulle sleeves over silk, hairline outlines"],
     ["工笔", "重彩", "白描"]),

    ("Guillermo del Toro", "德尔·托罗", "cold_industrial",
     "gothic hardware, cold industrial light, wet surfaces",
     ["brushed steel panels with rivets, one cold tube above",
      "a canvas tarp over machinery, condensation beading on metal"],
     ["冷工业", "哥特", "潮湿"]),

    ("Wes Anderson", "韦斯·安德森", "pastel_stylised",
     "deadpan symmetry, pastel palette, flat frontal staging",
     ["a ceramic vase dead centre on a painted shelf, symmetrical",
      "a pencil drawing pinned on a pale wall, perfectly centred"],
     ["粉彩", "对称", "平面化"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new = []
    for group, tag in ((GROUP_A_FRAMING, "A-景别"),
                       (GROUP_B_LIGHT, "B-高光"),
                       (GROUP_C_MATERIAL, "C-材质")):
        for en, zh, facet, sig, scenes, kws in group:
            for scene in scenes:
                n += 1
                desc = f"{scene}, {sig}"
                new.append({
                    "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                    "director": en, "director_zh": zh, "facet": facet,
                    "style_tags": [x.strip() for x in sig.split(",")][:6],
                    "kw_zh": kws, "batch": tag, "description": desc,
                    "text_semantic": f"{desc}, in the style of {en}",
                    "params": {"ar": "2.35:1", "style": "raw"},
                    "prompt": f"cinematic still, {desc}, in the style of {en}, "
                              f"35mm film, --ar 2.35:1 --style raw",
                })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"corpus_v11 -> v12 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print()
    print("按批次：", dict(Counter(d["batch"] for d in new)))
    print("按实体：", dict(Counter(d["director"] for d in new)))
    print()
    print("新增样例：")
    for d in new:
        print(f"  [{d['batch']}] {d['text_semantic'][:94]}")
    print()
    # 自检：不该出现通用质量词
    generic = ["cinematic", "photorealistic", "fine detail", "sharp", "great detail"]
    hits = [(d["doc_id"], g) for d in new for g in generic
            if g in d["description"].lower()]
    print(f"通用质量词自检: {'无' if not hits else hits}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V12_DONE")


if __name__ == "__main__":
    main()
