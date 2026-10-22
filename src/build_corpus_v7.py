"""
语料 v7：整 facet（三个结构性问题）

1) 留白 vs 一角 切开（不合并）
   区别在**位置**不在**空多少**：
     留白   liubai      主体居中，四周大片空
     一角   one_corner  主体贴着边角，极端不对称
   切完两边都不模糊，重叠消失。

2) 把「船」从留白里拿掉
   上一轮我给留白加了 "a fishing boat at the corner"，抢走了雾江(misty_river/wu_jiang)的
   「船」信号，导致雾江失败率 25% -> 41.7%。**船只属于雾江。**
   留白改用：鸟、芦、亭、枝、人影。

3) 修「对称、造作」回归
   挖掘器显示：该 query base 模型排第 1，微调后排 21~27 名。
   核实后这组 kw 属于 **朴赞郁 Park Chan-wook**（对称/造作/红绿），不是 Fassbinder。
   -> 给他补「对称/造作」的具体物件 doc。

corpus_v6 (897) -> corpus_v7
"""
import json
import os

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "corpus_v6.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v7.jsonl")

KW_LIUBAI = ["留白", "空旷", "元素极少"]
KW_CONER = ["一角", "半边", "贴着边角"]

# 域词绝不该出现在 kw_zh 里：kw 只描述**风格**，域由 domain 字段表达
DOMAIN_WORDS = {"运镜", "镜头运动", "时长", "视频", "图片", "静态"}

# facet -> 规范实体（重分配 facet 时必须同步改 director，否则出现
# ('Liubai Negative Space', 'one_corner') 这种自相矛盾的分组）
FACET_ENTITY = {
    "liubai": ("Liubai Negative Space", "留白构图"),
    "one_corner": ("One-Corner Composition", "马一角夏半边"),
    "misty_river": ("Hou Hsiao-hsien", "侯孝贤"),
    "wu_jiang": ("Misty River Lone Boat", "雾江孤舟"),
}

# (要替换掉的旧描述片段关键字, 新 facet, 新签名, 新描述, 新中文词)
REWRITE = [
    # 船 -> 从留白拿掉，改成不带船的主体
    ("one small boat at the far corner",
     "one_corner", "almost blank pale field, one tiny subject at the very edge",
     "one empty pavilion roof at the far corner of an almost blank pale field",
     KW_CONER),
    ("one small fishing boat at the extreme corner",
     "one_corner", "almost blank pale field, one tiny subject at the very edge",
     "one empty pavilion roof at the extreme corner of an almost blank pale field",
     KW_CONER),
    # 鸟在天空 / 崖底小人 -> 居中留白
    ("a single bird in an enormous blank sky",
     "liubai", "vast blank field, one small subject centred, everything else empty",
     "a single crane standing at the centre of a vast pale shallow water",
     KW_LIUBAI),
    ("a single bird alone in an enormous empty sky",
     "liubai", "vast blank field, one small subject centred, everything else empty",
     "a single crane standing at the centre of a vast pale shallow water",
     KW_LIUBAI),
    ("a tiny figure reduced to a speck at the base",
     "liubai", "vast blank field, one small subject centred, everything else empty",
     "one reed bending alone at the centre of an empty white field",
     KW_LIUBAI),
    ("a tiny figure at the very base of a towering cliff",
     "liubai", "vast blank field, one small subject centred, everything else empty",
     "one reed bending alone at the centre of an empty white field",
     KW_LIUBAI),
    # 枝从边缘 -> 一角
    ("one bare branch entering from the edge",
     "one_corner", "subject entering only from one edge, rest of frame empty",
     "a plum branch entering only from the lower right corner, nothing else in frame",
     KW_CONER),
]

