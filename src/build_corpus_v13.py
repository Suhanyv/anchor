"""
语料 v13：修三个「通用磁铁」

问题（场景锚定评测实测）
------------------------
1. 「荒原上只有一个孤独骑士」            -> top1 雾江孤舟（Villeneuve 排 8）
2. 「女骑士骑着披甲战马在草原上全速疾驰」 -> top1 手卷长卷（Villeneuve 排 16）
3. liubai 曾 9/9 全部流向 one_corner，之后又被"空旷"类 query 抢占

根因：签名写的是**属性**不是**物件**
    手卷 "continuous unfolding landscape"  <- 任何横向大景都匹配
    雾江 "lone + distant + misty"          <- 任何孤独遥远都匹配
    留白 "emptiness on all four sides"     <- 任何空画面都匹配

修法：把属性词换成**媒介词**（纸、绢、卷轴、题跋、印章、墨）
    手卷 = ink and mineral colour on paper, unrolling scroll read in sections, colophon and seals
    雾江 = one small boat on grey river water, mist banked on the surface, ink-wash distant peaks
    留白 = unpainted paper left blank, one small brush-painted subject, no painted background

kw_zh 保持不变 —— 否则挖掘器的 query 池会变，跨版本就不可比了。

corpus_v12 (788) -> corpus_v13
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v12.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v13.jsonl")

REBUILD_FACETS = {"handscroll", "wu_jiang", "liubai"}

# (facet, director_en, director_zh, 媒介锚定签名, [场景], kw_zh 保持不变)
REBUILD = [
    ("handscroll", "Handscroll Panorama", "手卷长卷",
     "ink and mineral colour on paper, an unrolling scroll read in sections, colophon and seals",
     ["a river landscape painted in ink on a long paper scroll, read left to right in sections",
      "a silk-mounted handscroll of travellers and donkeys on a mountain road, colophon at the end",
      "a painted handscroll of inns and bridges with red collector seals in the margins",
      "a narrow painted band of mountains and water on aged paper, unrolled flat on a table"],
     ["手卷", "长卷", "横向"]),

    ("wu_jiang", "Misty River Lone Boat", "雾江孤舟",
     "one small boat on grey river water, mist banked on the surface, ink-wash far peaks",
     ["one small wooden boat on wide grey river water, mist lying flat on the surface",
      "a single boat adrift below layered peaks painted in ink wash, pale still water",
      "a fisherman's boat on a misty river, far peaks reduced to pale ink silhouettes",
      "grey river water filling the frame, one boat, mist banding the far shore"],
     ["雾江", "孤舟", "远山"]),

    ("liubai", "Liubai Negative Space", "留白构图",
     "unpainted paper left blank, one small brush-painted subject, no painted background",
     ["a single ink-painted reed on otherwise blank paper, nothing else painted",
      "one small painted bird on unpainted silk, the rest of the sheet left bare",
      "a tiny painted pavilion on an empty sheet, no horizon and no ground painted",
      "one brush stroke of a boat on blank paper, no water painted around it"],
     ["留白", "空旷", "元素极少"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n0 = len(corpus)

    kept = [d for d in corpus if d.get("facet") not in REBUILD_FACETS]
    dropped = [d for d in corpus if d.get("facet") in REBUILD_FACETS]

    n = max(int(d["doc_id"][1:]) for d in corpus)
    new = []
    for facet, en, zh, sig, scenes, kws in REBUILD:
        for scene in scenes:
            n += 1
            desc = f"{scene}, {sig}"
            new.append({
                "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                "director": en, "director_zh": zh, "facet": facet,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws, "batch": "磁铁修复", "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": "2.35:1", "style": "raw"},
                "prompt": f"cinematic still, {desc}, in the style of {en}, "
                          f"35mm film, --ar 2.35:1 --style raw",
            })
        # 视频各 1 条
        n += 1
        desc = f"{scenes[0]}, {sig}, locked-off camera, one unbroken take"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
            "director": en, "director_zh": zh, "facet": facet, "motion": "STATIC",
            "style_tags": [x.strip() for x in sig.split(",")][:4] + ["static"],
            "kw_zh": kws, "batch": "磁铁修复", "description": desc,
            "text_semantic": f"{desc}, in the style of {en}, shot as moving footage",
            "params": {"ar": "21:9", "duration": "8s", "camera": "static"},
            "prompt": f"cinematic video, {desc}, in the style of {en}, "
                      f"35mm film, --ar 21:9 --duration 8s --style raw",
        })

    out = kept + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"corpus_v12 -> v13 : {n0} -> {len(out)}")
    print(f"  删除旧文档 {len(dropped)} 条（三个磁铁的全部文档）")
    print(f"  新增 图 {len([d for d in new if d['domain']=='prompt_image'])} "
          f"/ 视频 {len([d for d in new if d['domain']=='prompt_video'])}")
    print()
    print("=== 新签名（媒介锚定）===")
    for facet, en, zh, sig, scenes, kws in REBUILD:
        print(f"  {zh} [{facet}]")
        print(f"     签名: {sig}")
        print(f"     例  : {scenes[0]}")
    print()
    print("=== 通用属性词自检（新签名里不该出现）===")
    generic = ["emptiness", "vast blank", "continuous unfolding", "lone subject",
               "everything else empty", "all four sides"]
    for facet, en, zh, sig, scenes, kws in REBUILD:
        hits = [g for g in generic if g in sig.lower()]
        print(f"  {zh}: {'无' if not hits else hits}")
    print(f"\n=== kw_zh 是否保持不变 ===")
    for facet, en, zh, sig, scenes, kws in REBUILD:
        old = {tuple(d.get("kw_zh") or []) for d in dropped if d.get("facet") == facet}
        print(f"  {zh}: 旧 {old}  新 {kws}  {'一致' if tuple(kws) in old else '已变!'}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V13_DONE")


if __name__ == "__main__":
    main()
