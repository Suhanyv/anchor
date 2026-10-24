"""
「东方影像」facet 包 —— 补上语料完全缺失的一整套视觉语言。

起因：草船那条 query 只命中蔡明亮(slow water)和塔可夫斯基(water, ruins)，
      因为 119 位导演语料里没有任何「山水 / 留白 / 手卷 / 雾江」的描述。

做法：10 个中国传统影像范式 + 1 个侯孝贤雾江面，每个 3 条 doc。
      沿用机制化写法：用具体名词和可指物，不用"意境""气韵"这类无法定位的词。

输出 corpus_v4.jsonl / queries_v4.jsonl
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v3.jsonl")
SRC_QUERIES = os.path.join(ROOT, "data", "raw", "queries_v3.jsonl")
OUT_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v4.jsonl")
OUT_QUERIES = os.path.join(ROOT, "data", "raw", "queries_v4.jsonl")

# (entity_en, entity_zh, facet_id, 英文签名, [3 场景], [3 中文词])
EASTERN = [
    ("Chinese Literati Ink-Wash", "文人水墨", "ink_wash",
     "monochrome ink wash, wet brush strokes, vast empty paper, single dark accent, calligraphic restraint",
     ["a single withered tree against an empty paper horizon",
      "one dark rock in drifting mist with three brushstrokes of mountain",
      "an empty pavilion with a figure reduced to two ink marks"],
     ["水墨", "留白", "笔触"]),

    ("Blue-Green Landscape", "青绿山水", "qinglv",
     "mineral blue-green pigment, gold outline, layered peaks, decorative mineral colour, silk texture",
     ["layered azure peaks threaded with fine gold lines",
      "a valley of malachite green with vermilion pavilions",
      "a river winding between ultramarine mountains"],
     ["青绿", "矿物色", "金线"]),

    ("Song Academy Realism", "宋代院体", "song_academy",
     "meticulous observation, muted silk tones, restrained composition, quiet naturalism, birds and bare branches",
     ["two sparrows on a bare branch in muted silk tones",
      "a lotus pond rendered with fine even brushwork",
      "a hare crouched among winter grasses"],
     ["院体", "工细", "绢本"]),

    ("Gongbi Fine-Line Painting", "工笔重彩", "gongbi",
     "fine outline drawing, saturated mineral pigments, flat decorative colour, precise hairline detail",
     ["a court lady in vermilion and jade with hairline outlines",
      "a peony rendered in flat cinnabar with gold detail",
      "a phoenix with gold leaf applied over fine line work"],
     ["工笔", "重彩", "白描"]),

    ("Liubai Negative Space", "留白构图", "liubai",
     "overwhelming empty space, tiny subject pushed to the edge, asymmetric balance, silence made visible",
     ["one small boat at the far corner of an almost empty pale field",
      "a single bird in an enormous blank sky",
      "a figure reduced to a speck at the base of a vast cliff"],
     ["留白", "空旷", "一角"]),

    ("Misty River Lone Boat", "雾江孤舟", "wu_jiang",
     "layered mist, very low horizon, one small boat, pale flat water, receding dark hills",
     ["a lone thatched boat on a vast misty river at dawn",
      "an old boatman poling slowly out of thick fog",
      "reed banks dissolving into white mist at the waterline"],
     ["雾江", "孤舟", "远山"]),

    ("Handscroll Panorama", "手卷长卷", "handscroll",
     "extreme horizontal format, continuous unfolding landscape, sequential reading, long low band",
     ["a continuous river landscape unrolling across an extreme horizontal frame",
      "travellers walking along a long scroll-like road",
      "layered hills receding across a narrow horizontal band"],
     ["手卷", "长卷", "横向"]),

    ("One-Corner Composition", "马一角夏半边", "one_corner",
     "subject confined to a single corner, vast void elsewhere, deliberate emptiness, extreme asymmetry",
     ["a scholar's sleeve entering only from the lower corner",
      "a single sail in the upper corner of a blank field",
      "one branch intruding from the extreme edge of the frame"],
     ["一角", "半边", "极简"]),

    ("Folk Woodblock New Year Print", "木版年画", "nianhua",
     "flat woodblock colour, bold black outline, folk symbolism, saturated red and green",
     ["a door god printed in flat red and green with bold outlines",
      "a fish and lotus motif in woodblock colour",
      "a harvest scene in flat folk reds and greens"],
     ["年画", "木版", "民俗"]),

    ("Shadow Puppetry", "皮影", "piying",
     "translucent silhouettes, backlit screen, jointed figures, warm ochre light",
     ["a jointed shadow figure against a warm backlit screen",
      "two silhouette horsemen clashing on a lit screen",
      "a pagoda silhouette glowing in ochre light"],
     ["皮影", "剪影", "透光"]),

    # 侯孝贤追加一个「雾江」面 —— 导演视角的同一个视觉目标
    ("Hou Hsiao-hsien", "侯孝贤", "misty_river",
     "very long static shot, misty river with one distant boat, patient framing, muted grey-green air",
     ["a fixed very long shot of a single boat on a misty river",
      "an old boatman poling across a wide grey-green river",
      "distant hills dissolving into fog above still water"],
     ["雾江远景", "极长镜头", "灰绿"]),
]

# 手工用户口吻 query（每个 facet 2 条）
QUERIES = {
    "ink_wash":    ["想要水墨那种空的感觉", "只有墨色没有颜色那种画"],
    "qinglv":      ["青绿山水那种颜色，石青石绿", "山是蓝绿色的那种古画"],
    "song_academy":["宋代那种工细的花鸟", "两只鸟站在枯枝上那种画"],
    "gongbi":      ["工笔重彩那种艳丽", "线条特别细、颜色特别浓的画"],
    "liubai":      ["只有一点点东西，其他全是空的", "东西都在角落，中间一大片空"],
    "wu_jiang":    ["远远的镜头，一条草船在江上，有个老渔夫在划",
                    "雾里的江面，一条小船，远山一层层退过去"],
    "handscroll":  ["手卷那种很长很长的构图", "横向拉得很长的山水"],
    "one_corner":  ["只要一个角有东西，其他全空", "半边虚半边实那种"],
    "nianhua":     ["年画那种大红大绿", "门神那种木版画的颜色"],
    "piying":      ["皮影戏那种透光的剪影", "打着灯的影子戏"],
    "misty_river": ["侯孝贤那种雾江远景", "长时间不动的远景，江上一条船"],
}

SCENES_PER = 3


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC_CORPUS)
    queries = load(SRC_QUERIES)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new_docs, new_q = [], []
    for en, zh, fid, sig, scenes, kws in EASTERN:
        ids = []
        for si, scene in enumerate(scenes[:SCENES_PER]):
            n += 1
            is_video = (si == 2)
            ar = "21:9" if is_video else "2.35:1"
            desc = f"{scene}, {sig}"
            tail = "--v 6 --duration 5s" if is_video else "--v 6 --style raw"
            nd = {
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": "CN" if "Hou" not in en else "TW",
                "era": "traditional" if "Hou" not in en else "1980s-",
                "facet": fid,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws,
                "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": ar, "style": "raw"},
                "prompt": f"cinematic {'video' if is_video else 'still'}, {desc}, "
                          f"in the style of {en}, 35mm film, --ar {ar} {tail}",
            }
            ids.append(nd["doc_id"])
            new_docs.append(nd)

        for qi, text in enumerate(QUERIES.get(fid, [])):
            new_q.append({
                "query_id": f"qe_{fid}_{qi}",
                "query": text,
                "lang": "zh", "domain": "prompt_image",
                "relevant": ids,
                "target_director": en,
                "facet": fid,
                "query_kind": "style",
                "template_id": f"handcrafted:{fid}",
                "template": "handcrafted",
            })

    corpus4 = corpus + new_docs
    queries4 = queries + new_q

    with open(OUT_CORPUS, "w", encoding="utf-8") as f:
        for d in corpus4:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(OUT_QUERIES, "w", encoding="utf-8") as f:
        for q in queries4:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"corpus v3 -> v4 : {len(corpus)} -> {len(corpus4)}  (+{len(new_docs)})")
    print(f"queries v3 -> v4: {len(queries)} -> {len(queries4)}  (+{len(new_q)})")
    print(f"\n东方影像 facet: {len(EASTERN)} 个")
    for en, zh, fid, sig, scenes, kws in EASTERN:
        print(f"  {fid:<14} {zh:<8} {en}")
        print(f"     签: {sig[:70]}")
        print(f"     景: {scenes[0][:70]}")
    print("\n手工 query:")
    for fid, lst in QUERIES.items():
        for t in lst:
            print(f"  [{fid:<12}] {t}")
    print(f"\n-> {OUT_CORPUS}\n-> {OUT_QUERIES}")
    print("\n### EASTERN_PACK_DONE")


if __name__ == "__main__":
    main()
