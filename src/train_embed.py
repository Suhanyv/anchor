"""
训练：把 style 类（中文风格词 -> 英文提示词）从 0.3452 推上去。

训练目标明确锁定 style 类，而不是总体数字 —— 总体已被人名匹配撑高，不可信。

损失：InfoNCE = in-batch negatives + 每 query 的 hard negatives
      （复用实测结论：batch 32、seq 128、lr 2e-5 防跨语言对齐遗忘）

自定步调：每 REGMINE_EVERY 个 epoch 用当前模型重新挖掘 hard negatives
          —— 模型挑自己现在最容易错的样本，就是"自己感兴趣"的可操作定义
"""
import argparse
import json
import os
import random
import time
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
QUERIES = os.path.join(ROOT, "data", "raw", "query_director.jsonl")
BASE = "intfloat/multilingual-e5-small"
OUT_DIR = os.path.join(ROOT, "models", "e5-small-director-v1")
LOG = os.path.join(ROOT, "bench", "train_log.json")

Q_PREFIX = "query: "
P_PREFIX = "passage: "
MAXLEN = 128


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------------------------------------------------------------- 模型
class Embedder(nn.Module):
    def __init__(self, name, maxlen=MAXLEN):
        super().__init__()
        self.tok = AutoTokenizer.from_pretrained(name)
        self.enc = AutoModel.from_pretrained(name)
        self.maxlen = maxlen

    def forward(self, texts, prefix):
        b = self.tok([prefix + t for t in texts], padding=True, truncation=True,
                     max_length=self.maxlen, return_tensors="pt")
        b = {k: v.cuda() for k, v in b.items()}
        out = self.enc(**b).last_hidden_state           # (B, L, H)
        mask = b["attention_mask"].unsqueeze(-1).float()
        pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1e-6)
        return F.normalize(pooled.float(), dim=-1)


# ---------------------------------------------------------------- 数据
class PairDS(Dataset):
    """(query, positive) 对；hard negatives 由 batch 内按需查表。"""

    def __init__(self, pairs):
        self.pairs = pairs

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, i):
        return self.pairs[i]


def build_pairs(train_qs, corpus, weight_style=2.0):
    """风格类 query 权重更高（因为那是我们要优化的指标）。"""
    pairs = []
    for q in train_qs:
        w = int(weight_style) if q["query_kind"] == "style" else 1
        for _ in range(w):
            for did in q["relevant"]:
                pairs.append((q["query"], did))
    return pairs


# ---------------------------------------------------------------- 评估
@torch.no_grad()
def evaluate(model, corpus, qs, k=10, bs=64):
    model.eval()
    doc_ids = [d["doc_id"] for d in corpus]
    idx_of = {d: i for i, d in enumerate(doc_ids)}

    de = []
    for i in range(0, len(corpus), bs):
        chunk = [d["text_semantic"] for d in corpus[i:i + bs]]
        de.append(model(chunk, P_PREFIX).cpu())
    de = torch.cat(de)

    qe = []
    for i in range(0, len(qs), bs):
        chunk = [q["query"] for q in qs[i:i + bs]]
        qe.append(model(chunk, Q_PREFIX).cpu())
    qe = torch.cat(qe)

    S = (qe @ de.T).numpy()
    per_kind = defaultdict(list)
    allr = []
    for i, q in enumerate(qs):
        order = np.argsort(-S[i])[:k]
        rel = set(q["relevant"])
        hit = [doc_ids[j] for j in order if doc_ids[j] in rel]
        r = len(hit) / len(rel)
        per_kind[q["query_kind"]].append(r)
        allr.append(r)
    model.train()
    return float(np.mean(allr)), {k2: float(np.mean(v)) for k2, v in per_kind.items()}


