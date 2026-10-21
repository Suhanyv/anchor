"""
东方影像验证：v3（无东方语料）vs v4（有）

注意：v3 语料里不存在这些条目，所以 v3 的排名是"缺席"，不是"排得靠后"。
      这个区别很重要 —— 缺席意味着系统连候选都给不出来。
"""
import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
C3 = ROOT + r"\data\raw\corpus_v3.jsonl"
C4 = ROOT + r"\data\raw\corpus_v4.jsonl"
Q4 = ROOT + r"\data\raw\queries_v4.jsonl"
M3 = ROOT + r"\models\e5-director-v3"
M4 = ROOT + r"\models\e5-director-v4"
MAXLEN = 128


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class Enc:
    def __init__(self, path):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.enc = AutoModel.from_pretrained(path).eval()

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out)


def run(model_path, corpus, eq, label):
    m = Enc(model_path)
    de = m([d["text_semantic"] for d in corpus], "passage: ")
    qe = m([q["query"] for q in eq], "query: ")
    dirs = [d["director"] for d in corpus]
    present = set(dirs)
    S = (de @ qe.T).numpy()

    print("=" * 100)
    print(f"{label}   (语料 {len(corpus)} doc)")
    print("=" * 100)
    rows = []
    hit3 = 0
    for i, q in enumerate(eq):
        best = {}
        for j, d in enumerate(dirs):
            if d not in best or S[j][i] > best[d]:
                best[d] = float(S[j][i])
        rk = sorted(best.items(), key=lambda kv: -kv[1])
        tgt = q["target_director"]
        if tgt in present:
            rank = next(k + 1 for k, (d, _) in enumerate(rk) if d == tgt)
            if rank <= 3:
                hit3 += 1
            rs = f"第 {rank:>3} 名"
        else:
            rank = None
            rs = "缺席"
        top2 = ", ".join(d[:22] for d, _ in rk[:2])
        rows.append((q["query"], tgt, rank, rs, top2))
        print(f"  {q['query'][:26]:<28} {rs:<10} 期望 {tgt[:24]:<26} top2: {top2}")
    print(f"\n  前3命中 {hit3}/{len(eq)}")
    return rows, hit3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4", default=M4, help="v4 模型路径")
    ap.add_argument("--skip-v3", action="store_true")
    a = ap.parse_args()

    c3, c4 = load(C3), load(C4)
    qs = load(Q4)
    eq = [q for q in qs if q["query_id"].startswith("qe_")]
    print(f"东方 query: {len(eq)}\n")

    r3, h3 = ([], 0)
    if not a.skip_v3:
        r3, h3 = run(M3, c3, eq, "v3 模型 @ corpus_v3（无东方语料）")
        print()
    r4, h4 = run(a.v4, c4, eq, f"v4 模型 @ corpus_v4  [{a.v4.split(chr(92))[-1]}]")

    print("\n" + "=" * 100)
    print("对照")
    print("=" * 100)
    if not r3:
        print(f"  （跳过 v3 对照）v4 前3命中 {h4}/{len(eq)}")
        improved = 0
    else:
        print(f"{'query':<30} {'v3':>12} {'v4':>12}")
        improved = same = 0
        for (q, tgt, ran3, s3, _), (_, _, ran4, s4, _) in zip(r3, r4):
            print(f"{q[:28]:<30} {s3:>12} {s4:>12}")
            if ran3 is None and ran4 is not None and ran4 <= 3:
                improved += 1
            elif ran3 is not None and ran4 is not None and ran4 < ran3:
                improved += 1
            else:
                same += 1
        print(f"\n  前3命中: {h3}/{len(eq)} -> {h4}/{len(eq)}")
        print(f"  从缺席/靠后 -> 进前3: {improved} 条")

    out = {"queries": len(eq), "v3_hit3": h3, "v4_hit3": h4,
           "detail": [{"query": q, "target": t,
                       "v3_rank": a, "v4_rank": b,
                       "v3_top2": c, "v4_top2": d}
                      for (q, t, a, _, c), (_, _, b, _, d) in zip(r3, r4)]}
    p = ROOT + r"\bench\eval_eastern.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### EASTERN_EVAL_DONE")


if __name__ == "__main__":
    main()
