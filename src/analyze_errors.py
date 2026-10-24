"""
错误分析：中文 query -> 英文导演提示词，看模型到底错在哪。

要回答的问题
  1. 正确答案到底沉到第几名？（Recall@10/20/50/100）
  2. 召回的是不是「风格近亲」导演？（可救） 还是彻底乱猜？（难救）
  3. 哪些导演最容易混淆？-> 直接变成 hard negatives
"""
import json
import os
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
QUERIES = os.path.join(ROOT, "data", "raw", "query_director.jsonl")
MODEL = "intfloat/multilingual-e5-small"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    queries = load(QUERIES)
    print(f"corpus={len(corpus)} queries={len(queries)}")

    from sentence_transformers import SentenceTransformer
    import torch

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL, device=dev)
    print(f"model on {dev}")

    doc_texts = [d["description"] for d in corpus]
    doc_emb = model.encode(doc_texts, batch_size=32, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False,
                           prompt="passage: ")
    q_emb = model.encode([q["query"] for q in queries], batch_size=32,
                         normalize_embeddings=True, convert_to_numpy=True,
                         show_progress_bar=False, prompt="query: ")

    sims = q_emb @ doc_emb.T
    doc_director = [d["director"] for d in corpus]
    doc_tags = [set(d["style_tags"]) for d in corpus]

    # ---- 1. 正确答案排到第几 ----
    ranks = []
    recall_at = defaultdict(int)
    for qi, q in enumerate(queries):
        order = np.argsort(-sims[qi])
        pos = [i for i in range(len(order)) if corpus[order[i]]["doc_id"] in set(q["relevant"])]
        best = (pos[0] + 1) if pos else 10**9
        ranks.append(best)
        for kk in (10, 20, 50, 100):
            if any(p < kk for p in pos):
                recall_at[kk] += 1

    n = len(queries)
    print("\n=== 正确答案的排名分布 ===")
    print(f"  Recall@10  = {recall_at[10]/n:6.2%}")
    print(f"  Recall@20  = {recall_at[20]/n:6.2%}")
    print(f"  Recall@50  = {recall_at[50]/n:6.2%}")
    print(f"  Recall@100 = {recall_at[100]/n:6.2%}")
    print(f"  中位排名   = {int(np.median(ranks))}")
    print(f"  命中前100  = {sum(1 for r in ranks if r <= 100)}/{n}")

    # ---- 2. 召回的是不是风格近亲 ----
    near_miss, random_miss = 0, 0
    confusion = Counter()
    examples = []

    for qi, q in enumerate(queries):
        order = np.argsort(-sims[qi])[:5]
        truth = q["target_director"]
        got = [doc_director[i] for i in order]
        # 该 query 对应导演的 style_tags
        t_doc = next(d for d in corpus if d["director"] == truth)
        t_tags = set(t_doc["style_tags"])
        hit = truth in got
        if not hit:
            overlap = max(len(t_tags & doc_tags[i]) for i in order)
            if overlap >= 1:
                near_miss += 1
            else:
                random_miss += 1
            confusion[(truth, got[0])] += 1
        examples.append((q["query"], truth, got, hit))

    misses = near_miss + random_miss
    print("\n=== 未命中时的性质 ===")
    if misses:
        print(f"  风格近亲（有 tag 重叠）= {near_miss}/{misses}  ({near_miss/misses:.1%})")
        print(f"  完全无关（无 tag 重叠）= {random_miss}/{misses}  ({random_miss/misses:.1%})")
    print("  -> 近亲比例高 = 模型懂风格，只是分不清细分；训练 hard negative 很有效")
    print("  -> 无关比例高 = 跨语言对齐根本没建立；要补平行语料")

    print("\n=== 最常见的混淆对（前 12）===")
    for (truth, got), c in confusion.most_common(12):
        print(f"  {truth:<28} 被误认为 {got:<28} x{c}")

    print("\n=== 样例（前 8 条 query）===")
    for q, truth, got, hit in examples[:8]:
        mark = "OK  " if hit else "MISS"
        print(f"\n  [{mark}] {q}")
        print(f"       正确: {truth}")
        print(f"       Top5: {', '.join(got[:5])}")

    out = {
        "model": MODEL,
        "recall_at": {k: recall_at[k] / n for k in recall_at},
        "median_rank": float(np.median(ranks)),
        "near_miss_ratio": (near_miss / misses) if misses else None,
        "top_confusions": [{"truth": t, "predicted": g, "count": c}
                           for (t, g), c in confusion.most_common(30)],
    }
    p = os.path.join(ROOT, "bench", "error_analysis.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### ERROR_ANALYSIS_DONE")


if __name__ == "__main__":
    main()
