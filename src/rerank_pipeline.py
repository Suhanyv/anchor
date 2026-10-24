"""
两阶段：bi-encoder 召回 + cross-encoder 精排

为什么上重排器
--------------
今天把六种解释全试过（候选池 / 模型退化 / 标签过严 / 文档数偏置 / 分类混杂 / 措辞），
只解释了小部分。剩下的是**双编码器的结构性天花板**：
query 和 doc 各自独立压成向量，没有 token 级交互，细粒度区分天生不足。

cross-encoder 把 query 与 doc 拼在一起过一遍编码器，能看到两者的交互。
代价是慢（每个候选一次前向），所以用法是：**先召回 top-K，再精排这 K 条**。

协议（按今天立的纪律）
----------------------
1. 训练数据用训练 query（queries_v4_fixed21c），**评测用另外三套手写基准**，不重叠
2. 召回阶段固定：用同一个 bi-encoder（c27）取 top-K，重排前后候选集完全相同
   -> 增益只能来自精排，不含"候选池变化"的干扰
3. 严格口径（原标签），不偷偷放宽

产物
----
    models/e5-rerank-r1/       cross-encoder 权重
    bench/rerank_report.json   逐题明细
"""
import argparse
import json
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np                                    # noqa: E402
import torch                                          # noqa: E402
import torch.nn as nn                                 # noqa: E402
import torch.nn.functional as F                        # noqa: E402
from transformers import AutoModel, AutoTokenizer      # noqa: E402

from eval_motion import CASES as M_CASES               # noqa: E402
from eval_scene import CASES as S_CASES                # noqa: E402
from eval_cn_genre import CASES as G_CASES             # noqa: E402

