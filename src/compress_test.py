"""
压缩实验：int8 量化 + embedding 降维，测「体积 / 速度 / 精度」三方权衡

为什么要测而不是猜：
    我们的服务瓶颈是首次加载 50s + 分发 470MB，不是单次查询 50ms。
    量化的收益必须拿实测的精度损失来换，不能凭感觉。

测法
----
精度：用 2100 条「训练没见过的新句式」里抽 400 条，比 导演级 hit@1。
      （同一批 query、同一套文档，便于横向比较）
速度：CPU 上 64 条 query 的平均编码耗时。
体积：state_dict 落盘大小。

对比
----
  A fp32 原始
  B int8 动态量化（只量化 nn.Linear）
  C fp32 + PCA 降维 384->256
  D fp32 + PCA 降维 384->128
  E fp32 + PCA 降维 384->64
"""
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v5.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-v5")
OUT = os.path.join(ROOT, "bench", "compress_report.json")
MAXLEN = 128
N_QUERY = 400


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class Enc:
    def __init__(self, path, quantize=False):
        self.tok = AutoTokenizer.from_pretrained(path)
        m = AutoModel.from_pretrained(path).eval()
        if quantize:
            m = torch.quantization.quantize_dynamic(m, {nn.Linear}, dtype=torch.qint8)
        self.enc = m
        for p in self.enc.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            mk = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * mk).sum(1) / mk.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()


def make_queries(corpus, n=400, per_group=6, seed=11):
    """复现挖掘器的池子构造方式，取一个子集"""
    import random
    rnd = random.Random(seed)
    TPLS = ["{kw}，要那种感觉", "想搜{kw}相关的东西", "{kw} 这种怎么描述",
            "给我点{kw}的参考", "{kw} 关键词有哪些", "有没有{kw}的例子",
            "怎么用英文说{kw}", "{kw}，越具体越好", "{kw} 那种调子",
            "{kw} 相关的风格叫什么", "如果只要{kw}，怎么prompt", "{kw} 这个方向的提示词"]
    groups = {}
    for d in corpus:
        k = (d["director"], d.get("facet", "base"))
        groups.setdefault(k, {"kws": d.get("kw_zh", []), "ids": []})
        groups[k]["ids"].append(d["doc_id"])
    pool = []
    for k, g in groups.items():
        if not g["kws"]:
            continue
        for _ in range(per_group):
            tpl = rnd.choice(TPLS)
            kw = "、".join(rnd.sample(g["kws"], min(rnd.choice([2, 3]), len(g["kws"]))))
            pool.append({"query": tpl.format(kw=kw), "target": k[0],
                         "facet": k[1], "relevant": g["ids"]})
    rnd.shuffle(pool)
    return pool[:n]


def hit1(qe, de, queries, directors):
    S = qe @ de.T
    good = 0
    for i, q in enumerate(queries):
        best = {}
        for j, d in enumerate(directors):
            if d not in best or S[i][j] > best[d]:
                best[d] = float(S[i][j])
        top = max(best.items(), key=lambda kv: kv[1])[0]
        if top == q["target"]:
            good += 1
    return good / len(queries)


