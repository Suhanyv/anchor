"""
用真实用户 query 检验模型 —— n 太小，不做指标，只做定性分析。

看三件事：
  1. 正确导演排第几（base vs 微调后）
  2. Top-K 里召回的是谁（是不是风格近亲）
  3. 用户用词 vs 语料签名是否对得上（暴露语料偏差）
"""
import json
import os
import sys

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
BASE = "intfloat/multilingual-e5-small"
PROD = os.path.join(ROOT, "models", "e5-director-prod")
MAXLEN = 128

# (query, 期望导演英文名, 类型)
REAL = [
    ("王家卫的风格", "Wong Kar-wai", "纯名字"),
    ("想要黑泽明那种色彩鲜艳，整体有秩序又有混乱的效果", "Akira Kurosawa", "名字+描述"),
    # 关键对照：去掉名字，只留人类写的风格描述 —— 这才测的是风格理解
    ("色彩鲜艳，整体有秩序又有混乱的效果", "Akira Kurosawa", "纯描述(无名字)"),
    ("霓虹夜色，慢门，暧昧的感觉", "Wong Kar-wai", "纯描述(无名字)"),
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


def run(model_path, label, corpus, imgs):
    m = Emb(model_path)
    de = torch.cat([m([d["text_semantic"] for d in corpus[i:i+64]], "passage: ")
                    for i in range(0, len(corpus), 64)]).cpu()
    qe = m([q for q, *_ in REAL], "query: ").cpu()
    S = (qe @ de.T).numpy()

    directors = [d["director"] for d in corpus]
    print("=" * 84)
    print(f"模型: {label}")
    print("=" * 84)
    out = {}
    for qi, (query, truth, kind) in enumerate(REAL):
        # 每个导演取最高分
        best = {}
        for j, d in enumerate(directors):
            if d not in best or S[qi][j] > best[d][0]:
                best[d] = (float(S[qi][j]), j)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
        rank = next(i + 1 for i, (d, _) in enumerate(ranked) if d == truth)

        print(f"\n[Q{qi+1}] ({kind}) {query}")
        print(f"      期望导演: {truth}   -> 导演排名 第 {rank} / {len(ranked)}")
        print(f"      Top-8 召回导演:")
        for i, (d, (sc, j)) in enumerate(ranked[:8]):
            mark = " <<<" if d == truth else ""
            print(f"        {i+1:>2}. {d:<32} {sc:.4f}{mark}")
        out[query] = {"rank": rank, "top": [d for d, _ in ranked[:8]]}
    return out


def main():
    corpus = load(CORPUS)
    print(f"corpus={len(corpus)}  真实 query={len(REAL)}\n")

    # 语料签名 vs 用户用词
    print("=" * 84)
    print("语料里这两位导演的签名（对照用户描述）")
    print("=" * 84)
    for _, truth, *_ in REAL:
        d = next(x for x in corpus if x["director"] == truth)
        print(f"\n  {truth} / {d['director_zh']}")
        print(f"    中文标签 kw_zh : {'、'.join(d['kw_zh'])}")
        print(f"    英文签名       : {', '.join(d['style_tags'])}")
        print(f"    示例描述       : {d['description'][:110]}")

    print()
    r1 = run(BASE, f"baseline ({BASE})", corpus, REAL)
    print()
    if os.path.exists(PROD):
        r2 = run(PROD, f"微调后 ({PROD})", corpus, REAL)
    else:
        print(f"!! 未找到微调模型 {PROD}，先训生产版")
        r2 = None

    if r2:
        print("\n" + "=" * 84)
        print("对比")
        print("=" * 84)
        for q, _, kind in REAL:
            a = r1[q]["rank"]; b = r2[q]["rank"]
            print(f"  {q[:40]:<42} 第 {a:>3} 名 -> 第 {b:>3} 名  ({(a-b)/a*100:+.0f}%)")

    p = os.path.join(ROOT, "bench", "eval_real.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"base": r1, "finetuned": r2}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {p}")
    print("\n### REAL_EVAL_DONE")


if __name__ == "__main__":
    main()
