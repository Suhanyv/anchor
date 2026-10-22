"""
语料 v8：修实体边界 + 视频文档减半

依据（src/diag_confusion.py 实测，不是推测）
--------------------------------------------
liubai      失败 9/12，**全部 9 次都流向 one_corner**（100% 单向碾压）
            one_corner 失败 0/12 —— 它赢下了所有
            原因：one_corner 签名含 "almost blank pale field"，字面就是「空旷」；
                  liubai 只靠 "centred" 一个词区分，太弱。
wu_jiang    失败 7/12 -> handscroll:3（远山 撞 长卷山水）、
                        base(Herzog):3（雾 撞 丛林雾）、misty_river:1
            原以为和侯孝贤互抢，实际是「远山」「雾」被别的实体抢走。
song_academy 失败 11/12 -> gongbi:4（同为中国传统绘画，边界不清）

另一个依据（消融实验）
--------------------
corpus_v7(906, 350视频) 81.2%  vs  corpus_v7_img(556, 无视频) 82.7%
-> 视频文档确实稀释风格精度，代价约 1.5pp。
   但去掉就失去域区分（98.86%）。折中：**每组只留 1 条视频 doc**（350 -> 175）。

做法
----
1. 删掉 5 个 facet 的旧文档，用**正交签名 + 手工场景**重建
2. 视频文档每组保留 1 条
corpus_v7 (906) -> corpus_v8
"""
import json
import os

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "corpus_v7.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v8.jsonl")

# 要整体重建的 facet（旧文档全删，换成正交定义）
REBUILD = {"liubai", "one_corner", "wu_jiang", "song_academy", "gongbi"}