# 新增 doc：给 liubai / one_corner / 朴赞郁 各自补具体物件
ADD = [
    # ---- 留白（居中）----
    ("Liubai Negative Space", "留白构图", "liubai",
     "vast blank field, one small subject centred, everything else empty",
     ["a small pavilion alone at the centre of a blank misty lake",
      "a single reed standing at the centre of an empty pale field"],
     KW_LIUBAI),

    # ---- 一角（贴边）----
    ("One-Corner Composition", "马一角夏半边", "one_corner",
     "subject entering only from one edge, rest of frame empty",
     ["a single sail in the upper left corner of an empty sky",
      "a scholar's sleeve and hand entering from the bottom edge only",
      "one roof eave cropping in from the top corner, nothing else"],
     KW_CONER),

    # ---- 朴赞郁：补「对称/造作/红绿」的具体物件 ----
    ("Park Chan-wook", "朴赞郁", "base",
     "ornate symmetrical staging, deep green and red, theatrical artifice",
     ["a corridor of identical doors receding exactly symmetrically",
      "two figures posed exactly mirrored across a table",
      "an ornate room where every object is placed in perfect symmetry",
      "a staircase seen dead centre with matching lamps either side, deep green and red"],
     ["对称", "造作", "红绿"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    # ---------- 0) 清洗：kw_zh 里绝不能有域词 ----------
    cleaned = 0
    for d in corpus:
        kw = d.get("kw_zh") or []
        no_dom = [w for w in kw if w not in DOMAIN_WORDS]
        if no_dom != kw:
            d["kw_zh"] = no_dom
            cleaned += 1

    # ---------- 1) 重写 / 重分配 ----------
    rewritten = 0
    changed = []
    for d in corpus:
        desc = d.get("description", "")
        for frag, new_facet, new_sig, new_desc, new_kw in REWRITE:
            if frag in desc:
                old_facet = d.get("facet")
                d["facet"] = new_facet
                # 同步 director，否则分组自相矛盾
                ent = FACET_ENTITY.get(new_facet)
                if ent:
                    d["director"], d["director_zh"] = ent
                d["kw_zh"] = new_kw
                d["style_tags"] = [x.strip() for x in new_sig.split(",")][:6]
                d["description"] = new_desc
                d["text_semantic"] = f"{new_desc}, in the style of {d['director']}"
                d["prompt"] = d.get("prompt", "").split(", in the style of")[0]
                d["prompt"] = (f"cinematic still, {new_desc}, in the style of "
                               f"{d['director']}, 35mm film, "
                               f"--ar {d.get('params', {}).get('ar', '2.35:1')} --style raw")
                rewritten += 1
                changed.append((old_facet, new_facet, new_desc[:46]))
                break

    # 同步已有 liubai 文档的 kw（去掉「一角」）
    for d in corpus:
        if d.get("facet") == "liubai" and d.get("kw_zh") == ["留白", "空旷", "一角"]:
            d["kw_zh"] = KW_LIUBAI
        if d.get("facet") == "one_corner":
            d["kw_zh"] = KW_CONER

    # ---------- 2) 新增 ----------
    new = []
    for en, zh, facet, sig, scenes, kws in ADD:
        for si, scene in enumerate(scenes):
            n += 1
            desc = f"{scene}, {sig}"
            new.append({
                "doc_id": f"d{n:04d}",
                "domain": "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": "CN", "era": "traditional",
                "facet": facet,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws,
                "description": desc,
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
    print(f"corpus_v6 -> v7 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print(f"kw_zh 清洗（去掉域词）: {cleaned} 条")
    print(f"\n重写/重分配 {rewritten} 条：")
    for a, b, desc in changed:
        print(f"  {a:<12} -> {b:<12}  {desc}")
    nf = Counter(d["facet"] for d in out)
    print(f"\n关键 facet 数量：")
    for f in ("liubai", "one_corner", "misty_river", "wu_jiang"):
        print(f"  {f:<14} {nf.get(f, 0)}")
    print(f"\n检查：liubai 里还有船吗？")
    bad = [d for d in out if d.get("facet") == "liubai" and "boat" in d["text_semantic"].lower()]
    print(f"  剩 {len(bad)} 条" + ("" if not bad else "  <-- 仍要处理"))
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V7_DONE")


if __name__ == "__main__":
    main()
