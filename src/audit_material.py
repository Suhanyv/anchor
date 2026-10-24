"""
材质/光评测的判分方式再检验：词面判分到底低估了多少？

疑点
----
c14 的材质/光文档级得分 47%，8 道失败里命中的文档大多是"语义相近但不含该词"：
    胶片颗粒 -> "70mm wide dusty landscape"（70mm 是胶片规格，但没有 grain）
    高光     -> "a pool party at dusk in warm tungsten light"（有光，没有 highlight）
    暗角     -> "a symmetrical muted interior"（室内，没有 vignette）
这提示 47% 是**词面判分的下限**，不是真实能力。

做法
----
对每道失败的题，把 top1 文档和"该概念的英文词"都编码，算它们之间的余弦相似度。
如果 top1 文档与概念词的相似度已经很高（比如 > 0.75），说明检索其实抓到了概念，
只是没用那个词 -> 词面判分不公平。
如果相似度很低，说明检索确实错了 -> 47% 是真的。

同时对比：该题在 top10 里有没有真正含关键词的文档（如果有，说明是排序问题不是知识缺失）。
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_material as EM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-c18")


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


def main():
    corpus = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    enc = Enc(MODEL)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([c[0] for c in EM.CASES], "query: ")

    print(f"{'概念':<12} {'top1判定':<6} {'top1与概念词相似':>14} {'top10含词':>10}  top1 文档")
    print("-" * 118)
    n_fair = n_unfair = 0
    for qi, (q, kws, name) in enumerate(EM.CASES):
        order = np.argsort(-de[:, 0] * 0 + (-(de @ qe[qi])))[:10]
        top1 = corpus[int(order[0])]["text_semantic"]
        hit1 = EM.grade(top1, kws)
        # top10 里有没有真正含词的
        in10 = any(EM.grade(corpus[int(i)]["text_semantic"], kws) for i in order)
        # top1 文档与该概念词的语义相似度
        kw_emb = enc([kws[0]], "query: ")[0]
        sim = float(de[int(order[0])] @ kw_emb)
        if not hit1 and sim >= 0.60:
            n_unfair += 1
            flag = "词面误判"
        elif not hit1:
            n_fair += 1
            flag = "真错"
        else:
            flag = "对"
        print(f"{name:<12} {('对' if hit1 else '错'):<6} {sim:>14.3f} "
              f"{('有' if in10 else '无'):>10}  {top1[:52]}  [{flag}]")

    print("-" * 118)
    print(f"\n失败项里：约 {n_unfair} 道疑似「词面误判」（top1 与概念词相似度 >= 0.60）")
    print(f"         约 {n_fair} 道是「真错」（相似度低，即检索确实没抓到概念）")
    print("\n判读：若「真错」占多数，则 47% 基本可信；若「词面误判」占多数，则 47% 是低估。")
    print("\n### MATERIAL_AUDIT_DONE")


if __name__ == "__main__":
    main()
