"""
重排器增益的严格验证：按句式留出，大样本

为什么还要验一次
----------------
α 扫描在手写基准（54 题）上得到 +5pp，但 54 题上一个标准误约 6.7pp，
**+5pp 等于多对 3 题，统计上站不住。** 不能凭它上线。

这个脚本换一套更好的验证：
1. 拿 777 条训练 query，按 **template_id** 留出 20%（整段句式不在训练里）
2. 重排器只在剩下 80% 上训练
3. 在 ~150 条留出 query 上比：纯召回 / 纯重排 / 各 α 混合

样本大 3 倍，且测的是"没见过的句式"，比手写基准更能说明泛化。
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np                                    # noqa: E402
import torch                                          # noqa: E402
import torch.nn as nn                                 # noqa: E402
import torch.nn.functional as F                        # noqa: E402
from transformers import AutoModel, AutoTokenizer      # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"
MAXLEN = 256


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


@torch.no_grad()
def encode(model_dir, texts, prefix, bs=64):
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
    torch.cuda.empty_cache()
    return torch.cat(out)


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
        return self.head(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float()).squeeze(-1)


def main():
    ap_epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    corpus = load(os.path.join(ROOT, "data/raw/corpus_v21.jsonl"))
    qs = load(os.path.join(ROOT, "data/raw/queries_v4_fixed21m.jsonl"))
    docs = [d["text_semantic"] for d in corpus]
    doc_ids = [d["doc_id"] for d in corpus]
    dirs = [d["director"] for d in corpus]
    id2i = {x: i for i, x in enumerate(doc_ids)}

    # 按 template_id 切分
    tids = sorted({q.get("template_id", q["query_id"]) for q in qs})
    rnd = random.Random(20261025)
    rnd.shuffle(tids)
    hold = set(tids[: max(1, len(tids) // 5)])
    tr = [q for q in qs if q.get("template_id", q["query_id"]) not in hold]
    te = [q for q in qs if q.get("template_id", q["query_id"]) in hold]
    print(f"句式 {len(tids)} 个：训练 {len(tids)-len(hold)} / 留出 {len(hold)}")
    print(f"query：训练 {len(tr)} / 留出 {len(te)}")

    bienc = os.path.join(ROOT, "models/e5-director-c27")
    D = encode(bienc, docs, "passage: ")

    # 训练对（只用训练集）
    St = (encode(bienc, [q["query"] for q in tr], "query: ") @ D.T).cpu().numpy()
    rnd2 = random.Random(7)
    pq, pp, py = [], [], []
    for i, q in enumerate(tr):
        pos = [id2i[x] for x in q.get("relevant", []) if x in id2i]
        if not pos:
            continue
        order = np.argsort(-St[i])
        negs = [int(j) for j in order[:30] if int(j) not in set(pos)][:6]
        p = int(rnd2.choice(pos))
        for j in [p] + negs:
            pq.append(q["query"]); pp.append(docs[j]); py.append(1.0 if j == p else 0.0)
    print(f"训练对 {len(pq)}（正 {int(sum(py))}）")

    model = CrossEnc(bienc).to(DEV)
    head = list(model.head.parameters())
    encp = [p for n, p in model.named_parameters() if not n.startswith("head.")]
    opt = torch.optim.AdamW([{"params": head, "lr": 1e-3},
                             {"params": encp, "lr": 2e-5}], weight_decay=0.01)
    lossf = nn.BCEWithLogitsLoss()
    idx = list(range(len(pq)))
    for ep in range(ap_epochs):
        rnd2.shuffle(idx)
        tot, nb, cor = 0.0, 0, 0
        for s in range(0, len(idx), 16):
            b = idx[s:s + 16]
            if len(b) < 2:
                continue
            lg = model([pq[k] for k in b], [pp[k] for k in b])
            y = torch.tensor([py[k] for k in b], device=DEV)
            loss = lossf(lg, y)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss.detach()); nb += 1
            cor += int(((lg.detach() > 0).float() == y).sum())
        print(f"  epoch {ep+1}/{ap_epochs} loss={tot/max(nb,1):.4f} 逐对准确率={cor/len(idx):.1%}")
    model.eval()

    # 留出集评测
    Se = (encode(bienc, [q["query"] for q in te], "query: ") @ D.T).cpu().numpy()
    ALPHAS = [1.0, 0.85, 0.75, 0.65, 0.55, 0.45, 0.3, 0.0]
    acc = {a: 0 for a in ALPHAS}
    n = 0
    for i, q in enumerate(te):
        pos = {id2i[x] for x in q.get("relevant", []) if x in id2i}
        if not pos:
            continue
        n += 1
        order = list(np.argsort(-Se[i])[:10])
        bi = np.array([Se[i][j] for j in order], dtype=np.float64)
        with torch.no_grad():
            rr = model([q["query"]] * len(order), [docs[int(j)] for j in order]).cpu().numpy()

        def norm(v):
            lo, hi = v.min(), v.max()
            return (v - lo) / (hi - lo + 1e-9)

        bn, rn = norm(bi), norm(rr)
        for a in ALPHAS:
            sc = a * bn + (1 - a) * rn
            k = int(np.argmax(sc))
            if order[k] in pos:
                acc[a] += 1
    print(f"\n留出集 {n} 条（整段句式未参与训练）")
    print(f"{'α':>6} {'@1':>7}  说明")
    for a in ALPHAS:
        note = "纯召回（现行）" if a == 1.0 else ("纯重排" if a == 0.0 else "")
        print(f"{a:>6.2f} {acc[a]/n:>6.0%}  {note}")
    base = acc[1.0]
    best = max(ALPHAS, key=lambda a: acc[a])
    print(f"\n最佳 α={best:.2f}: {acc[best]/n:.1%}（基线 {base/n:.1%}，"
          f"{(acc[best]-base)/n:+.1%}）")
    se = (0.5 * 0.5 / n) ** 0.5
    print(f"样本 {n} 条，一个标准误约 {se:.1%}；"
          f"增益大于 {2*se:.1%} 才算站得住。")
    print("\n### RERANK_VALIDATE_DONE")


if __name__ == "__main__":
    main()
