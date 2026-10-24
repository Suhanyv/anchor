"""
让系统自己对「网上流通的提示词」表态：它感不感兴趣

用户的问法：「想让他看看他对现在这种的提示词感不感兴趣」
-> 不该由我判断，该由它的三信号回答。

三信号（同 mine_interesting.py）
    1. margin        导演层 第1 - 第3 分差。小 = 犹豫
    2. novelty       1 - 到最近文档的最大相似度。高 = 没见过
    3. disagreement  base e5 与微调模型 c10 的排名差 + 命中翻转

兴趣分 = 0.40*(1-margin_norm) + 0.30*novelty + 0.30*disagreement

判定口径（先定好再看结果，避免事后解释）
    兴趣分 >= 0.60  高（明显没见过这类，且犹豫）
    0.40 ~ 0.60      中
    < 0.40           低（熟，有把握）

query 来源
----------
中文提示词（04/05）直接摘原句片段，不做改写。
英文提示词（01/02）必须由我转成中文 query —— 这部分是我的改写，非原文，需标注。
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v10.jsonl")
FT = os.path.join(ROOT, "models", "e5-director-c10")
BASE = "intfloat/multilingual-e5-small"
OUT = os.path.join(ROOT, "bench", "interest_on_real_prompts.json")
MAXLEN = 128

# (提示词编号, 说明, [(中文 query, 是否来自原文摘录)])
TESTS = [
    ("P01", "视频·女骑士偷窥", [
        ("女骑士骑马慢慢走向镜头，有人蹲在草丛里偷看她，她突然发现了", False),
        ("从树枝后面看过去，前景有草叶挡住画面，像有人藏着", False),
        ("一个女骑士穿着破旧的钢甲，长发在风里飘", False),
    ]),
    ("P02", "图像(标注)·草原疾驰", [
        ("女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头", False),
        ("广阔荒原上只有一个孤独骑士，低地平线，人很小", False),
        ("钢铁盔甲反光，侧光，深影，冷硬", False),
    ]),
    ("P04", "视频·中文分镜·武侠雪林射箭", [
        ("雪林高处，女子拉满弓弦屏息瞄准，冷白色的雪光", True),
        ("雪粒在劲风中横飞弥漫，远山在雪雾里若隐若现，轻微泛光漫射与柔焦晕散", True),
        ("箭矢离弦后她转身隐入身后纷飞雪幕，身形被完全遮挡", True),
    ]),
    ("P05", "视频·中文七镜·神话史诗", [
        ("巨大的金色佛掌从天而降，压向四颗巨型眼球", True),
        ("黑暗宇宙虚空中四颗彩色巨型眼球，各自散发混沌能量", True),
        ("东方神明雕塑质感，白色丝绸道袍，层叠体积光", True),
    ]),
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


def per_query(enc, corpus, dirs, q):
    """返回 (rank_of_top1 列表, margin, novelty, top1, top3)"""
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([q], "query: ")[0]
    s = de @ qe
    best = {}
    for j, d in enumerate(dirs):
        if d not in best or s[j] > best[d]:
            best[d] = float(s[j])
    rk = sorted(best.items(), key=lambda kv: -kv[1])
    margin = rk[0][1] - rk[min(2, len(rk) - 1)][1]
    novelty = 1.0 - float(np.max(s))
    return rk, margin, novelty


def main():
    corpus = load(CORPUS)
    dirs = [d["director"] for d in corpus]
    print(f"corpus {len(corpus)} doc")

    m_ft = Enc(FT)
    m_base = Enc(BASE)

    rows = []
    for pid, desc, qs in TESTS:
        print(f"\n=== {pid}  {desc} ===")
        for q, is_verbatim in qs:
            rk_ft, margin, novelty = per_query(m_ft, corpus, dirs, q)
            rk_b, _, _ = per_query(m_base, corpus, dirs, q)
            nf = [k for k, _ in rk_ft]
            nb = [k for k, _ in rk_b]
            rf = 1
            rb = nb.index(nf[0]) + 1 if nf[0] in nb else len(nb)
            flip = 1.0 if (nb[0] != nf[0]) else 0.0
            disagree = min(1.0, abs(rf - rb) / 20.0) * 0.5 + flip * 0.5
            rows.append({
                "prompt": pid, "desc": desc, "query": q, "verbatim": is_verbatim,
                "top1": nf[0], "top1_score": rk_ft[0][1],
                "margin": margin, "novelty": novelty, "disagree": disagree,
                "base_top1": nb[0],
            })
            print(f"  {q[:40]:<42} top1={nf[0][:22]:<24} "
                  f"score={rk_ft[0][1]:.3f} margin={margin:.4f} nov={novelty:.3f} "
                  f"dis={disagree:.2f}")

    # 归一化 + 合成
    mg = np.array([r["margin"] for r in rows])
    nv = np.array([r["novelty"] for r in rows])
    mg_n = (mg - mg.min()) / (np.ptp(mg) + 1e-9)
    for i, r in enumerate(rows):
        r["interest"] = round(float(0.40 * (1 - mg_n[i]) + 0.30 * r["novelty"]
                                   + 0.30 * r["disagree"]), 4)

    print("\n" + "=" * 92)
    print(f"{'提示词':<8} {'说明':<26} {'平均兴趣分':>10} {'平均novelty':>12} {'判定':>6}")
    print("=" * 92)
    summary = []
    for pid, desc, _ in TESTS:
        rs = [r for r in rows if r["prompt"] == pid]
        it = float(np.mean([r["interest"] for r in rs]))
        nov = float(np.mean([r["novelty"] for r in rs]))
        verdict = "高" if it >= 0.60 else ("中" if it >= 0.40 else "低")
        summary.append({"prompt": pid, "desc": desc, "interest": round(it, 4),
                        "novelty": round(nov, 4), "verdict": verdict})
        print(f"{pid:<8} {desc:<26} {it:>10.3f} {nov:>12.3f} {verdict:>6}")
    print("=" * 92)

    allmean = float(np.mean([s["interest"] for s in summary]))
    print(f"\n总体平均兴趣分 {allmean:.3f}")
    print("口径：>=0.60 高 / 0.40-0.60 中 / <0.40 低（事先定好，未事后调整）")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### INTEREST_ON_PROMPTS_DONE")


if __name__ == "__main__":
    main()