# (facet, director_en, director_zh, 正交签名, [场景...], kw)
NEW = [
    # ---- 留白：只占「四周全空 + 主体居中」，一个字都不提边角 ----
    ("liubai", "Liubai Negative Space", "留白构图",
     "emptiness on all four sides, one small subject at dead centre",
     ["one small bird alone at dead centre of an empty white sky",
      "one low pavilion at dead centre of a wide blank lake",
      "a single reed at dead centre of an empty pale field",
      "one tiny figure standing at dead centre of an open snow field"],
     ["留白", "空旷", "元素极少"]),

    # ---- 一角：只占「从边角伸进来」，不提「空」----
    ("one_corner", "One-Corner Composition", "马一角夏半边",
     "subject entering from one corner only, everything else left bare",
     ["a plum branch entering from the lower right corner only",
      "one sail touching the upper left corner, all else untouched",
      "a scholar's sleeve entering from the bottom edge only",
      "one roof eave cropping in at the top corner, frame otherwise bare"],
     ["一角", "半边", "贴着边角"]),

    # ---- 雾江：强化远山 + 雾 + 孤舟三件套 ----
    ("wu_jiang", "Misty River Lone Boat", "雾江孤舟",
     "distant mountains half dissolved in mist, one lone boat on a wide still river",
     ["three ranges of distant mountains fading into mist above a wide grey river",
      "a lone wooden boat adrift where the mist swallows the far mountains",
      "one small boat on a still grey river, mountains layered and half erased by fog",
      "wide misty water, distant peaks reduced to pale silhouettes, a single boat"],
     ["雾江", "孤舟", "远山"]),

    # ---- 宋代院体：只占「院体画/绢本/精微观察动植物」----
    ("song_academy", "Song Academy Realism", "宋代院体",
     "imperial academy scroll, precise study of a bird or plant on silk",
     ["two sparrows quarrelling on a bare winter twig, painted on silk",
      "a hare crouched in dry winter grass, every hair observed",
      "a lotus leaf with one dragonfly, meticulous imperial academy study",
      "a plum branch in early snow, two buds open, painted on silk"],
     ["院体", "工细", "绢本"]),

    # ---- 工笔重彩：只占「细线勾轮廓 + 矿物色平涂 + 装饰性」，不谈观察对象 ----
    ("gongbi", "Gongbi Fine-Line Painting", "工笔重彩",
     "hairline outline filled with flat mineral colour, decorative symmetry",
     ["a peony in flat cinnabar red, gold outline, decorative and symmetrical",
      "a phoenix with gold leaf laid inside hairline line work",
      "a kingfisher in flat mineral blue and green inside a fine gold line",
      "a court lady's hairpin in flat vermilion and jade, decorative pattern"],
     ["工笔", "重彩", "白描"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n0 = len(corpus)

    # ---------- 1) 删掉要重建的 facet 的旧文档 ----------
    keep = [d for d in corpus if d.get("facet") not in REBUILD
            and d.get("domain") in (None, "prompt_image")]
    dropped_img = [d for d in corpus if d.get("facet") in REBUILD
                   and d.get("domain") in (None, "prompt_image")]
    videos = [d for d in corpus if d.get("domain") == "prompt_video"]

    # ---------- 2) 视频文档每组只留 1 条 ----------
    seen, keep_vid, dropped_vid = set(), [], []
    for d in videos:
        k = (d["director"], d.get("facet", "base"))
        if k in seen:
            dropped_vid.append(d)
        else:
            seen.add(k)
            keep_vid.append(d)

    # 重建 facet 的旧视频也丢掉（它们的签名已被判为有歧义）
    keep_vid = [d for d in keep_vid if d.get("facet") not in REBUILD]

    # ---------- 3) 重建 ----------
    n = max(int(d["doc_id"][1:]) for d in corpus)
    new = []
    for facet, en, zh, sig, scenes, kws in NEW:
        for scene in scenes:
            n += 1
            desc = f"{scene}, {sig}"
            new.append({
                "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                "director": en, "director_zh": zh, "country": "CN",
                "era": "traditional", "facet": facet,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws, "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": "2.35:1", "style": "raw"},
                "prompt": f"cinematic still, {desc}, in the style of {en}, "
                          f"35mm film, --ar 2.35:1 --style raw",
            })
        # 每个重建 facet 配 1 条视频
        n += 1
        scene = scenes[0]
        dur = "8s" if facet in ("liubai", "one_corner", "wu_jiang") else "6s"
        desc = f"{scene}, {sig}, locked-off camera, one long unbroken take"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
            "director": en, "director_zh": zh, "country": "CN",
            "era": "traditional", "facet": facet, "motion": "STATIC",
            "style_tags": [x.strip() for x in sig.split(",")][:4] + ["static"],
            "kw_zh": kws, "description": desc,
            "text_semantic": f"{desc}, in the style of {en}, shot as moving footage",
            "params": {"ar": "21:9", "duration": dur, "camera": "static"},
            "prompt": f"cinematic video, {desc}, in the style of {en}, "
                      f"35mm film, --ar 21:9 --duration {dur} --style raw",
        })

    out = keep + keep_vid + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    from collections import Counter
    dom = Counter(d["domain"] for d in out)
    fac = Counter(d["facet"] for d in out)
    print(f"corpus_v7 -> v8 : {n0} -> {len(out)}")
    print(f"  删除重建 facet 旧文档 : {len(dropped_img)} 条")
    print(f"  视频文档 350 -> {len(keep_vid)+5} 条（每组只留 1 条）")
    print(f"  域分布 : {dict(dom)}")
    print("\n重建后的关键 facet：")
    for f in ("liubai", "one_corner", "wu_jiang", "song_academy", "gongbi"):
        print(f"  {f:<14} {fac.get(f,0)} 条")
    print("\n正交性检查（签名两两不共享关键词）：")
    sigs = {f: s for f, _, _, s, _, _ in NEW}
    for a in sigs:
        for b in sigs:
            if a < b:
                wa = set(w for w in sigs[a].replace(",", " ").split() if len(w) > 3)
                wb = set(w for w in sigs[b].replace(",", " ").split() if len(w) > 3)
                shared = wa & wb
                print(f"  {a:<14} vs {b:<14} 共享词: {sorted(shared) if shared else '无'}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V8_DONE")


if __name__ == "__main__":
    main()
