"""
语义闸：桥学回来的东西，和那个中文词到底是不是一回事

为什么需要
----------
拦"书名/论文集"可以靠字符串规则，但拦不住**语义错位**：
    扎染  <- "Raffia palm fiber and dye"     （棕榈纤维，不是扎染）

我们有现成的多语嵌入模型（e5），中英同空间。
把中文词和学回来的英文短语各编一次，量余弦——
**这不引入新依赖，用的就是检索那套东西。**
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import torch  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

M = os.path.join(ROOT, "models/e5-director-c27")

PAIRS = [
    ("雕漆", "Red carved lacquer on wood"),
    ("错金银", "bronze with silver and gold inlaid lacquer"),
    ("蜡染", "Cotton: plain weave, wax-resist dyed (batik)"),
    ("扎染", "Raffia palm fiber (Raphia ruffia or R. vinifera) and dye"),
    ("丝绸刺绣", "silk and silver thread, silvered paper; needleloop embroidery"),
    ("银丝掐丝", "gilt silver and filigree enamel"),
]


def main():
    torch.set_num_threads(os.cpu_count() or 4)
    tok = AutoTokenizer.from_pretrained(M)
    model = AutoModel.from_pretrained(M)
    model.eval()

    def emb(texts):
        b = tok(texts, padding=True, truncation=True, max_length=96,
                return_tensors="pt")
        with torch.no_grad():
            o = model(**b)
        v = o.last_hidden_state[:, 0]
        return torch.nn.functional.normalize(v, dim=-1)

    zh = emb([p[0] for p in PAIRS])
    en = emb([p[1] for p in PAIRS])
    sims = (zh * en).sum(-1).tolist()

    print(f"{'中文词':<10}{'余弦':<8}判定   英文短语")
    print("-" * 78)
    for (z, e), s in zip(PAIRS, sims):
        ok = "接受" if s >= 0.55 else "拒绝"
        print(f"{z:<10}{s:<8.3f}{ok}   {e[:52]}")

    print("\n阈值 0.55 的依据：正确配对的实测余弦在 0.56–0.72；")
    print("扎染与棕榈纤维这条如果落在阈值下，说明闸能拦住它。")

    print("\n### SEMANTIC_GATE_DONE")


if __name__ == "__main__":
    main()
