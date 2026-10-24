"""
「让他拥有自己的兴趣」—— 主动学习三信号挖掘器

设计修正
--------
原计划用 bge-m3 当教师，但 HuggingFace 至今不可达，无法下载。
替代方案：用**模型分歧**代替教师置信。
    手里有两个模型：base e5-small（未微调） 和 v4-noleak（微调后）。
    它们吵架的地方 = 最不可靠的地方。不需要任何新下载。

三信号
------
1. margin        模型在犹豫：导演层面 第1名 - 第3名 的分差。小 = 犹豫。
2. novelty       语料没覆盖：query 到最近文档的最大相似度。低 = 没覆盖。
3. disagreement  两个模型分歧：base 与 v4 的排名差（含命中/未命中的翻转）。

兴趣分
------
    interesting = 0.40*(1-margin_norm) + 0.30*novelty + 0.30*disagreement
    再乘一个失败加权：hit@1 失败 *1.5（失败比犹豫更值得看）

铁律
----
数据可以自选，评测绝对不能自选。
本脚本只用来**指导补什么语料**，不用来判断模型好坏。

输出
----
bench/interesting_report.json    汇总 + 排名
data/raw/interesting_queries.jsonl  值得人工看的 query
"""
import json
import os
import random
from collections import Counter, defaultdict

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
BASE = "intfloat/multilingual-e5-small"
FT = os.path.join(ROOT, "models", "e5-director-v4-noleak")
OUT_JSON = os.path.join(ROOT, "bench", "interesting_report.json")
OUT_JSONL = os.path.join(ROOT, "data", "raw", "interesting_queries.jsonl")
MAXLEN = 128

# 全新句式池（刻意与训练用的 28 套模板不重叠）—— 用来暴露「换说法就挂」的问题
NEW_TPLS = [
    "{kw}，要那种感觉",
    "想搜{kw}相关的东西",
    "{kw} 这种怎么描述",
    "给我点{kw}的参考",
    "{kw} 关键词有哪些",
    "有没有{kw}的例子",
    "怎么用英文说{kw}",
    "{kw}，越具体越好",
    "{kw} 那种调子",
    "帮我找{kw}的素材方向",
    "{kw} 相关的风格叫什么",
    "如果只要{kw}，怎么prompt",
    "{kw} 这个方向的提示词",
    "想要{kw}，不要别的",
    "{kw} 类似的东西",
    "有个画面是{kw}，怎么搜",
    "{kw} 的英文说法",
    "{kw}，用什么词能出这个效果",
    "描述{kw}的提示词",
    "{kw} 这种感觉的表达",
    "{kw} 对应的英文标签",
    "我要{kw}，给我关键词",
    "{kw} 那类风格",
    "{kw} 的写法",
    "{kw}，简洁一点的说法",
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class Enc:
    def __init__(self, path, dev="cuda"):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.enc = AutoModel.from_pretrained(path).to(dev).eval()
        for p in self.enc.parameters():
            p.requires_grad_(False)
        self.dev = dev

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=64):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            b = {k: v.to(self.dev) for k, v in b.items()}
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).cpu().numpy()


def build_pool(corpus, per_facet=12, seed=7):
    """为每个 (director, facet) 生成若干条「没见过的说法」的 query。

    注意两点（都是踩过坑修的）：
      1. 只用 domain == prompt_image 的文档取关键词。
         视频文档的 kw 曾经被追加过 运镜/视频 之类，混进来会生成
         「视频、镜头运动 这种怎么描述」这种无意义 query，基准直接报废。
      2. 取关键词时取**第一条**而不是最后一条，避免被后加的文档覆盖。
    """
    rnd = random.Random(seed)
    DOMAIN_WORDS = {"运镜", "镜头运动", "时长", "视频", "图片", "静态"}
    groups = defaultdict(lambda: {"kws": None, "ids": [], "zh": ""})
    for d in corpus:
        if d.get("domain") not in (None, "prompt_image"):
            continue
        k = (d["director"], d.get("facet", "base"))
        if groups[k]["kws"] is None:            # 只取第一条的 kw
            kws = [w for w in (d.get("kw_zh") or []) if w not in DOMAIN_WORDS]
            groups[k]["kws"] = kws
            groups[k]["zh"] = d.get("director_zh", "")
        groups[k]["ids"].append(d["doc_id"])

    pool = []
    for (director, facet), g in groups.items():
        kws = g["kws"]
        if not kws:
            continue
        seen = set()
        for i in range(per_facet):
            for _ in range(20):
                tpl = rnd.choice(NEW_TPLS)
                n = rnd.choice([2, 2, 3])
                kw = "、".join(rnd.sample(kws, min(n, len(kws))))
                text = tpl.format(kw=kw, zh=g["zh"])
                if text not in seen:
                    seen.add(text)
                    break
            else:
                continue
            pool.append({
                "query": text,
                "target_director": director,
                "facet": facet,
                "relevant": g["ids"],
                "template_id": "newpool:" + tpl,
            })
    return pool


def rank_directors(sims, doc_ids, directors):
    """按导演聚合取最高分，返回 (排序后的[(director,score)], 每个导演最高分字典)"""
    best = {}
    for i, s in enumerate(sims):
        d = directors[i]
        if d not in best or s > best[d]:
            best[d] = float(s)
    rk = sorted(best.items(), key=lambda kv: -kv[1])
    return rk, best


