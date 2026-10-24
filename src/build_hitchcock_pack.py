"""
希区柯克「机制化」facet 包 —— 验证一个更大的问题：
    多面签名该怎么拆才有效？
    按情绪拆（suspense/voyeurism）= 影评人语言，用户不会这么说
    按机制拆（炸弹/画框/客厅尸体/螺旋/错认）= 可复用画面装置，用户能描述

实验设计（避免混淆）：
    语料 v3 = v2 + 希区柯克 5 个机制 facet（+15 doc）
    对比 A：v2 模型 vs v3 模型，**都在 corpus_v3 上评测**
            -> 隔离「用机制 facet 训练」的净贡献（文档都在，只差训练）
    对比 B：v2 模型在 corpus_v2 vs corpus_v3 上评测
            -> 隔离「文档覆盖」的贡献
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl")
SRC_QUERIES = os.path.join(ROOT, "data", "raw", "queries_v2b.jsonl")
OUT_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v3.jsonl")
OUT_QUERIES = os.path.join(ROOT, "data", "raw", "queries_v3.jsonl")

DIRECTOR = "Alfred Hitchcock"
ZH = "希区柯克"

# (facet_id, 英文签名, [3 个场景], [中文机制名])
MECHANISMS = [
    ("mech_object_threat",
     "an innocent object made sinister, single prop in frame, hard underlighting, unbearable stillness",
     ["a glass of milk carried up a dark staircase lit from below",
      "a door key held in a trembling hand under a single lamp",
      "a pair of scissors on a desk under harsh underlighting"],
     ["物件变凶器", "发光的牛奶", "日常物的威胁"]),

    ("mech_window_frame",
     "telephoto compression, frame within frame, a grid of windows, heat haze, voyeur distance",
     ["a grid of apartment windows at dusk with one lit window",
      "a figure seen through a window frame from across a courtyard",
      "a telephoto view of a neighbour through heat haze"],
     ["画框嵌套", "远摄窥视", "一格格窗户"]),

    ("mech_domestic_horror",
     "polite domestic surface, horror in plain sight, chest used as furniture, warm lamplight",
     ["a dinner party arranged on top of a wooden chest",
      "candles and silverware set on a locked trunk",
      "guests chatting over a covered piece of furniture"],
     ["客厅里的尸体", "表面正常", "把恐怖当家具"]),

    ("mech_vertical_dread",
     "spiral geometry, downward vertigo, sickly green light, plunging perspective",
     ["a spiral staircase seen from directly above with a descending figure",
      "a plunging view down an open stairwell in green light",
      "a dizzying zoom toward a receding corridor"],
     ["螺旋", "垂直恐惧", "往下掉的眩晕"]),

    ("mech_wrong_man",
     "ordinary man crushed by machinery, flat fluorescent light, bureaucratic exposure, no escape",
     ["a man in a police lineup under flat fluorescent light",
      "a handcuffed wrist on a steel table",
      "an ordinary face under a numbered placard"],
     ["普通人被误认", "官僚荧光灯", "错误的人"]),
]

SCENES_PER = 3

# 用户口吻的中文 query（每个机制 2 条）
QUERIES = {
    "mech_object_threat": [
        "一个杯子就让人紧张起来那种感觉",
        "普通的东西变得很可怕，怎么描述",
    ],
    "mech_window_frame": [
        "从窗外偷看整栋楼邻居的那种画面",
        "一格格窗户里各过各的生活，怎么prompt",
    ],
    "mech_domestic_horror": [
        "表面很正常的晚宴，其实底下藏着事",
        "把恐怖摆在明面上的画面怎么搜",
    ],
    "mech_vertical_dread": [
        "往下掉的那种眩晕感，螺旋楼梯",
        "从上往下看的楼梯，看着就头晕",
    ],
    "mech_wrong_man": [
        "普通人被当成了罪犯那种压抑",
        "警局里一排人站着认人的画面",
    ],
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC_CORPUS)
    queries = load(SRC_QUERIES)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new_docs, new_q = [], []
    for fid, sig, scenes, kws in MECHANISMS:
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
                "lang": "en", "director": DIRECTOR, "director_zh": ZH,
                "country": "UK/US", "era": "1920s-70s",
                "facet": fid,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws,
                "description": desc,
                "text_semantic": f"{desc}, in the style of {DIRECTOR}",
                "params": {"ar": ar, "style": "raw"},
                "prompt": f"cinematic {'video' if is_video else 'still'}, {desc}, "
                          f"in the style of {DIRECTOR}, 35mm film, --ar {ar} {tail}",
            }
            ids.append(nd["doc_id"])
            new_docs.append(nd)

        for qi, text in enumerate(QUERIES[fid]):
            new_q.append({
                "query_id": f"qh_{fid}_{qi}",
                "query": text,
                "lang": "zh", "domain": "prompt_image",
                "relevant": ids,
                "target_director": DIRECTOR,
                "facet": fid,
                "query_kind": "style",
                "template_id": f"handcrafted:{fid}",
                "template": "handcrafted",
            })

    corpus3 = corpus + new_docs
    queries3 = queries + new_q

    with open(OUT_CORPUS, "w", encoding="utf-8") as f:
        for d in corpus3:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(OUT_QUERIES, "w", encoding="utf-8") as f:
        for q in queries3:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"corpus v2 -> v3 : {len(corpus)} -> {len(corpus3)}  (+{len(new_docs)})")
    print(f"queries v2 -> v3: {len(queries)} -> {len(queries3)}  (+{len(new_q)})")
    print(f"\n希区柯克 doc 总数: {sum(1 for d in corpus3 if d['director']==DIRECTOR)}")
    print("\n各机制 facet:")
    for fid, _, scenes, kws in MECHANISMS:
        cnt = sum(1 for d in corpus3 if d.get("facet") == fid)
        print(f"  {fid:<24} {cnt} doc   {'、'.join(kws)}")
        print(f"     e.g. {scenes[0][:74]}")
    print("\n手工中文 query:")
    for fid, lst in QUERIES.items():
        for t in lst:
            print(f"  [{fid.replace('mech_',''):<16}] {t}")
    print(f"\n-> {OUT_CORPUS}\n-> {OUT_QUERIES}")
    print("\n### HITCHCOCK_PACK_DONE")


if __name__ == "__main__":
    main()
