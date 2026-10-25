"""
语料 v23：补「简牍」与「帛书」

为什么补
--------
实测一个真实查询：「一个人拿起桌上的竹简」——
**主体通道判成「武侠竹林」0.4344，赢过了风格 0.2709**，于是提示词里出现了竹林。

根因两条：
1. 库里没有「简牍」这个媒介，问竹简查不到东西
2. 主体索引里有「武侠竹林」，共用一个"竹"字 -> 字面碰撞

补进风格索引之后还有个附带好处：
**风格分会抬高（竹简对上简牍文档），主体通道就不再过门槛**（要求 `分数 > 风格分`），
误判会自动消失。这比单独去调主体阈值干净。

顺带补「帛书」——竹简→帛→纸是同一串历史，用户问到时会连着问。

corpus_v21 (1045) -> corpus_v23
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v21.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v23.jsonl")

E = [
    ("简牍", "Bamboo Slips", "CN", "战国-魏晋",
     ["bamboo slips bound with cord", "ink characters down each strip", "worn bamboo edges"],
     "a hand unrolls the bundle and the cord clicks as the strips fall open", "6s",
     [("image", "bamboo slips bound with cord, ink characters running down each strip, "
                "the roll half open on a low table",
       ["竹简", "编绳", "墨书", "半展"]),
      ("image", "a bundle of slips tied with silk cord, the bamboo edges worn dark by handling",
       ["编绳", "磨损", "成卷"]),
      ("facet", "image", "the back of a slip scraped clean where a character was corrected, "
                         "the knife marks left in the bamboo",
       ["刮削", "改字", "刀痕"]),
      ("facet", "image", "slips laid out flat in reading order, each strip catching light along its bevel",
       ["摊开", "排列", "倒角光"]),
      ("video", "a hand unrolls the bundle, the cord clicking as the strips fall open one by one",
       ["展开", "编绳声", "逐个落下"]),
      ("video", "the camera tracks along a row of slips, ink characters passing one strip at a time",
       ["横移", "墨字", "逐条掠过"])]),

    ("帛书", "Silk Manuscript", "CN", "战国-汉",
     ["silk ground with ink columns", "frayed edges", "soft sheen through the fibres"],
     "a hand lifts the silk edge and the fabric catches the light as it lifts", "6s",
     [("image", "a silk manuscript with columns of ink characters, the weave visible through the ground",
       ["帛书", "丝织基底", "墨书竖列"]),
      ("image", "silk laid flat and unweighted, edges frayed, a red seal at the end of the text",
       ["毛边", "朱印", "摊平"]),
      ("facet", "image", "ink bleeding slightly into the silk where the brush paused",
       ["墨渗", "洇开", "笔停处"]),
      ("facet", "image", "a silk scroll half unrolled over a wooden roller, the fabric holding a low sheen",
       ["半卷", "木轴", "低光泽"]),
      ("video", "the camera drifts along the silk as the ink columns pass one by one",
       ["横移", "墨列", "逐列掠过"]),
      ("video", "a hand lifts the silk edge, the fabric catching light as it lifts",
       ["手指挑起", "织物反光", "轻"])]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)
    print(f"corpus_v21: {len(corpus)} 条")

    added = []
    for zh, en, country, era, tags, cam, dur, rows in E:
        for row in rows:
            # base 行 3 元组 (kind, desc, kw)；facet 行多一个前缀 (facet, kind, desc, kw)
            if len(row) == 4:
                facet, kind, desc, kw = row
            else:
                facet, kind, desc, kw = "base", row[0], row[1], row[2]
            n += 1
            is_video = (kind == "video")
            doc = {
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": country, "era": era,
                "facet": facet,
                "style_tags": tags[:4],
                "kw_zh": kw, "batch": "书写媒介补充",
                "description": desc,
                "text_semantic": (f"{desc}, {cam}, one continuous shot, in the style of {en}"
                                  if is_video else f"{desc}, in the style of {en}"),
                "params": ({"ar": "21:9", "duration": dur, "camera": "slow"} if is_video
                           else {"ar": "2.35:1", "style": "raw"}),
                "prompt": (f"cinematic {'video' if is_video else 'still'}, {desc}, "
                           f"in the style of {en}, --ar {'21:9' if is_video else '2.35:1'} --style raw"),
            }
            if is_video:
                doc["motion"] = "SLOW"
            added.append(doc)

    out = corpus + added
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"新增 {len(added)} 条（2 实体 x 6）")
    print(f"corpus_v21 -> v23 : {len(corpus)} -> {len(out)}   实体 175 -> 177")

    # 自检：新增文档里"竹"字只出现在竹简语境
    hit = [d for d in added if "bamboo" in d["text_semantic"].lower()]
    print(f"\n含 bamboo 的新文档 {len(hit)} 条，全部属于简牍：",
          all(d["director"] == "Bamboo Slips" for d in hit))
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V23_DONE")


if __name__ == "__main__":
    main()
