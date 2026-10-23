"""
生成中/日双语训练 query（喂匀）

背景
----
v9 评测发现：日文 93.1% > 中文 85.7%。
不是中文难，是**喂得少**：
    中文 509 条（复用旧数据，句式少）
    日文 1050 条（6 套句式 x 175 组）
-> 按同样方式给中文补齐。

输出 queries_v9.jsonl = 旧 queries_v4(509) + 日文(训练句式) + 中文(训练句式)
句式一律取自 lang_templates.TRAIN_*，与评测用的 EVAL_* 严格隔离。
"""
import json
import os
import random
import sys

ROOT = r"F:\llm"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ja_lexicon import JA                     # noqa: E402
from kode_lexicon import KO, DE               # noqa: E402
from lang_templates import TRAIN_ZH, TRAIN_JA, TRAIN_KO, TRAIN_DE, _check_no_overlap  # noqa: E402

CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v7.jsonl")
SRC_Q = os.path.join(ROOT, "data", "raw", "queries_v4_fixed14b.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "queries_v10.jsonl")


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    _check_no_overlap()
    corpus = load(CORPUS)
    src = load(SRC_Q)

    groups = {}
    for d in corpus:
        if d.get("domain") not in (None, "prompt_image"):
            continue
        k = (d["director"], d.get("facet", "base"))
        g = groups.setdefault(k, {"zh": None, "ids": []})
        if g["zh"] is None:
            g["zh"] = list(d.get("kw_zh") or [])
        g["ids"].append(d["doc_id"])

    rnd = random.Random(4242)
    zh_q, ja_q = [], []
    covered = 0
    for (director, facet), g in groups.items():
        zh_kw = g["zh"] or []
        ja_map = {w: JA[w] for w in zh_kw if w in JA}
        if len(zh_kw) < 2:
            continue
        covered += 1
        pick = rnd.sample(zh_kw, min(3, len(zh_kw)))

        for ti, tpl in enumerate(TRAIN_ZH):
            zh_q.append({
                "query_id": f"qzh_{len(zh_q):04d}",
                "query": tpl.format(kw="、".join(pick)),
                "lang": "zh", "domain": "prompt_image",
                "relevant": g["ids"], "target_director": director,
                "facet": facet, "query_kind": "style",
                "template_id": f"zh:{ti}", "template": tpl,
            })

        if len(ja_map) >= 2:
            ja_pick = [JA[w] for w in pick if w in JA]
            if len(ja_pick) >= 2:
                for ti, tpl in enumerate(TRAIN_JA):
                    ja_q.append({
                        "query_id": f"qja_{len(ja_q):04d}",
                        "query": tpl.format(kw="、".join(ja_pick)),
                        "lang": "ja", "domain": "prompt_image",
                        "relevant": g["ids"], "target_director": director,
                        "facet": facet, "query_kind": "style",
                        "template_id": f"ja:{ti}", "template": tpl,
                    })

    # 韩语 / 德语（同一批组，只在有对照词时生成）
    ko_q, de_q = [], []
    for (director, facet), g in groups.items():
        zh_kw = g["zh"] or []
        if len(zh_kw) < 2:
            continue
        pick = rnd.sample(zh_kw, min(3, len(zh_kw)))
        for lang, Lex, Tpls, bucket, tag in (
                ("ko", KO, TRAIN_KO, ko_q, "ko"), ("de", DE, TRAIN_DE, de_q, "de")):
            mapped = [Lex[w] for w in pick if w in Lex]
            if len(mapped) < 2:
                continue
            for ti, tpl in enumerate(Tpls):
                bucket.append({
                    "query_id": f"q{tag}_{len(bucket):04d}",
                    "query": tpl.format(kw=", ".join(mapped)),
                    "lang": lang, "domain": "prompt_image",
                    "relevant": g["ids"], "target_director": director,
                    "facet": facet, "query_kind": "style",
                    "template_id": f"{tag}:{ti}", "template": tpl,
                })

    out = src + zh_q + ja_q + ko_q + de_q
    with open(OUT, "w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"语料 {len(corpus)} doc，覆盖组 {covered}/{len(groups)}")
    print(f"旧中文 {len(src)} + 新中文 {len(zh_q)} + 日文 {len(ja_q)} + 韩语 {len(ko_q)} + 德语 {len(de_q)} = {len(out)}")
    print(f"  -> {OUT}")
    print("\n中文样例:")
    for q in zh_q[:4]:
        print(f"  {q['query']:<36} -> {q['target_director']}")
    print("日文样例:")
    for q in ja_q[:4]:
        print(f"  {q['query']:<36} -> {q['target_director']}")
    print("\n### MLQ_DONE")


if __name__ == "__main__":
    main()