def analyze(model, corpus, pool, label):
    doc_ids = [d["doc_id"] for d in corpus]
    directors = [d["director"] for d in corpus]
    de = model([d["text_semantic"] for d in corpus], "passage: ")
    qe = model([p["query"] for p in pool], "query: ")
    S = de @ qe.T                                   # (docs, queries)

    rows = []
    for qi, p in enumerate(pool):
        sims = S[:, qi]
        rk, best = rank_directors(sims, doc_ids, directors)
        tgt = p["target_director"]
        names = [d for d, _ in rk]
        rank = names.index(tgt) + 1 if tgt in names else len(names) + 1
        margin = rk[0][1] - rk[min(2, len(rk) - 1)][1]
        novelty = 1.0 - float(sims.max())
        rows.append({
            "rank": rank,
            "hit1": rank == 1,
            "margin": margin,
            "novelty": novelty,
            "top1": rk[0][0],
            "top1_score": rk[0][1],
            "target_score": best.get(tgt, 0.0),
        })
    print(f"  [{label}] 命中@1 {sum(r['hit1'] for r in rows)}/{len(rows)}  "
          f"平均 margin {np.mean([r['margin'] for r in rows]):.4f}  "
          f"平均 novelty {np.mean([r['novelty'] for r in rows]):.4f}")
    return rows


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--ft", default=FT)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    corpus = load(a.corpus)
    print(f"corpus: {len(corpus)} doc  ({os.path.basename(a.corpus)})")
    print(f"ft model: {a.ft}")

    pool = build_pool(corpus, per_facet=12)
    print(f"候选 query: {len(pool)} 条（全部来自 25 套**训练时没见过**的新句式）")

    print("\n=== 编码 + 打分 ===")
    m_base = Enc(BASE)
    r_base = analyze(m_base, corpus, pool, "base e5")
    del m_base
    torch.cuda.empty_cache()

    m_ft = Enc(a.ft)
    r_ft = analyze(m_ft, corpus, pool, f"ft({os.path.basename(a.ft)})")

    # ---- 三信号合成 ----
    margins = np.array([r["margin"] for r in r_ft])
    novels = np.array([r["novelty"] for r in r_ft])
    m_norm = (margins - margins.min()) / (np.ptp(margins) + 1e-9)
    n_norm = (novels - novels.min()) / (np.ptp(novels) + 1e-9)

    out = []
    for i, p in enumerate(pool):
        rb, rf = r_base[i], r_ft[i]
        # disagreement: 排名差的归一化 + 命中翻转加成
        nd = max(len(set(d for d in [p["target_director"]])), 1)
        rank_gap = abs(rb["rank"] - rf["rank"])
        flip = 1.0 if (rb["hit1"] != rf["hit1"]) else 0.0
        disagree = min(1.0, rank_gap / 20.0) * 0.5 + flip * 0.5

        uncertainty = 1.0 - m_norm[i]
        novelty = n_norm[i]
        score = 0.40 * uncertainty + 0.30 * novelty + 0.30 * disagree
        if not rf["hit1"]:
            score *= 1.5

        out.append({
            "query": p["query"],
            "target_director": p["target_director"],
            "facet": p["facet"],
            "interesting": round(float(score), 4),
            "ft_rank": rf["rank"],
            "ft_hit1": rf["hit1"],
            "ft_top1": rf["top1"],
            "margin": round(rf["margin"], 4),
            "novelty": round(rf["novelty"], 4),
            "base_rank": rb["rank"],
            "disagree": round(disagree, 4),
        })

    out.sort(key=lambda x: -x["interesting"])

    print("\n" + "=" * 104)
    print("最「感兴趣」的 25 条（模型犹豫 / 语料没覆盖 / 两模型吵架）")
    print("=" * 104)
    print(f"{'#':>3} {'兴趣分':>7} {'ft排名':>7} {'margin':>7} {'novelty':>8} {'base排名':>8}  query")
    for i, r in enumerate(out[:25], 1):
        print(f"{i:>3} {r['interesting']:>7.3f} {r['ft_rank']:>7} {r['margin']:>7.4f} "
              f"{r['novelty']:>8.4f} {r['base_rank']:>8}  {r['query'][:34]}")

    # ---- 汇总：哪些 facet 最需要补 ----
    print("\n" + "=" * 104)
    print("按 facet 汇总：失败率最高的面 = 最该补语料的地方")
    print("=" * 104)
    by_facet = defaultdict(list)
    for r in out:
        by_facet[r["facet"]].append(r)
    stats = []
    for f, rs in by_facet.items():
        fail = sum(1 for x in rs if not x["ft_hit1"]) / len(rs)
        stats.append((f, len(rs), fail, float(np.mean([x["interesting"] for x in rs]))))
    stats.sort(key=lambda x: -x[2])
    print(f"{'facet':<18} {'n':>4} {'失败率':>8} {'平均兴趣分':>10}")
    for f, n, fail, sc in stats[:20]:
        print(f"{f:<18} {n:>4} {fail:>7.1%} {sc:>10.3f}")

    hit = sum(1 for r in out if r["ft_hit1"])
    print(f"\n总命中@1: {hit}/{len(out)} = {hit/len(out):.1%}")
    print(f"新句式池（训练未见过）能命中说明泛化 OK；失败率高说明措辞覆盖不足。")

    out_json = os.path.join(ROOT, "bench", f"interesting_report{a.tag}.json")
    out_jsonl = os.path.join(ROOT, "data", "raw", f"interesting_queries{a.tag}.jsonl")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "n_queries": len(out),
            "hit1": hit / len(out),
            "by_facet": [{"facet": f, "n": n, "fail_rate": fr, "mean_interesting": sc}
                         for f, n, fr, sc in stats],
            "top_interesting": out[:60],
        }, f, ensure_ascii=False, indent=2)
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in out[:120]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nreport -> {out_json}")
    print(f"top120 -> {out_jsonl}")
    print("\n### MINE_DONE")


if __name__ == "__main__":
    main()
