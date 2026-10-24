"""
重排器能不能"只用一点"？—— 混合分数扫描

背景
----
重排器（e5-rerank-r2）训练集逐对准确率 90%，但基准上把 41% 打到 30%。
诊断：训练 query 是模板生成，学到的线索是关键词重叠；基准是自然句子，线索失效。

在放弃之前，试最后一件事：**不要重排后的绝对分，只要它对召回分的一点点扰动**。
    final = α · norm(召回分) + (1-α) · norm(重排分)
α=1 等同纯召回（现行），α=0 等同纯重排（已知很差）。
如果某个中间 α 能带来正增益，就用它；否则结论是这套数据训不动重排器。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np                                    # noqa: E402
import torch                                          # noqa: E402
import torch.nn.functional as F                        # noqa: E402
from transformers import AutoModel, AutoTokenizer      # noqa: E402

from eval_motion import CASES as M_CASES               # noqa: E402
from eval_scene import CASES as S_CASES                # noqa: E402
from eval_cn_genre import CASES as G_CASES             # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"


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


def main():
    corpus_path = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
    bienc = os.path.join(ROOT, "models/e5-director-c27")
    rdir = os.path.join(ROOT, "models/e5-rerank-r2")
    if not os.path.isdir(rdir):
        raise SystemExit(f"重排器不存在：{rdir}")

    corpus = load(corpus_path)
    docs = [d["text_semantic"] for d in corpus]
    dirs = [d["director"] for d in corpus]

    tok = AutoTokenizer.from_pretrained(rdir)
    enc = AutoModel.from_pretrained(rdir).eval().to(DEV)
    head = torch.nn.Linear(enc.config.hidden_size, 1).to(DEV)
    head.load_state_dict(torch.load(os.path.join(rdir, "head.pt"), map_location=DEV))
    head.eval()

    @torch.no_grad()
    def rerank(q, idxs):
        b = tok(["query: " + q] * len(idxs), ["passage: " + docs[int(j)] for j in idxs],
                padding=True, truncation=True, max_length=256, return_tensors="pt")
        b = {k: v.to(DEV) for k, v in b.items()}
        h = enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        pooled = (h * m).sum(1) / m.sum(1).clamp(min=1e-6)
        return head(pooled.float()).squeeze(-1).cpu().numpy()

    D = encode(bienc, docs, "passage: ")
    groups = {"运镜 25 题": [(q, set(a)) for q, a, *_ in M_CASES],
              "场景 20 题": [(q, set(a)) for q, a, *_ in S_CASES],
              "中国类型片 9 题": [(q, set(a)) for q, a, *_ in G_CASES]}

    ALPHAS = [1.0, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.0]
    print(f"{'基准':<20}" + "".join(f"α={al:<5}" for al in ALPHAS))
    print("-" * 68)
    grand = {al: [0, 0] for al in ALPHAS}
    for label, cases in groups.items():
        qe = encode(bienc, [c[0] for c in cases], "query: ")
        sm = (qe @ D.T).cpu().numpy()
        acc = {al: 0 for al in ALPHAS}
        for i, (q, accept) in enumerate(cases):
            order = list(np.argsort(-sm[i])[:10])
            bi = np.array([sm[i][j] for j in order], dtype=np.float64)
            rr = rerank(q, order)

            def norm(v):
                lo, hi = v.min(), v.max()
                return (v - lo) / (hi - lo + 1e-9)

            bi_n, rr_n = norm(bi), norm(rr)
            for al in ALPHAS:
                sc = al * bi_n + (1 - al) * rr_n
                be = {}
                for k, s in enumerate(sc):
                    e = dirs[order[k]]
                    if e not in be or s > be[e]:
                        be[e] = float(s)
                top = max(be.items(), key=lambda kv: kv[1])[0]
                if top in accept:
                    acc[al] += 1
                    grand[al][0] += 1
        n = len(cases)
        for al in ALPHAS:
            grand[al][1] += n
        print(f"{label:<20}" + "".join(f"{acc[al]/n:>6.0%}" for al in ALPHAS))
    print("-" * 68)
    print(f"{'合计 54 题':<20}" + "".join(f"{grand[al][0]/grand[al][1]:>6.0%}" for al in ALPHAS))
    print("\nα=1.00 等同纯召回（现行）；α=0.00 等同纯重排。")
    print("\n### BLEND_DONE")


if __name__ == "__main__":
    main()
