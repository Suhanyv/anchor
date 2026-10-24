"""
评测：图像/视频是否真的分开了

两个指标分开看（不能只看总体，这是这个项目反复踩的坑）：
  1. **域准确率**：视频 query 的 top1 是不是视频文档？图片 query 呢？
  2. **导演准确率**：过滤之后，正确导演还找得到吗？（过滤的副作用）

四组对照（都在 corpus_v6 上，同一模型）：
  A  v5 语料，不过滤            <- 分开之前的基线（没有视频文档）
  B  v6 语料，不过滤
  C  v6 语料，**按 query 自动判域并过滤**
"""
import json
import os
import random

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

import domain_router as DR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C5 = os.path.join(ROOT, "data", "raw", "corpus_v5.jsonl")
C6 = os.path.join(ROOT, "data", "raw", "corpus_v6.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-v5")
MAXLEN = 128
N_PER_DOMAIN = 200

T_IMG = ["{kw} 的画面", "{kw} 风格的海报", "想要{kw}的静态画面",
         "{kw} 图片提示词怎么写", "出一张{kw}的图"]
T_VID = ["{kw} 的视频提示词", "{kw} 运镜怎么描述", "想要{kw}那种镜头运动",
         "{kw} 5秒视频怎么prompt", "sora 里 {kw} 怎么运镜"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


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


def build_queries(corpus, n=N_PER_DOMAIN, seed=23):
    """为每个 (director,facet) 组生成图片 query 和视频 query 各若干"""
    rnd = random.Random(seed)
    groups = {}
    for d in corpus:
        groups.setdefault((d["director"], d.get("facet", "base")), d.get("kw_zh", []))
    items = [(k, v) for k, v in groups.items() if v]
    rnd.shuffle(items)

    qs = []
    for (director, facet), kws in items:
        for dom, tpls, want in (("prompt_image", T_IMG, "prompt_image"),
                                ("prompt_video", T_VID, "prompt_video")):
            if sum(1 for q in qs if q["want"] == want) >= n:
                continue
            tpl = rnd.choice(tpls)
            kw = "、".join(rnd.sample(kws, min(rnd.choice([2, 3]), len(kws))))
            qs.append({"query": tpl.format(kw=kw), "want": want,
                       "target_director": director, "facet": facet})
    return qs


def evaluate(enc, corpus, queries, label, use_filter):
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([q["query"] for q in queries], "query: ")
    S = de @ qe.T
    domains = [d["domain"] for d in corpus]
    directors = [d["director"] for d in corpus]

    dom_ok = dir_ok = 0
    routed = {"prompt_image": 0, "prompt_video": 0, "any": 0}
    for qi, q in enumerate(queries):
        if use_filter:
            pred = DR.detect(q["query"])
        else:
            pred = "any"
        routed[pred] += 1

        allowed = [j for j in range(len(corpus))
                   if pred == "any" or domains[j] == pred]
        if not allowed:
            allowed = list(range(len(corpus)))

        best_doc = max(allowed, key=lambda j: S[j][qi])
        if domains[best_doc] == q["want"]:
            dom_ok += 1

        # 导演准确率：在允许集合里按导演聚合取最高
        best = {}
        for j in allowed:
            d = directors[j]
            if d not in best or S[j][qi] > best[d]:
                best[d] = float(S[j][qi])
        if max(best.items(), key=lambda kv: kv[1])[0] == q["target_director"]:
            dir_ok += 1

    n = len(queries)
    print(f"  {label:<34} 域准确率 {dom_ok/n:6.2%}   导演准确率 {dir_ok/n:6.2%}   "
          f"路由分布 {routed}")
    return {"label": label, "domain_acc": dom_ok / n, "director_acc": dir_ok / n,
            "routed": routed, "n": n}


def main():
    c5, c6 = load(C5), load(C6)
    queries = build_queries(c6)
    nv = sum(1 for q in queries if q["want"] == "prompt_video")
    print(f"corpus_v5 {len(c5)} doc / corpus_v6 {len(c6)} doc")
    print(f"query {len(queries)} 条（图 {len(queries)-nv} / 视频 {nv}）\n")

    enc = Enc(MODEL)
    print("=== 对照 ===")
    rows = []
    rows.append(evaluate(enc, c5, queries, "A  v5 语料 + 不过滤", use_filter=False))
    rows.append(evaluate(enc, c6, queries, "B  v6 语料 + 不过滤", use_filter=False))
    rows.append(evaluate(enc, c6, queries, "C  v6 语料 + 自动判域过滤", use_filter=True))

    print("\n" + "=" * 92)
    print(f"{'方案':<34} {'域准确率':>10} {'导演准确率':>12}")
    print("=" * 92)
    for r in rows:
        print(f"{r['label']:<34} {r['domain_acc']:>10.2%} {r['director_acc']:>12.2%}")
    print("=" * 92)
    b, c = rows[1], rows[2]
    print(f"\n过滤带来的变化：域准确率 {b['domain_acc']:+.2%} -> {c['domain_acc']:.2%} "
          f"({c['domain_acc']-b['domain_acc']:+.2%})   导演准确率 "
          f"{b['director_acc']:.2%} -> {c['director_acc']:.2%} "
          f"({c['director_acc']-b['director_acc']:+.2%})")

    p = os.path.join(ROOT, "bench", "eval_domain.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {p}")
    print("\n### EVAL_DOMAIN_DONE")


if __name__ == "__main__":
    main()
