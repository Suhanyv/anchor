"""
材质/光评测：文档级判分，不指定导演

为什么不用导演级判分
--------------------
场景基准里 #3「钢铁盔甲的反光，侧光，深影，冷硬质感」期望 [Villeneuve, Haneke, Fincher]，
实际 top1 是德尔·托罗 —— 他的"冷工业、湿金属、一格冷光管"其实很贴切。
那份可接受名单是我随手定的，**改宽它就是移动球门**。

另一个更客观的做法：这类 query 问的是**材质/光本身**，不是某个导演。
所以判据改成**文档级**：
    检索到的第 1 条 doc 里，有没有出现该材质的英文词？
这不需要我指定任何导演，也不需要"可接受答案"名单。

覆盖的概念来自 src/extract_external_vocab_v2.py 查出的缺口
（高光、羊皮纸、薄纱、拉丝钢、陶瓷、浅景深、暗角、胶片颗粒…）。
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
OUT = os.path.join(ROOT, "bench", "eval_material.json")
MAXLEN = 128

# (中文 query, [top1 文档里应出现的英文词，任一命中即算对], 概念名)
CASES = [
    ("钢铁盔甲的反光，侧光，深影，冷硬质感",
     ["steel", "plate", "armour", "armor", "metal", "highlight", "specular"], "钢/金属"),
    ("白丝绸的垂坠，褶皱随之落下",
     ["silk", "sleeve", "fabric", "cloth", "drapery"], "丝绸"),
    ("雪粒在逆光里飞，细小亮点",
     ["snow", "grain", "grit", "backlit", "light"], "雪粒"),
    ("体积光里的金箔和浮尘",
     ["gold leaf", "gilt", "gold foil", "dust", "shaft", "beam"], "金箔+体积光"),
    ("羊皮纸的质感，边缘泛黄",
     ["parchment", "vellum", "paper", "aged"], "羊皮纸"),
    ("拉丝金属表面，细密纹路",
     ["brushed", "steel", "metal", "polished", "burnished"], "拉丝金属"),
    ("薄纱半透明的袖子，能看见后面的光",
     ["tulle", "gauze", "sheer", "translucent", "semi-transparent"], "薄纱"),
    ("暗角，画面边缘压暗",
     ["vignette", "corner", "falloff"], "暗角"),
    ("浅景深，背景完全虚化",
     ["shallow depth", "shallow focus", "blurred", "out of focus", "defocused"], "浅景深"),
    ("胶片颗粒，粗颗粒质感",
     ["grain", "film grain", "granular"], "胶片颗粒"),
    ("抛光不锈钢上的高光划过",
     ["polished", "stainless", "steel", "highlight", "specular", "glint"], "高光"),
    ("湿混凝土地面的反光",
     ["concrete", "wet", "reflection", "reflecting"], "湿混凝土"),
    ("陶瓷的釉面反光",
     ["ceramic", "porcelain", "glaze"], "陶瓷"),
    ("帆布的粗织纹理",
     ["canvas", "duck cloth", "coarse"], "帆布"),
    ("铅笔线条，石墨的手绘感",
     ["pencil", "graphite", "drawn", "sketch"], "铅笔"),
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


def grade(text, kws):
    t = text.lower()
    return any(k.lower() in t for k in kws)


def run(corpus_path, model_path, label, verbose=False):
    corpus = load(corpus_path)
    enc = Enc(model_path)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([c[0] for c in CASES], "query: ")
    S = de @ qe.T

    ok1 = ok3 = 0
    rows = []
    if verbose:
        print(f"\n{'#':>2} {'概念':<12} {'top1 文档':<58} 判定")
        print("-" * 96)
    for qi, (q, kws, name) in enumerate(CASES):
        order = np.argsort(-S[:, qi])[:3]
        hit1 = grade(corpus[int(order[0])]["text_semantic"], kws)
        hit3 = any(grade(corpus[int(i)]["text_semantic"], kws) for i in order)
        ok1 += hit1
        ok3 += hit3
        rows.append({"query": q, "concept": name,
                     "top1": corpus[int(order[0])]["doc_id"],
                     "top1_text": corpus[int(order[0])]["text_semantic"],
                     "hit1": bool(hit1), "hit3": bool(hit3)})
        if verbose:
            mark = "✅" if hit1 else ("○top3" if hit3 else "❌")
            print(f"{qi+1:>2} {name:<12} {corpus[int(order[0])]['text_semantic'][:56]:<58} {mark}")

    n = len(CASES)
    if verbose:
        print("-" * 96)
    print(f"  {label:<40} 文档级 top1 {ok1}/{n} = {ok1/n:.0%}   top3 {ok3}/{n} = {ok3/n:.0%}")
    return {"label": label, "n": n, "top1": ok1 / n, "top3": ok3 / n, "rows": rows}


def main():
    runs = [
        (r"F:\llm\data\raw\corpus_v12.jsonl", r"F:\llm\models\e5-director-c12", "c12"),
        (r"F:\llm\data\raw\corpus_v13.jsonl", r"F:\llm\models\e5-director-c13", "c13"),
        (r"F:\llm\data\raw\corpus_v14.jsonl", r"F:\llm\models\e5-director-c14", "c14"),
    ]
    print("=== 材质/光 · 文档级判分 ===")
    results = []
    for cp, mp, tag in runs:
        results.append(run(cp, mp, tag, verbose=(tag == "c14")))
    print()
    print("=" * 70)
    print(f"{'版本':<10} {'top1':>8} {'top3':>8}")
    for r in results:
        print(f"{r['label']:<10} {r['top1']:>7.0%} {r['top3']:>8.0%}")
    print("=" * 70)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({r["label"]: {"top1": r["top1"], "top3": r["top3"],
                                "rows": r["rows"]} for r in results},
                  f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### EVAL_MATERIAL_DONE")


if __name__ == "__main__":
    main()
