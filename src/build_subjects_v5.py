"""
题材索引 v5：补「简牍」「帛书」

为什么加在题材而不是风格
------------------------
实测「一个人拿起桌上的竹简」：
    主体 武侠竹林 0.4344 ✅ 过门槛
    风格 简牍     0.2709 ❌ 太低
于是输出了竹林。根因是**风格语料是训练过的英文索引**，
中文「竹简」映射到 "bamboo slips" 天然弱，训练数据也没覆盖这个词。

而**题材索引是零样本的、带中文锚点**（`subjects_v4` 的 kw_zh 直接进文本），
竹简本身就是个"能被画出来的物件"，本来就该在这里。

好处：**不用重训模型**，加完立刻生效。

subjects_v4 (40) -> subjects_v5 (52)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data/raw/subjects_v4.jsonl")
OUT = os.path.join(ROOT, "data/raw/subjects_v5.jsonl")

# (英文名, 中文名, 输出短语, 中文关键词, type, [描述变体])
NEW = [
    ("Bamboo Slips", "简牍",
     "a bundle of bamboo slips bound with cord, ink characters down each strip",
     ["竹简", "木牍", "简册", "竹片", "编绳", "墨书", "竹卷", "简牍"],
     "character_object",
     ["bamboo slips bound with cord, the roll half open on a table",
      "a bundle of slips held in both hands, ink characters running down each strip",
      "slips laid out flat in reading order, edges worn dark by handling",
      "the back of a slip scraped clean where a character was corrected"]),

    ("Silk Manuscript", "帛书",
     "a silk manuscript with columns of ink characters, frayed edges, a soft sheen",
     ["帛书", "丝帛", "绢帛", "帛卷", "墨字", "朱印", "丝织"],
     "character_object",
     ["a silk manuscript with columns of ink characters, the weave showing through",
      "silk laid flat and unweighted, edges frayed, a red seal at the end",
      "a silk scroll half unrolled over a wooden roller"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    rows = load(SRC)
    n = 40
    added = []
    for en, zh, phrase, kw, typ, variants in NEW:
        for v in variants:
            n += 1
            added.append({
                "doc_id": f"s{n:04d}",
                "kind": "subject",
                "subject_en": en, "subject_zh": zh,
                "phrase": phrase,
                "kw_zh": kw,
                "type": typ,
                "description": v,
                # 中文锚点：零样本索引必须说用户的语言（已验证过的做法）
                "text_semantic": f"{v}，{zh}，{'、'.join(kw)}",
            })

    out = rows + added
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  题材 v4 {len(rows)} -> v5 {len(out)}（新增 {len(added)} 条 / {len(NEW)} 个题材）")
    for en, zh, *_ in NEW:
        print(f"    {zh:<6} {en}")
    print(f"\n-> {OUT}")
    print("\n### SUBJECTS_V5_DONE")


if __name__ == "__main__":
    main()
