"""
2x2 消融：把「文档是否含导演名」和「query 是否做别名归一化」两件事分开。

  A: description      + 原始 query     <- 之前的「基线」
  B: description      + 归一化 query
  C: text_semantic    + 原始 query     <- 文档含名字
  D: text_semantic    + 归一化 query   <- 两边都有名字

预期：A≈B（别名无用，文档无名字），C 明显高于 A，D 再高于 C。
"""
import json
import os
from collections import defaultdict

import numpy as np

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
Q_ORIG = os.path.join(ROOT, "data", "raw", "query_director.jsonl")
Q_NORM = os.path.join(ROOT, "data", "raw", "query_director_norm.jsonl")
MODEL = "intfloat/multilingual-e5-small"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    qs = {"orig": load(Q_ORIG), "norm": load(Q_NORM)}

    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(MODEL, device=dev)
    print(f"model {MODEL} on {dev}\n")

    # 预编码两组 doc 字段
    doc_emb = {}
    for field in ("description", "text_semantic"):
        texts = [d[field] for d in corpus]
        doc_emb[field] = m.encode(texts, batch_size=32, normalize_embeddings=True,
                                  convert_to_numpy=True, show_progress_bar=False,
                                  prompt="passage: ")
        print(f"encoded docs[{field}] : {len(texts)}")

    q_emb = {}
    for tag, qlist in qs.items():
        q_emb[tag] = m.encode([q["query"] for q in qlist], batch_size=32,
                              normalize_embeddings=True, convert_to_numpy=True,
                              show_progress_bar=False, prompt="query: ")
        print(f"encoded queries[{tag}] : {len(qlist)}")

    combos = [
        ("A", "description", "orig", "description + 原始query（旧基线）"),
        ("B", "description", "norm", "description + 归一化query"),
        ("C", "text_semantic", "orig", "含名字文档 + 原始query"),
        ("D", "text_semantic", "norm", "含名字文档 + 归一化query"),
    ]

    results = {}
    print("\n" + "=" * 92)
    print(f"{'':2} {'组合':<34} {'Recall@10':>10} {'MRR@10':>9} {'NDCG@10':>9}   {'name类':>8} {'both类':>8} {'style类':>8}")
    print("=" * 92)

    for tag, field, qtag, desc in combos:
        E = doc_emb[field]
        Q = q_emb[qtag]
        S = Q @ E.T
        qlist = qs[qtag]

        per_kind = defaultdict(list)
        recs, mrrs, ndcgs = [], [], []
        for i, q in enumerate(qlist):
            order = np.argsort(-S[i])
            ranked = [corpus[j]["doc_id"] for j in order[:10]]
            rel = set(q["relevant"])
            hit = [r for r in ranked if r in rel]
            rec = len(hit) / len(rel)
            mrr = 1.0 / (ranked.index(hit[0]) + 1) if hit else 0.0
            dcg = sum(1.0 / np.log2(k + 2) for k, d in enumerate(ranked) if d in rel)
            ideal = sum(1.0 / np.log2(k + 2) for k in range(min(len(rel), 10)))
            ndcg = dcg / ideal if ideal else 0.0
            recs.append(rec); mrrs.append(mrr); ndcgs.append(ndcg)
            per_kind[q.get("query_kind", "?")].append(rec)

        results[tag] = dict(recall=float(np.mean(recs)), mrr=float(np.mean(mrrs)),
                            ndcg=float(np.mean(ndcgs)),
                            per_kind={k: float(np.mean(v)) for k, v in per_kind.items()})
        pk = results[tag]["per_kind"]
        print(f"{tag:2} {desc:<34} {np.mean(recs):>10.4f} {np.mean(mrrs):>9.4f} {np.mean(ndcgs):>9.4f}   "
              f"{pk.get('name', 0):>8.4f} {pk.get('both', 0):>8.4f} {pk.get('style', 0):>8.4f}")

    print("=" * 92)
    print("\n=== 结论 ===")
    a, b = results["A"]["recall"], results["B"]["recall"]
    c, d = results["C"]["recall"], results["D"]["recall"]
    print(f"  别名归一化（无名字文档 A->B）  : {a:.4f} -> {b:.4f}  ({(b-a)/a*100:+.1f}%)")
    print(f"  文档加导演名（C->C）           : {a:.4f} -> {c:.4f}  ({(c-a)/a*100:+.1f}%)")
    print(f"  两者叠加（A->D）               : {a:.4f} -> {d:.4f}  ({(d-a)/a*100:+.1f}%)")
    print(f"  name 类 (A->D): {results['A']['per_kind'].get('name',0):.4f} -> {results['D']['per_kind'].get('name',0):.4f}")

    p = os.path.join(ROOT, "bench", "ablation_alias.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### ABLATION_DONE")


if __name__ == "__main__":
    main()
