"""
生成日文训练 query，让模型学会「日文说法 -> 英文文档」

起因（eval_3lang 实测）：
    中文 query 命中@1 77.4%，日文只有 49.1%（差 28.3pp）
    且日文失败样例几乎全命中日本/亚洲导演：
        不気味、夢の中 -> 期望 David Lynch，命中 Apichatpong
        長回し、群像   -> 期望 PTA，命中 溝口健二
    典型的**语言-国籍混淆**：模型没见过日文→英文的映射，
    把「日文」这个表面特征当成了「日本」这个语义特征。

做法（零翻译成本）
------------------
训练数据里只有「中文 query ↔ 英文文档」这一种跨语言对。
现在补上「日文 query ↔ 同一批英文文档」，逼模型走语义而不是国籍。
文档一条都不用翻。

输出 queries_v8.jsonl = 原 queries_v4（509 条） + 日文 query
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
SRC_Q = os.path.join(ROOT, "data", "raw", "queries_v4.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "queries_v8.jsonl")

# 复用 eval_3lang 里的中日对照表
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ja_lexicon import JA  # noqa: E402  单一来源，不依赖评测脚本

T_JA = [
    "{kw} な感じがほしい",
    "{kw} ってどう表現する",
    "{kw} っぽい雰囲気",
    "{kw} のスタイルは何て言う",
    "{kw} の映像を作りたい",
    "{kw} を英語でどう言う",
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    src = load(SRC_Q)

    # 按 (director, facet) 聚合 image 文档
    groups = {}
    for d in corpus:
        if d.get("domain") not in (None, "prompt_image"):
            continue
        k = (d["director"], d.get("facet", "base"))
        g = groups.setdefault(k, {"zh": None, "ids": [], "zh_name": ""})
        if g["zh"] is None:
            g["zh"] = list(d.get("kw_zh") or [])
            g["zh_name"] = d.get("director_zh", "")
        g["ids"].append(d["doc_id"])

    rnd = random.Random(2027)
    ja_q = []
    used_groups = 0
    for (director, facet), g in groups.items():
        zh_kw = g["zh"] or []
        ja_map = {w: JA[w] for w in zh_kw if w in JA}
        if len(ja_map) < 2:
            continue
        used_groups += 1
        zh_pick = rnd.sample(zh_kw, min(3, len(zh_kw)))
        ja_pick = [JA[w] for w in zh_pick if w in JA]
        if len(ja_pick) < 2:
            continue
        for ti, tpl in enumerate(T_JA):
            ja_q.append({
                "query_id": f"qja_{len(ja_q):04d}",
                "query": tpl.format(kw="、".join(ja_pick)),
                "lang": "ja",
                "domain": "prompt_image",
                "relevant": g["ids"],
                "target_director": director,
                "facet": facet,
                "query_kind": "style",          # 加权 x2，与中文 style 类同等待遇
                "template_id": f"ja:{ti}",
                "template": tpl,
            })

    out = src + ja_q
    with open(OUT, "w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"语料 {len(corpus)} doc，可覆盖组 {used_groups}")
    print(f"queries_v4 {len(src)} + 日文 {len(ja_q)} = {len(out)}  -> {OUT}")
    print("\n日文 query 样例：")
    for q in ja_q[:8]:
        print(f"  {q['query']:<40} -> {q['target_director']}")
    ka = sum(1 for q in ja_q if len(q["relevant"]) >= 1)
    print(f"\n正例完整的日文 query: {ka}/{len(ja_q)}")
    print("\n### JA_QUERIES_DONE")


if __name__ == "__main__":
    main()