# ---------------------------------------------------------------- 挖负例
@torch.no_grad()
def mine_hard(model, corpus, qs, n_hard=4, bs=64):
    """对每个 query，取当前模型排序里最靠前但不是正例的 doc。"""
    model.eval()
    de = []
    for i in range(0, len(corpus), bs):
        de.append(model([d["text_semantic"] for d in corpus[i:i + bs]], P_PREFIX).cpu())
    de = torch.cat(de)
    qe = []
    for i in range(0, len(qs), bs):
        qe.append(model([q["query"] for q in qs[i:i + bs]], Q_PREFIX).cpu())
    qe = torch.cat(qe)
    S = (qe @ de.T).numpy()

    doc_ids = [d["doc_id"] for d in corpus]
    hard = {}
    for i, q in enumerate(qs):
        rel = set(q["relevant"])
        picked = []
        for j in np.argsort(-S[i]):
            if doc_ids[j] not in rel:
                picked.append(doc_ids[j])
                if len(picked) >= n_hard:
                    break
        hard[q["query"]] = picked
    model.train()
    return hard


# ---------------------------------------------------------------- 训练
def collate(batch_pairs, hard, doc_text, B):
    """in-batch 正例 + 每 query 自己的 hard negatives。"""
    qs = [p[0] for p in batch_pairs]
    pos = [doc_text[p[1]] for p in batch_pairs]
    n_hard = max((len(hard.get(q, [])) for q in qs), default=0)
    negs = []
    for q in qs:
        h = hard.get(q, [])
        h = (h + [h[-1]] * n_hard)[:n_hard] if h else [pos[0]] * n_hard
        negs.append(h)
    return qs, pos, negs, n_hard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--n-hard", type=int, default=4)
    ap.add_argument("--regmine-every", type=int, default=5)
    ap.add_argument("--dev-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fold", type=int, default=-1, help="交叉验证折号（-1 表示不用 CV）")
    ap.add_argument("--n-folds", type=int, default=1)
    ap.add_argument("--log-suffix", type=str, default="")
    ap.add_argument("--skip-save", action="store_true", help="CV 时不落盘模型（省 USB 写入）")
    ap.add_argument("--select-mode", choices=["best", "final"], default="best",
                    help="best=在 dev 上挑最优(有选择偏差)；final=固定 epoch，报告最后一轮(无偏)")
    ap.add_argument("--split-by", choices=["query", "template"], default="query",
                    help="query=按 query 划分；template=按句式模板整段留出(更严格)")
    ap.add_argument("--out-dir", default=OUT_DIR, help="模型保存目录")
    ap.add_argument("--corpus", default=CORPUS, help="语料 jsonl")
    ap.add_argument("--queries", default=QUERIES, help="query jsonl")
    a = ap.parse_args()

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)

    corpus = load(a.corpus)
    queries = load(a.queries)
    doc_text = {d["doc_id"]: d["text_semantic"] for d in corpus}

    # 分层划分：按 query_kind 保证每类都有
    by_kind = defaultdict(list)
    for q in queries:
        by_kind[q["query_kind"]].append(q)

    if a.split_by == "template":
        # 模板级留出：整段句式分到同一折，训练只见过其他句式
        # -> 检验「换一种说法」是否还能检索到，最接近真实泛化
        by_kind_tpl = defaultdict(lambda: defaultdict(list))
        for q in queries:
            by_kind_tpl[q["query_kind"]][q.get("template_id", q["query_id"])].append(q)
        dev, train = [], []
        dev_tpls = []
        for kind in sorted(by_kind_tpl):
            tpls = sorted(by_kind_tpl[kind])
            for i, t in enumerate(tpls):
                if i % a.n_folds == a.fold:
                    dev.extend(by_kind_tpl[kind][t])
                    dev_tpls.append(t)
                else:
                    train.extend(by_kind_tpl[kind][t])
        print(f"[split=template] dev 模板 ({len(dev_tpls)}): {dev_tpls}")
    elif a.n_folds > 1:
        # 分层轮转，确定性；折号跨 0..n_folds-1 时全部 query 恰好各当一次 dev
        dev, train = [], []
        for kind, lst in by_kind.items():
            lst = sorted(lst, key=lambda q: q["query_id"])
            for i, q in enumerate(lst):
                (dev if i % a.n_folds == a.fold else train).append(q)
    else:
        dev, train = [], []
        for kind, lst in by_kind.items():
            lst = list(lst)
            random.shuffle(lst)
            n_dev = max(1, int(len(lst) * a.dev_ratio))
            dev += lst[:n_dev]
            train += lst[n_dev:]
    print(f"train={len(train)} dev={len(dev)}  ({ {k: sum(1 for q in dev if q['query_kind']==k) for k in by_kind} } in dev)")

    model = Embedder(BASE).cuda()
    model.train()

    print("\n=== 训练前 dev 基线 ===")
    r0, k0 = evaluate(model, corpus, dev)
    print(f"  overall={r0:.4f}  " + "  ".join(f"{k}={v:.4f}" for k, v in sorted(k0.items())))

    pairs = build_pairs(train, corpus)
    print(f"\n训练对: {len(pairs)} （style 类加权 x2）")

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    steps_per_epoch = max(1, len(pairs) // a.batch_size)
    total = steps_per_epoch * a.epochs
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=a.lr, total_steps=total, pct_start=0.1)

    hard = mine_hard(model, corpus, train, a.n_hard)
    log = []
    best = {"style": -1.0, "epoch": -1}
    t0 = time.time()

    for ep in range(1, a.epochs + 1):
        if ep > 1 and (ep - 1) % a.regmine_every == 0:
            hard = mine_hard(model, corpus, train, a.n_hard)
            print(f"  [re-mined hard negatives @ epoch {ep}]")

        ds = PairDS(pairs)
        # collate_fn 直通：避免默认 collate 把 (q,id) 元组转置成 [(q...),(id...)]
        dl = DataLoader(ds, batch_size=a.batch_size, shuffle=True, drop_last=True,
                        collate_fn=lambda b: b)
        tot_loss, nb = 0.0, 0

        for batch in dl:
            batch = list(batch)
            qs, pos, negs, n_hard = collate(batch, hard, doc_text, a.batch_size)

            with torch.autocast("cuda", dtype=torch.bfloat16):
                qe = model(qs, Q_PREFIX)
                pe = model(pos, P_PREFIX)
                S_in = qe @ pe.T                                  # (B,B)
                if n_hard > 0:
                    flat = [d for row in negs for d in row]        # B*n_hard
                    ne = model(flat, P_PREFIX).view(len(qs), n_hard, -1)
                    S_h = torch.einsum("bd,bnd->bn", qe, ne)       # (B,n_hard)
                    S = torch.cat([S_in, S_h], dim=1) / 0.05
                else:
                    S = S_in / 0.05
                target = torch.arange(len(qs), device="cuda")
                loss = F.cross_entropy(S, target)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
            tot_loss += loss.item(); nb += 1

        avg_loss = tot_loss / max(nb, 1)
        r, kd = evaluate(model, corpus, dev)
        style = kd.get("style", 0.0)
        print(f"epoch {ep:>3}  loss={avg_loss:.4f}  dev_overall={r:.4f}  "
              f"style={style:.4f}  both={kd.get('both',0):.4f}  name={kd.get('name',0):.4f}")

        log.append({"epoch": ep, "loss": avg_loss, "dev_overall": r, **kd})
        if a.select_mode == "final":
            take = (ep == a.epochs)               # 固定 epoch，报告最后一轮：无选择偏差
        else:
            take = (style > best["style"])        # 在 dev 上挑最优：偏乐观
        if take:
            best = {"style": style, "epoch": ep, "overall": r}
            if not a.skip_save:
                os.makedirs(a.out_dir, exist_ok=True)
                model.enc.save_pretrained(a.out_dir)
                model.tok.save_pretrained(a.out_dir)

    dt = time.time() - t0
    print(f"\n=== 完成 {dt/60:.1f} 分钟 ===")
    print(f"训练前 dev style = {k0.get('style', 0):.4f}")
    print(f"最佳 dev style   = {best['style']:.4f}  @ epoch {best['epoch']}")
    print(f"提升 {(best['style']-k0.get('style',0))*100:+.2f} 个百分点")
    print(f"模型已存 -> {a.out_dir}")

    logpath = os.path.join(ROOT, "bench", f"train_log{a.log_suffix}.json")
    with open(logpath, "w", encoding="utf-8") as f:
        json.dump({"config": vars(a), "baseline": {"overall": r0, **k0},
                   "best": best, "log": log, "minutes": dt / 60}, f,
                  ensure_ascii=False, indent=2)
    print(f"训练日志 -> {logpath}")
    print("\n### TRAIN_DONE")


if __name__ == "__main__":
    main()
