"""
真实 query 对照：baseline / v1 单面 / v2 多面

n 太小不做指标，只看排名。
关键观察：Q3「色彩鲜艳、有秩序又有混乱」在 v2 多面语料下能否命中黑泽明。
"""
import argparse
import json
import os

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
MAXLEN = 128

REAL = [
    ("王家卫的风格", "Wong Kar-wai", "纯名字"),
    ("想要黑泽明那种色彩鲜艳，整体有秩序又有混乱的效果", "Akira Kurosawa", "名字+描述"),
    ("色彩鲜艳，整体有秩序又有混乱的效果", "Akira Kurosawa", "纯描述(无名字)"),
    ("霓虹夜色，慢门，暧昧的感觉", "Wong Kar-wai", "纯描述(无名字)"),
    ("黑白、大雨、群像，那种气势", "Akira Kurosawa", "纯描述(黑白面)"),
]

MODELS = [
    "baseline=intfloat/multilingual-e5-small",
    r"v1单面=F:\llm\models\e5-director-prod",
    r"v2多面=F:\llm\models\e5-director-v2",
]


class Emb:
    def __init__(self, name):
        self.tok = AutoTokenizer.from_pretrained(name)
        self.enc = AutoModel.from_pretrained(name).cuda().eval()
        self.maxlen = MAXLEN

    @torch.no_grad()
    def __call__(self, texts, prefix):
        b = self.tok([prefix + t for t in texts], padding=True, truncation=True,
                     max_length=self.maxlen, return_tensors="pt")
        b = {k: v.cuda() for k, v in b.items()}
        out = self.enc(**b).last_hidden_state
        mask = b["attention_mask"].unsqueeze(-1).float()
        pooled = (out * mask).sum(1) / mask.sum(1).clamp(min=1e-6)
        return F.normalize(pooled.float(), dim=-1)


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run(path, label, corpus):
    m = Emb(path)
    de = torch.cat([m([d["text_semantic"] for d in corpus[i:i+64]], "passage: ")
                    for i in range(0, len(corpus), 64)]).cpu()
    qe = m([q for q, *_ in REAL], "query: ").cpu()
    S = (qe @ de.T).numpy()
    directors = [d["director"] for d in corpus]

    print("=" * 80)
    print(f"模型: {label}   (语料 {len(corpus)} doc)")
    print("=" * 80)
    res = {}
    for qi, (query, truth, kind) in enumerate(REAL):
        best = {}
        for j, d in enumerate(directors):
            if d not in best or S[qi][j] > best[d][0]:
                best[d] = (float(S[qi][j]), j)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
        rank = next(i + 1 for i, (d, _) in enumerate(ranked) if d == truth)
        top3 = [d for d, _ in ranked[:3]]
        res[query] = {"rank": rank, "top3": top3}
        mark = "OK  " if rank <= 3 else "    "
        print(f"  [{mark}] {kind:<14} 第 {rank:>3}/{len(ranked)} 名 | {query[:34]}")
        print(f"         top3: {', '.join(top3)}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl"))
    a = ap.parse_args()
    corpus = load(a.corpus)
    print(f"corpus = {a.corpus}  ({len(corpus)} docs)")
    print(f"queries = {len(REAL)}\n")

    all_res = {}
    for spec in MODELS:
        label, path = spec.split("=", 1)
        if path.startswith("intfloat"):
            pass
        elif not os.path.exists(path):
            print(f"跳过 {label}（模型不存在: {path}）\n")
            continue
        all_res[label] = run(path, label, corpus)
        print()

    print("=" * 80)
    print("排名汇总（越小越好）")
    print("=" * 80)
    labels = list(all_res)
    print(f"{'query':<30} " + " ".join(f"{l:>10}" for l in labels))
    for qi, (query, truth, kind) in enumerate(REAL):
        short = query[:26]
        row = " ".join(f"{all_res[l][query]['rank']:>10}" for l in labels)
        print(f"{short:<30} {row}")

    p = os.path.join(ROOT, "bench", "eval_real_v2.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(all_res, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### REAL_V2_DONE")


if __name__ == "__main__":
    main()
