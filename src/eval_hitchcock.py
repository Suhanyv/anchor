"""
希区柯克机制化 facet 实验：三种对照

A) v2 模型 @ corpus_v2  -> 没有机制文档
B) v2 模型 @ corpus_v3  -> 有文档，但模型没在这些文档上训练过
C) v3 模型 @ corpus_v3  -> 文档 + 训练都有

A->B 隔离「文档覆盖」；B->C 隔离「用机制 facet 训练」。
"""
import argparse
import json
import os

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C2 = os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl")
C3 = os.path.join(ROOT, "data", "raw", "corpus_v3.jsonl")
Q3 = os.path.join(ROOT, "data", "raw", "queries_v3.jsonl")
TARGET = "Alfred Hitchcock"
MAXLEN = 128


class Emb:
    def __init__(self, name):
        self.tok = AutoTokenizer.from_pretrained(name)
        self.enc = AutoModel.from_pretrained(name).cuda().eval()

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=64):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            b = {k: v.cuda() for k, v in b.items()}
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out)


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run(model_path, label, corpus, hq):
    m = Emb(model_path)
    de = m([d["text_semantic"] for d in corpus], "passage: ").cpu()
    qe = m([q["query"] for q in hq], "query: ").cpu()
    S = (qe @ de.T).numpy()
    directors = [d["director"] for d in corpus]

    ranks = []
    print(f"\n--- {label}  (corpus {len(corpus)} doc) ---")
    for i, q in enumerate(hq):
        best = {}
        for j, d in enumerate(directors):
            if d not in best or S[i][j] > best[d][0]:
                best[d] = (float(S[i][j]), j)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
        rank = next(k + 1 for k, (d, _) in enumerate(ranked) if d == TARGET)
        ranks.append(rank)
        top2 = [d for d, _ in ranked[:2]]
        print(f"  {q['query'][:26]:<28} 第 {rank:>3}/{len(ranked)} 名   top2: {', '.join(top2)}")
    print(f"  平均排名 {sum(ranks)/len(ranks):.1f}   中位 {sorted(ranks)[len(ranks)//2]}   "
          f"前3命中 {sum(1 for r in ranks if r<=3)}/{len(ranks)}")
    return ranks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", default=os.path.join(ROOT, "models", "e5-director-v2"))
    ap.add_argument("--v3", default=os.path.join(ROOT, "models", "e5-director-v3"))
    a = ap.parse_args()

    q3 = load(Q3)
    hq = [q for q in q3 if q["query_id"].startswith("qh_")]
    print(f"手工希区柯克 query: {len(hq)} 条")

    c2, c3 = load(C2), load(C3)
    res = {}
    res["A"] = run(a.v2, "A: v2模型 @ corpus_v2（无机制文档）", c2, hq)
    res["B"] = run(a.v2, "B: v2模型 @ corpus_v3（有文档未训练）", c3, hq)
    if os.path.exists(a.v3):
        res["C"] = run(a.v3, "C: v3模型 @ corpus_v3（文档+训练）", c3, hq)
    else:
        print(f"\n!! v3 模型不存在: {a.v3}")

    print("\n" + "=" * 66)
    print("平均排名（越小越好）")
    print("=" * 66)
    for k, v in res.items():
        print(f"  {k}: {sum(v)/len(v):.2f}")
    if "C" in res:
        print(f"\n  文档覆盖贡献 (A->B): {sum(res['B'])/len(res['B']) - sum(res['A'])/len(res['A']):+.2f}")
        print(f"  机制训练贡献 (B->C): {sum(res['C'])/len(res['C']) - sum(res['B'])/len(res['B']):+.2f}")

    p = os.path.join(ROOT, "bench", "eval_hitchcock.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### HITCHCOCK_EVAL_DONE")


if __name__ == "__main__":
    main()
