"""
query 去主体偏置实验：把「画什么」从向量里减掉，只留「怎么拍」

动机（来自 diag_q1.py 的拆词消融）
----------------------------------
query = 「女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头」
    只有「远景全身，跟随镜头」        -> Villeneuve 第 1，0.4638  ✅
    只有「女骑士骑着披甲战马」        -> Villeneuve 第 44，0.0997  ❌
    完整 query                        -> Villeneuve 第 8，0.2493

即：主体名词在语料里没有对应概念（纯噪声），却把风格信号稀释了。
我们已有题材通道能识别主体，于是可以：
    v_style = normalize(v_query - alpha * v_subject_phrase)

扫 alpha，看场景基准（20 题，导演级 top1/top3/top5）怎么变。

注意
----
题材命中用与生产一致的门槛：subject_score >= style_score * 0.95 且 >= 0.36。
未命中则不做减法（alpha 无效），保持原样。
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_scene as ES  # noqa: E402

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")
SUBJ = os.path.join(ROOT, "data", "raw", "subjects_v2.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-c14")
OUT = os.path.join(ROOT, "bench", "eval_debias.json")
SUBJECT_RATIO = 0.95
SUBJECT_FLOOR = 0.36
# 只对「具体的物/人/室内器物件」去偏；
# 「地貌/街道/场地」与"辽阔/空旷/自然光"等风格词共享语义，减了会伤自己。
DEBIAS_TYPES = {"character_object"}


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
                         truncation=True, max_length=128, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def rank(hits, dirs_all, corpus):
    """按导演聚合取最高分"""
    best, bdoc = {}, {}
    for j, d in enumerate(dirs_all):
        if d not in best or hits[j] > best[d]:
            best[d] = float(hits[j])
            bdoc[d] = j
    rk = sorted(best.items(), key=lambda kv: -kv[1])
    return rk, bdoc


def main():
    corpus = load(CORPUS)
    subjects = load(SUBJ)
    dirs = [d["director"] for d in corpus]
    enc = Enc(MODEL)

    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    se = enc([s["text_semantic"] for s in subjects], "passage: ")
    queries = [c[0] for c in ES.CASES]
    accepts = [c[1] for c in ES.CASES]
    qe = enc(queries, "query: ")

    print(f"corpus {len(corpus)} / subjects {len(subjects)} / queries {len(queries)}\n")

    for alpha in (0.0, 0.5, 1.0, 1.5):
        hit1 = hit3 = hit5 = 0
        debiased_n = 0
        per_q = []
        for qi, qv in enumerate(qe):
            # 直接风格分
            s_raw = de @ qv
            rk_raw, _ = rank(s_raw, dirs, corpus)
            # 题材命中判定
            ssub = se @ qv
            k = int(ssub.argmax())
            subj_score = float(ssub[k])
            style_top = rk_raw[0][1]
            hit = (subj_score >= style_top * SUBJECT_RATIO
                   and subj_score >= SUBJECT_FLOOR)
            if alpha > 0 and hit and subjects[k].get("type") in DEBIAS_TYPES:
                v = qv - alpha * se[k]
                n = np.linalg.norm(v)
                v = v / n if n > 1e-9 else qv
                debiased_n += 1
            else:
                v = qv
            s = de @ v
            rk, _ = rank(s, dirs, corpus)
            names = [d for d, _ in rk]
            ranks = [names.index(a) + 1 for a in accepts[qi] if a in names]
            r = min(ranks) if ranks else 999
            if r == 1:
                hit1 += 1
            if r <= 3:
                hit3 += 1
            if r <= 5:
                hit5 += 1
            per_q.append(r)
        n = len(qe)
        tag = "原样（不减）" if alpha == 0 else f"alpha={alpha}（去偏 {debiased_n}/{n} 条）"
        print(f"{tag:<34} top1 {hit1}/{n}={hit1/n:.0%}  "
              f"top3 {hit3/n:.0%}  top5 {hit5/n:.0%}   逐题排名 {per_q}")

    print("\n### DEBIAS_DONE")


if __name__ == "__main__":
    main()
