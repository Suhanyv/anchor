"""
交叉编码器 reranker —— 补完「召回 + 精排」两阶段架构。

背景：
  bi-encoder 把 query 和 doc 各自压成向量，必须共享同一空间 -> 跨域会打架。
  cross-encoder 把两者拼在一起过编码器，token 级交互 -> 天然跨域。
  所以设计上：embedding 分路召回，reranker 单一收口。

网络不可达（hf-mirror / huggingface.co 均超时），无法下载 bge-reranker-base。
解法：用已缓存的 multilingual-e5-small 当骨干自建交叉编码器，零下载。

评测协议（与之前一致，可对比）：
  * 模板级留出 5 折（整段句式不在训练集里）
  * 一阶段固定用未训练的 e5-small 取 top-K —— 隔离出 reranker 的净贡献
  * 指标：Recall@10 / MRR@10 / Top-1 命中率 / 首个相关的平均排名
"""
import argparse
import json
import os
import time
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl")
QUERIES = os.path.join(ROOT, "data", "raw", "queries_v2b.jsonl")
BASE = "intfloat/multilingual-e5-small"
LOG = os.path.join(ROOT, "bench", "train_rerank_log.json")

MAXLEN = 256
Q_PREFIX = "query: "
P_PREFIX = "passage: "


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------------------------------------------------------------- 骨干
class BiEncoder(nn.Module):
    def __init__(self, name):
        super().__init__()
        self.tok = AutoTokenizer.from_pretrained(name)
        self.enc = AutoModel.from_pretrained(name)

    @torch.no_grad()
    def encode(self, texts, prefix, bs=64):
        self.enc.eval()
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=128, return_tensors="pt")
            b = {k: v.cuda() for k, v in b.items()}
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out)


class CrossEncoder(nn.Module):
    def __init__(self, name):
        super().__init__()
        self.tok = AutoTokenizer.from_pretrained(name)
        self.enc = AutoModel.from_pretrained(name)
        hidden = self.enc.config.hidden_size
        self.head = nn.Linear(hidden, 1)

    def forward(self, queries, passages):
        b = self.tok(queries, passages, padding=True, truncation=True,
                     max_length=MAXLEN, return_tensors="pt")
        b = {k: v.cuda() for k, v in b.items()}
        h = self.enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-6)
        return self.head(pooled.float()).squeeze(-1)


