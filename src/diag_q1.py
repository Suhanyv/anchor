"""
诊断：#1「女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头」
为什么 Villeneuve 只排第 8。

方法
----
1. 打印完整排名，看 top5 是谁、各自的文档是什么
2. Villeneuve 自己最贴那条 doc 是哪个、差多少分
3. **拆词消融**：把 query 切成不同组合，看哪一个片段在拉动排名
   如果去掉「女骑士 / 披甲战马」排名就上来 -> 主体词在拉走
   如果去掉「草原 / 疾驰」排名下降  -> 场景词在支撑
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-c14")
TARGET = "Denis Villeneuve"
MAXLEN = 128

FULL = "女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头"

VARIANTS = [
    ("完整", FULL),
    ("去掉主体（女骑士/披甲战马）", "在无边草原上全速疾驰，远景全身，跟随镜头"),
    ("只有主体", "女骑士骑着披甲战马"),
    ("只有景别与运镜", "远景全身，跟随镜头"),
    ("只有场景与速度", "无边草原上全速疾驰"),
    ("主体+景别（无草原）", "女骑士骑着披甲战马，远景全身，跟随镜头"),
    ("草原+景别（无主体）", "无边草原上全速疾驰，远景全身，跟随镜头"),
    ("骑手版（中性主体词）", "一个骑手在无边草原上全速疾驰，远景全身，跟随镜头"),
    ("英文对应（对照）", "a lone rider crossing a vast open plain, low horizon, tracking shot"),
]


class Enc:
    def __init__(self, path):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.enc = AutoModel.from_pretrained(path).eval()
        for p in self.enc.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    dirs = [d["director"] for d in corpus]
    print(f"corpus {len(corpus)} doc / model {os.path.basename(MODEL)}")

    enc = Enc(MODEL)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")

    # ---------- 1. 完整排名 ----------
    qe = enc([FULL], "query: ")[0]
    s = de @ qe
    best = {}
    best_doc = {}
    for j, d in enumerate(dirs):
        if d not in best or s[j] > best[d]:
            best[d] = float(s[j])
            best_doc[d] = j
    rk = sorted(best.items(), key=lambda kv: -kv[1])
    names = [k for k, _ in rk]
    print(f"\n=== 完整 query 的 top5 ===")
    print(f"query: {FULL}")
    for i, (d, sc) in enumerate(rk[:5], 1):
        doc = corpus[best_doc[d]]["text_semantic"]
        mark = "  <<< 正确答案" if d == TARGET else ""
        print(f"  {i}. {d[:26]:<28} {sc:.4f}  [{corpus[best_doc[d]].get('facet')}]{mark}")
        print(f"       {doc[:92]}")
    rank = names.index(TARGET) + 1 if TARGET in names else 999
    print(f"\n  Villeneuve 排名 {rank}  分数 {best.get(TARGET, 0):.4f}")
    vdoc = corpus[best_doc[TARGET]]["text_semantic"]
    print(f"  他最贴的 doc: {vdoc[:100]}")

    # ---------- 2. 拆词消融 ----------
    print(f"\n=== 拆词消融（Villeneuve 的排名 / 分数，以及 top1 是谁）===")
    qs = [v[1] for v in VARIANTS]
    qe2 = enc(qs, "query: ")
    print(f"{'变体':<26} {'V排名':>6} {'V分数':>7}  top1")
    print("-" * 84)
    for (tag, q), qv in zip(VARIANTS, qe2):
        ss = de @ qv
        bb = {}
        for j, d in enumerate(dirs):
            if d not in bb or ss[j] > bb[d]:
                bb[d] = float(ss[j])
        rr = sorted(bb.items(), key=lambda kv: -kv[1])
        nn = [k for k, _ in rr]
        r = nn.index(TARGET) + 1 if TARGET in nn else 999
        print(f"{tag:<26} {r:>6} {bb.get(TARGET, 0):>7.4f}  {rr[0][0][:30]}")

    print("\n### DIAG_Q1_DONE")


if __name__ == "__main__":
    main()
