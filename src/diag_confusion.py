"""
混淆诊断：facet 的失败 query 到底流向了谁

动机
----
liubai 在 v4/v5/v7/v7img 四个版本里失败率精确停在 75%，
语料和模型完全不同却一点不变 -> 不是「数据量」问题，是「结构」问题。
假设：留白 query 跑去了 one_corner（对方文档里字面写着 almost blank pale field）。

本脚本不训练、不改数据，只回答一个问题：
    某个 facet 失败的 query，top-1 落在哪个 director / facet 上？

用 v7img 模型 + corpus_v7_img（去掉视频文档，最干净）。
"""
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_interesting import build_pool, load  # noqa: E402

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v7_img.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-v7img")
OUT = os.path.join(ROOT, "bench", "confusion.json")
MAXLEN = 128


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


def main():
    corpus = load(CORPUS)
    pool = build_pool(corpus, per_facet=12)
    print(f"corpus {len(corpus)} doc / pool {len(pool)} query")

    enc = Enc(MODEL)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([p["query"] for p in pool], "query: ")
    S = de @ qe.T

    directors = [d["director"] for d in corpus]
    facets = [d.get("facet", "base") for d in corpus]

    # 每个 query 的 top-1（按 director 聚合最高分）
    rows = []
    for qi, p in enumerate(pool):
        best = {}
        for j in range(len(corpus)):
            d = directors[j]
            if d not in best or S[j][qi] > best[d][0]:
                best[d] = (float(S[j][qi]), facets[j])
        top_dir, (top_s, top_facet) = max(best.items(), key=lambda kv: kv[1][0])
        rows.append({
            "query": p["query"], "want": p["target_director"],
            "want_facet": p["facet"],
            "got": top_dir, "got_facet": top_facet,
            "ok": top_dir == p["target_director"],
        })

    # 按 facet 统计失败流向
    by = defaultdict(lambda: {"n": 0, "fail": 0, "flow": Counter()})
    for r in rows:
        b = by[r["want_facet"]]
        b["n"] += 1
        if not r["ok"]:
            b["fail"] += 1
            b["flow"][r["got_facet"]] += 1

    print(f"\n{'facet':<16} {'n':>4} {'失败':>6} {'失败率':>7}   主要流向（facet:次数）")
    print("-" * 96)
    for f, b in sorted(by.items(), key=lambda kv: -(kv[1]["fail"] / kv[1]["n"])):
        rate = b["fail"] / b["n"]
        if b["fail"] == 0:
            continue
        flow = ", ".join(f"{k}:{v}" for k, v in b["flow"].most_common(4))
        flag = "  <<<" if rate >= 0.5 else ""
        print(f"{f:<16} {b['n']:>4} {b['fail']:>6} {rate:>6.1%}   {flow}{flag}")

    print("\n=== 重点检查：自相残杀 ===")
    pairs = [("liubai", "one_corner"), ("one_corner", "liubai"),
             ("wu_jiang", "misty_river"), ("misty_river", "wu_jiang"),
             ("liubai", "misty_river"), ("song_academy", None)]
    for a, b2 in pairs:
        if a not in by:
            continue
        x = by[a]
        if b2:
            n = x["flow"].get(b2, 0)
            print(f"  {a:<14} 失败流向 {b2:<14} {n}/{x['fail']} 次")
        else:
            print(f"  {a:<14} 失败 {x['fail']}/{x['n']}，流向 {dict(x['flow'].most_common(5))}")

    # 明细：liubai / wu_jiang 的失败 query 全列出来
    for target in ("liubai", "wu_jiang"):
        print(f"\n=== {target} 的失败明细 ===")
        for r in rows:
            if r["want_facet"] == target and not r["ok"]:
                print(f"  {r['query'][:40]:<42} 期望 {r['want'][:22]:<24} "
                      f"实得 {r['got'][:22]:<24} [{r['got_facet']}]")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({f: {"n": b["n"], "fail": b["fail"],
                       "flow": dict(b["flow"])} for f, b in by.items()},
                  f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### CONFUSION_DONE")


if __name__ == "__main__":
    main()
