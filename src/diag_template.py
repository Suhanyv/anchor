"""
诊断：模板是否压过了内容？

假设：query 之间高度雷同（同一模板只换几个词），导致向量坍缩。
指标：
  1. query 两两余弦均值  -> 越接近 1 越坍缩
  2. doc  两两余弦均值
  3. 与「去内容模板」的相似度 -> 衡量模板贡献占比
  4. 有效信息占比（内容词 / 全部 token）
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "intfloat/multilingual-e5-small"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def mean_pairwise_cos(E):
    S = E @ E.T
    n = len(E)
    iu = np.triu_indices(n, k=1)
    return float(S[iu].mean()), float(np.percentile(S[iu], 95))


def main():
    corpus = load(os.path.join(ROOT, "data", "raw", "prompt_director.jsonl"))
    queries = load(os.path.join(ROOT, "data", "raw", "query_director.jsonl"))

    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(MODEL, device=dev)

    q_texts = [q["query"] for q in queries]
    d_texts = [d["description"] for d in corpus]
    # 纯模板（去掉内容词和导演名）
    template = "想要那种的感觉，像的电影，提示词怎么写"

    qe = m.encode(q_texts, batch_size=32, normalize_embeddings=True,
                  convert_to_numpy=True, show_progress_bar=False, prompt="query: ")
    de = m.encode(d_texts, batch_size=32, normalize_embeddings=True,
                  convert_to_numpy=True, show_progress_bar=False, prompt="passage: ")
    te = m.encode([template], normalize_embeddings=True,
                  convert_to_numpy=True, show_progress_bar=False, prompt="query: ")[0]

    print("=== query 之间的相似度 ===")
    mu, p95 = mean_pairwise_cos(qe)
    print(f"  两两余弦 均值 {mu:.4f}   95分位 {p95:.4f}")
    print(f"  向量标准差（各维平均） {qe.std(axis=0).mean():.5f}")
    sim_t = qe @ te
    print(f"  与「纯模板」相似度  均值 {sim_t.mean():.4f}  最低 {sim_t.min():.4f}  最高 {sim_t.max():.4f}")
    print("  -> 若均值 >0.90，说明模板完全主导，内容词无效")

    print("\n=== doc 之间的相似度 ===")
    mu2, p952 = mean_pairwise_cos(de)
    print(f"  两两余弦 均值 {mu2:.4f}   95分位 {p952:.4f}")

    print("\n=== 内容词的信息占比（按字符）===")
    ql = [len(t) for t in q_texts]
    # 内容 = 关键词部分（中文括号内）+ 导演名，粗略取「那种」与「的感觉」之间
    content = []
    for t in q_texts:
        a = t.find("那种") + 2
        b = t.find("的感觉")
        content.append(b - a if b > a else 0)
    print(f"  query 总长 均值 {np.mean(ql):.1f} 字")
    print(f"  关键词部分 均值 {np.mean(content):.1f} 字")
    print(f"  内容占比 {np.mean(content)/np.mean(ql):.1%}")

    print("\n=== doc 模板占比 ===")
    dl = [len(t) for t in d_texts]
    # 每条都含固定尾巴 "in the style of <dir>, 35mm film, --ar ... --v 6 --style raw"
    print(f"  description 总长 均值 {np.mean(dl):.1f} 字符")
    print(f"  固定尾巴约 55 字符 -> 占比约 {55/np.mean(dl):.1%}")

    print("\n### DIAG_DONE")


if __name__ == "__main__":
    main()