def main():
    corpus = load(CORPUS)
    queries = make_queries(corpus)
    directors = [d["director"] for d in corpus]
    doc_texts = [d["text_semantic"] for d in corpus]
    q_texts = [q["query"] for q in queries]
    print(f"corpus {len(corpus)} doc / {len(queries)} 条新句式 query（训练未见过）\n")

    rows = []

    # ---------- A: fp32 ----------
    print("=== A   fp32 原始 ===")
    t0 = time.time()
    e32 = Enc(MODEL, quantize=False)
    load_t = time.time() - t0
    t0 = time.time()
    de32 = e32(doc_texts, "passage: ")
    dq32 = e32(q_texts, "query: ")
    enc_t = time.time() - t0
    sd = os.path.join(ROOT, "temp", "_fp32.safetensors")
    os.makedirs(os.path.dirname(sd), exist_ok=True)
    torch.save(e32.enc.state_dict(), sd)
    size32 = os.path.getsize(sd) / 2**20
    h32 = hit1(dq32, de32, queries, directors)
    per_q32 = enc_t / len(q_texts) * 1000
    print(f"  体积 {size32:7.1f} MB   加载 {load_t:5.1f}s   编码 {per_q32:5.1f} ms/条   hit@1 {h32:.4f}")
    rows.append({"name": "A fp32", "size_mb": round(size32, 1), "hit1": round(h32, 4),
                 "ms_per_query": round(per_q32, 1), "dim": 384})
    os.remove(sd)

    # ---------- B: int8 动态量化 ----------
    print("\n=== B   int8 动态量化 ===")
    t0 = time.time()
    e8 = Enc(MODEL, quantize=True)
    load_t = time.time() - t0
    t0 = time.time()
    de8 = e8(doc_texts, "passage: ")
    dq8 = e8(q_texts, "query: ")
    enc_t = time.time() - t0
    sd = os.path.join(ROOT, "temp", "_int8.pt")
    torch.save(e8.enc.state_dict(), sd)
    size8 = os.path.getsize(sd) / 2**20
    h8 = hit1(dq8, de8, queries, directors)
    per_q8 = enc_t / len(q_texts) * 1000
    print(f"  体积 {size8:7.1f} MB   加载 {load_t:5.1f}s   编码 {per_q8:5.1f} ms/条   hit@1 {h8:.4f}")
    print(f"  -> 体积 {size8/size32*100:.0f}%   速度 {per_q8/per_q32*100:.0f}%   精度 {h8-h32:+.4f}")
    rows.append({"name": "B int8动态", "size_mb": round(size8, 1), "hit1": round(h8, 4),
                 "ms_per_query": round(per_q8, 1), "dim": 384})
    os.remove(sd)

    # ---------- C/D/E: PCA 降维（作用于 embedding，不是模型本身） ----------
    print("\n=== PCA 降维（索引侧压缩，模型不变）===")
    mu = de32.mean(0, keepdims=True)
    X = de32 - mu
    # SVD 求主成分
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    print(f"  解释方差前 10 个主成分占比: " +
          ", ".join(f"{v:.3f}" for v in (S**2 / (S**2).sum())[:10]))
    for dim in (256, 128, 64):
        P = Vt[:dim].T                       # (384, dim)
        de_r = F.normalize(torch.tensor(X @ P), dim=-1).numpy()
        dq_r = F.normalize(torch.tensor((dq32 - mu) @ P), dim=-1).numpy()
        h = hit1(dq_r, de_r, queries, directors)
        idx_kb = len(corpus) * dim * 4 / 1024
        print(f"  dim={dim:>4}  索引 {idx_kb:6.0f} KB   hit@1 {h:.4f}   ({h-h32:+.4f})")
        rows.append({"name": f"C/D/E PCA-{dim}", "size_mb": None, "hit1": round(h, 4),
                     "ms_per_query": per_q32, "dim": dim,
                     "index_kb": round(idx_kb, 0)})

    print("\n" + "=" * 78)
    print(f"{'方案':<16} {'模型体积':>10} {'编码ms':>8} {'维度':>6} {'hit@1':>8} {'精度变化':>9}")
    print("=" * 78)
    for r in rows:
        sz = f"{r['size_mb']:.0f} MB" if r.get("size_mb") else "-"
        print(f"{r['name']:<16} {sz:>10} {r['ms_per_query']:>8.1f} {r['dim']:>6} "
              f"{r['hit1']:>8.4f} {r['hit1']-h32:>+9.4f}")
    print("=" * 78)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"baseline_hit1": round(h32, 4), "rows": rows}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### COMPRESS_DONE")


if __name__ == "__main__":
    main()