MAXLEN = 256
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class CrossEnc(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.tok = AutoTokenizer.from_pretrained(base)
        self.enc = AutoModel.from_pretrained(base)
        self.head = nn.Linear(self.enc.config.hidden_size, 1)

    def forward(self, qs, ps):
        b = self.tok(["query: " + q for q in qs], ["passage: " + p for p in ps],
                     padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt")
        b = {k: v.to(DEV) for k, v in b.items()}
        h = self.enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-6)
        return self.head(pooled.float()).squeeze(-1)


@torch.no_grad()
def encode_bienc(model_dir, texts, prefix, bs=64):
    tok = AutoTokenizer.from_pretrained(model_dir)
    enc = AutoModel.from_pretrained(model_dir).eval().to(DEV)
    out = []
    for i in range(0, len(texts), bs):
        b = tok([prefix + t for t in texts[i:i + bs]], padding=True,
                truncation=True, max_length=128, return_tensors="pt")
        b = {k: v.to(DEV) for k, v in b.items()}
        h = enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
    del enc
    if DEV == "cuda":
        torch.cuda.empty_cache()
    return torch.cat(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/raw/corpus_v21.jsonl")
    ap.add_argument("--queries", default="data/raw/queries_v4_fixed21m.jsonl")
    ap.add_argument("--bienc", default="models/e5-director-c27")
    ap.add_argument("--out", default="models/e5-rerank-r1")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--topk", type=int, default=10, help="召回候选数")
    ap.add_argument("--neg", type=int, default=4, help="每条的难负例数")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    print(f"设备 {DEV}")
    corpus = load(os.path.join(ROOT, a.corpus))
    qs = load(os.path.join(ROOT, a.queries))
    if a.limit:
        qs = qs[: a.limit]
    docs = [d["text_semantic"] for d in corpus]
    doc_ids = [d["doc_id"] for d in corpus]
    id2i = {x: i for i, x in enumerate(doc_ids)}
    dirs = [d["director"] for d in corpus]
    print(f"语料 {len(corpus)} 条 / 训练 query {len(qs)} 条")

    # ---------- 1. 召回（bi-encoder）----------
    t0 = time.time()
    D = encode_bienc(os.path.join(ROOT, a.bienc), docs, "passage: ")
    qtext = [q["query"] for q in qs]
    Q = encode_bienc(os.path.join(ROOT, a.bienc), qtext, "query: ")
    S = (Q @ D.T).cpu().numpy()
    print(f"召回矩阵 {S.shape} 用时 {time.time()-t0:.1f}s")

    # ---------- 2. 造训练对 ----------
    rnd = random.Random(20261025)
    pairs_q, pairs_p, pairs_y = [], [], []
    usable = 0
    for i, q in enumerate(qs):
        pos_idx = [id2i[x] for x in q.get("relevant", []) if x in id2i]
        if not pos_idx:
            continue
        usable += 1
        order = np.argsort(-S[i])
        negs = [int(j) for j in order[: a.topk * 3] if int(j) not in set(pos_idx)][: a.neg]
        pos = int(rnd.choice(pos_idx))
        for j in [pos] + negs:
            pairs_q.append(q["query"])
            pairs_p.append(docs[j])
            pairs_y.append(1.0 if j == pos else 0.0)
    print(f"可用 query {usable} / 训练对 {len(pairs_q)}（正 {sum(1 for y in pairs_y if y>0)}）")

    # ---------- 3. 训练 ----------
    # 关键：新加的输出头是随机初始化的，必须给它单独的大学习率；
    # 编码器是预训练的，用小学习率。混在一起用 2e-5 会让头几乎学不动，
    # 输出接近噪声 -> 重排反而把正确的排序打乱（实测合计 41% -> 20%）。
    model = CrossEnc(os.path.join(ROOT, a.bienc)).to(DEV)
    head_params = list(model.head.parameters())
    enc_params = [p for n, p in model.named_parameters() if not n.startswith("head.")]
    opt = torch.optim.AdamW(
        [{"params": head_params, "lr": 1e-3},
         {"params": enc_params, "lr": 2e-5}],
        weight_decay=0.01)
    lossf = nn.BCEWithLogitsLoss()
    idx = list(range(len(pairs_q)))
    bs = 16
    for ep in range(a.epochs):
        rnd.shuffle(idx)
        tot = 0.0
        nb = 0
        correct = 0
        for s in range(0, len(idx), bs):
            b = idx[s:s + bs]
            if len(b) < 2:
                continue
            logits = model([pairs_q[k] for k in b], [pairs_p[k] for k in b])
            y = torch.tensor([pairs_y[k] for k in b], device=DEV)
            loss = lossf(logits, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss.detach())
            nb += 1
            correct += int(((logits.detach() > 0).float() == y).sum())
        print(f"  epoch {ep+1}/{a.epochs}  loss={tot/max(nb,1):.4f}  训练集逐对准确率={correct/len(idx):.1%}")

    os.makedirs(os.path.join(ROOT, a.out), exist_ok=True)
    model.enc.save_pretrained(os.path.join(ROOT, a.out))
    model.tok.save_pretrained(os.path.join(ROOT, a.out))
    torch.save(model.head.state_dict(), os.path.join(ROOT, a.out, "head.pt"))
    print(f"模型已存 -> {a.out}")

    # ---------- 4. 评测（固定候选集：都是 bi-encoder 的 top-K）----------
    model.eval()
    groups = {"运镜 25 题": [(q, set(ac)) for q, ac, *_ in M_CASES],
              "场景 20 题": [(q, set(ac)) for q, ac, *_ in S_CASES],
              "中国类型片 9 题": [(q, set(ac)) for q, ac, *_ in G_CASES]}

    report = {}
    print(f"\n{'基准':<18} {'重排前@1':>9} {'重排后@1':>9} {'变化':>7}   (候选 top-{a.topk})")
    print("-" * 68)
    tot_b = tot_a = tot_n = 0
    for label, cases in groups.items():
        qe = encode_bienc(os.path.join(ROOT, a.bienc), [c[0] for c in cases], "query: ")
        s_mat = (qe @ D.T).cpu().numpy()
        before = after = 0
        rows = []
        for i, (q, accept) in enumerate(cases):
            order = np.argsort(-s_mat[i])[: a.topk]
            # 重排前：按实体取最高分
            def best_entity(idxs, scores):
                be = {}
                for j, sc in zip(idxs, scores):
                    e = dirs[int(j)]
                    if e not in be or sc > be[e]:
                        be[e] = float(sc)
                return sorted(be.items(), key=lambda kv: -kv[1])[0][0]

            top_before = best_entity(order, [s_mat[i][j] for j in order])

            # 重排：对 top-K 的每条文档打分
            with torch.no_grad():
                rs = model([q] * len(order), [docs[int(j)] for j in order]).cpu().numpy()
            top_after = best_entity(order, rs)

            ok_b = top_before in accept
            ok_a = top_after in accept
            before += ok_b
            after += ok_a
            rows.append({"query": q, "accept": sorted(accept),
                         "before": top_before, "after": top_after,
                         "ok_before": ok_b, "ok_after": ok_a})
        n = len(cases)
        print(f"{label:<18} {before/n:>8.0%} {after/n:>9.0%} {(after-before)/n:>+7.0%}")
        report[label] = {"n": n, "before": before, "after": after, "rows": rows}
        tot_b += before
        tot_a += after
        tot_n += n
    print("-" * 68)
    print(f"{'合计 ' + str(tot_n) + ' 题':<18} {tot_b/tot_n:>8.0%} {tot_a/tot_n:>9.0%} "
          f"{(tot_a-tot_b)/tot_n:>+7.0%}")

    with open(os.path.join(ROOT, "bench", "rerank_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n-> bench/rerank_report.json")
    print("\n### RERANK_DONE")


if __name__ == "__main__":
    main()