class PairDS(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return self.rows[i]


# ---------------------------------------------------------------- 指标
def metrics(rankings, relevant, k=10):
    """rankings: list of doc_id lists（已排序）"""
    rec, mrr, top1, first = [], [], [], []
    for ranked, rel in zip(rankings, relevant):
        rel = set(rel)
        head = ranked[:k]
        hit = [d for d in head if d in rel]
        rec.append(len(hit) / len(rel))
        if hit:
            pos = ranked.index(hit[0]) + 1
            mrr.append(1.0 / pos)
            first.append(pos)
        else:
            mrr.append(0.0)
            first.append(10 ** 6)
        top1.append(1.0 if ranked and ranked[0] in rel else 0.0)
    return {
        f"recall@{k}": float(np.mean(rec)),
        "mrr@10": float(np.mean(mrr)),
        "top1": float(np.mean(top1)),
        "mean_first_rank": float(np.mean([x for x in first if x < 10 ** 6]) if any(x < 10 ** 6 for x in first) else 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--n-neg", type=int, default=4)
    ap.add_argument("--n-folds", type=int, default=5)
    a = ap.parse_args()

    torch.manual_seed(42); np.random.seed(42)

    corpus = load(CORPUS)
    queries = load(QUERIES)
    doc_text = {d["doc_id"]: d["text_semantic"] for d in corpus}
    doc_ids = [d["doc_id"] for d in corpus]
    print(f"corpus={len(corpus)} queries={len(queries)}")

    # ---- 一阶段：固定用未训练的 bi-encoder 取 top-K（隔离 reranker 贡献）
    bi = BiEncoder(BASE).cuda()
    de = bi.encode([d["text_semantic"] for d in corpus], P_PREFIX)
    qe = bi.encode([q["query"] for q in queries], Q_PREFIX)
    S = (qe @ de.T).cpu().numpy()
    print("stage-1 (base e5, 未训练) 完成编码")

    stage1 = {}
    topk_ids = {}
    for i, q in enumerate(queries):
        order = np.argsort(-S[i])[:a.topk]
        ids = [doc_ids[j] for j in order]
        topk_ids[q["query_id"]] = ids
        stage1[q["query_id"]] = ids

    base_m = metrics([stage1[q["query_id"]] for q in queries],
                     [q["relevant"] for q in queries])
    print(f"\n=== stage-1 基线（无 rerank）===")
    print(f"  recall@10={base_m['recall@10']:.4f}  mrr@10={base_m['mrr@10']:.4f} "
          f" top1={base_m['top1']:.4f}  mean_first_rank={base_m['mean_first_rank']:.2f}")

    # ---- 5 折模板留出
    folds = defaultdict(list)
    for q in queries:
        folds[q["template_id"]].append(q)
    tpls = sorted(folds)
    print(f"\n模板数: {len(tpls)}  折数: {a.n_folds}")

    agg = defaultdict(list)
    t0 = time.time()
    for f in range(a.n_folds):
        dev_tpls = {t for i, t in enumerate(tpls) if i % a.n_folds == f}
        dev = [q for t in dev_tpls for q in folds[t]]
        train = [q for t in tpls if t not in dev_tpls for q in folds[t]]

        # 训练对：正例 + 从 top-K 里挖的 hard negative（同折内，无泄漏）
        rows = []
        for q in train:
            pos = set(q["relevant"])
            for d in q["relevant"]:
                rows.append((q["query"], doc_text[d], 1.0))
            negs = [d for d in topk_ids[q["query_id"]] if d not in pos][:a.n_neg]
            for d in negs:
                rows.append((q["query"], doc_text[d], 0.0))
        if not rows:
            continue

        ce = CrossEncoder(BASE).cuda().train()
        opt = torch.optim.AdamW(ce.parameters(), lr=a.lr, weight_decay=0.01)
        dl = DataLoader(PairDS(rows), batch_size=a.batch_size, shuffle=True,
                        drop_last=True, collate_fn=lambda b: b)
        for ep in range(a.epochs):
            tot = nb = 0
            for batch in dl:
                qs = [r[0] for r in batch]
                ps = [r[1] for r in batch]
                ys = torch.tensor([r[2] for r in batch], device="cuda")
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits = ce(qs, ps)
                loss = F.binary_cross_entropy_with_logits(logits.float(), ys)
                opt.zero_grad(set_to_none=True); loss.backward()
                torch.nn.utils.clip_grad_norm_(ce.parameters(), 1.0)
                opt.step()
                tot += loss.item(); nb += 1

        # 在 holdout 折上：对 top-K 重排序
        ce.eval()
        reranked = []
        for q in dev:
            cand = topk_ids[q["query_id"]]
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                sc = []
                for i in range(0, len(cand), 32):
                    chunk = cand[i:i + 32]
                    sc.append(ce([q["query"]] * len(chunk),
                                 [doc_text[d] for d in chunk]).float().cpu())
                sc = torch.cat(sc).numpy()
            order = np.argsort(-sc)
            reranked.append([cand[j] for j in order])

        m_after = metrics(reranked, [q["relevant"] for q in dev])
        m_before = metrics([stage1[q["query_id"]] for q in dev], [q["relevant"] for q in dev])
        print(f"  fold {f}: dev={len(dev):>3}  "
              f"recall@10 {m_before['recall@10']:.3f}->{m_after['recall@10']:.3f}  "
              f"mrr {m_before['mrr@10']:.3f}->{m_after['mrr@10']:.3f}  "
              f"top1 {m_before['top1']:.3f}->{m_after['top1']:.3f}  "
              f"first {m_before['mean_first_rank']:.1f}->{m_after['mean_first_rank']:.1f}")
        for k, v in m_after.items():
            agg[f"after_{k}"].append(v)
        for k, v in m_before.items():
            agg[f"before_{k}"].append(v)
        agg["n"].append(len(dev))
        del ce
        torch.cuda.empty_cache()

    print(f"\n=== {a.n_folds} 折汇总（{time.time()-t0:.0f}s）===")
    print(f"{'指标':<20} {'rerank 前':>12} {'rerank 后':>12} {'变化':>10}")
    for k in ("recall@10", "mrr@10", "top1", "mean_first_rank"):
        b = np.mean(agg[f"before_{k}"]); af = np.mean(agg[f"after_{k}"])
        if k == "mean_first_rank":
            print(f"{k:<20} {b:>12.2f} {af:>12.2f} {af-b:>+10.2f}")
        else:
            print(f"{k:<20} {b:>12.4f} {af:>12.4f} {(af-b)*100:>+9.2f}pp")

    out = {"config": vars(a),
           "stage1_full": base_m,
           "before": {k: float(np.mean(agg[f"before_{k}"])) for k in
                      ("recall@10", "mrr@10", "top1", "mean_first_rank")},
           "after": {k: float(np.mean(agg[f"after_{k}"])) for k in
                     ("recall@10", "mrr@10", "top1", "mean_first_rank")}}
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {LOG}")
    print("\n### RERANK_DONE")


if __name__ == "__main__":
    main()
