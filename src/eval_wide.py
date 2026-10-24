"""
双口径评测：严格 vs 宽松（允许语义相邻答案）

为什么做
--------
磁铁审计发现，很多「被抢」其实是基准标签过严：
    「手持跟拍一个人跑过拥挤的街道」
        期望 Paul Greengrass / Kathryn Bigelow
        实得 Street Photography
    两者描述的是同一件事（手持、街头、贴身跟拍），只是一个是导演、一个是媒介传统。

纪律
----
1. **宽松口径只能作为补充，永不替换严格口径。** 两个数一起报。
2. **每一条放宽都要写理由**，理由说不清就不放宽。
3. 放宽只加「同一个视觉语言里的等价答案」，不加"看起来也还行"的答案。

用法
----
    python src/eval_wide.py models/e5-director-c27 data/raw/corpus_v21.jsonl
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from eval_motion import CASES as M_CASES          # noqa: E402
from eval_scene import CASES as S_CASES            # noqa: E402
from eval_cn_genre import CASES as G_CASES         # noqa: E402

# (query 片段, 额外可接受的答案, 理由)
ADJACENT = [
    ("手持跟拍", ["Street Photography"],
     "手持贴身跟拍就是街头摄影的语言；导演与媒介在对的地方"),
    ("摄影机贴着人物侧面", ["Street Photography"],
     "同上：侧面贴身跟拍 + 街道，两种标签都成立"),
    ("快速推近一张脸", ["Street Photography"],
     "甩镜抓拍在街头摄影里是同一手法（近身、突然改框）"),
    ("雨夜的狭窄街道", ["Wasteland"],
     "湿街 + 废弃物 + 蒸汽，废土的街道语法同样成立"),
    ("品红和青色霓虹", ["Synthwave", "Vaporwave"],
     "品红+青色就是合成器浪潮/蒸汽波的配色签名"),
    ("强光打在一只举起的手", ["Film Noir"],
     "强光 + 其余全黑 = 明暗对照法，黑色电影与巴洛克共用这套光"),
    ("废墟街道上的巨大管道", ["Wasteland"],
     "废墟街道与管道是废土的核心布景"),
    ("漏水的天花板", ["Wasteland"],
     "废弃建筑的渗漏与积尘，两种标签都说得通"),
    ("女骑士骑马慢慢走向镜头", ["Ching Siu-tung"],
     "骑马走近 + 隐蔽观察，武侠片语言里同样成立"),
    ("金底花园从上面看", ["Rimpa", "Tibetan Thangka"],
     "金底 + 俯视 + 平铺，琳派与唐卡共用这套空间处理"),
    ("土红色墙上飞天", ["Minhwa"],
     "平涂 + 土红 + 纸/壁面基底，民画语言相通"),
    ("平涂的蓝色巨浪", ["Rimpa"],
     "平涂 + 水纹 + 装饰性波纹，琳派与浮世绘同源"),
]

WIDE_CACHE = {}


def widen(query, accept):
    """返回 (宽松后的可接受集合, 命中的理由列表)"""
    if query in WIDE_CACHE:
        return WIDE_CACHE[query]
    out = set(accept)
    reasons = []
    for frag, extras, why in ADJACENT:
        if frag in query:
            for e in extras:
                if e not in out:
                    out.add(e)
                    reasons.append(f"{e}（{why}）")
    WIDE_CACHE[query] = (out, reasons)
    return out, reasons


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "e5-director-c27")
    corpus_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "raw", "corpus_v21.jsonl")
    if not os.path.isdir(model):
        raise SystemExit(f"模型目录不存在：{model}")

    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8") if l.strip()]
    dirs = [d["director"] for d in corpus]

    groups = {
        "运镜 25 题": [(q, set(a)) for q, a, *_ in M_CASES],
        "场景 20 题": [(q, set(a)) for q, a, *_ in S_CASES],
        "中国类型片 9 题": [(q, set(a)) for q, a, *_ in G_CASES],
    }

    tok = AutoTokenizer.from_pretrained(model)
    enc = AutoModel.from_pretrained(model).eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    @torch.no_grad()
    def encode(texts, prefix):
        out = []
        for i in range(0, len(texts), 32):
            b = tok([prefix + t for t in texts[i:i + 32]], padding=True,
                    truncation=True, max_length=128, return_tensors="pt")
            h = enc.__call__(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()

    de = encode([d["text_semantic"] for d in corpus], "passage: ")
    print(f"模型 {os.path.basename(model)}   语料 {len(corpus)} 条\n")

    print(f"{'基准':<18} {'严格@1':>8} {'宽松@1':>8} {'严格@3':>8} {'宽松@3':>8}")
    print("-" * 60)
    totals = {"strict1": 0, "wide1": 0, "strict3": 0, "wide3": 0, "n": 0}
    for label, cases in groups.items():
        qe = encode([c[0] for c in cases], "query: ")
        s1 = w1 = s3 = w3 = 0
        for qi, (q, accept) in enumerate(cases):
            s = de @ qe[qi]
            best = {}
            for j, d in enumerate(dirs):
                if d not in best or s[j] > best[d]:
                    best[d] = float(s[j])
            rk = [k for k, _ in sorted(best.items(), key=lambda kv: -kv[1])]
            wide, _ = widen(q, accept)

            def rank(aset):
                rs = [rk.index(a) + 1 for a in aset if a in rk]
                return min(rs) if rs else 999

            r_strict, r_wide = rank(accept), rank(wide)
            s1 += (r_strict == 1)
            w1 += (r_wide == 1)
            s3 += (r_strict <= 3)
            w3 += (r_wide <= 3)
        n = len(cases)
        print(f"{label:<18} {s1/n:>7.0%} {w1/n:>8.0%} {s3/n:>8.0%} {w3/n:>8.0%}")
        totals["strict1"] += s1
        totals["wide1"] += w1
        totals["strict3"] += s3
        totals["wide3"] += w3
        totals["n"] += n

    n = totals["n"]
    print("-" * 60)
    print(f"{'合计 ' + str(n) + ' 题':<18} "
          f"{totals['strict1']/n:>7.0%} {totals['wide1']/n:>8.0%} "
          f"{totals['strict3']/n:>8.0%} {totals['wide3']/n:>8.0%}")

    print("\n=== 本次放宽了哪些（逐条理由）===")
    seen = set()
    for label, cases in groups.items():
        for q, accept in cases:
            _, reasons = widen(q, accept)
            if reasons and q not in seen:
                seen.add(q)
                print(f"  {q[:34]}")
                for r in reasons:
                    print(f"      + {r}")
    if not seen:
        print("  （本模型下无命中放宽项）")

    print("\n判读：严格口径用于和历史数字对比，宽松口径用于判断"
          "'它到底有没有给出一个说得通的答案'。两者都不许单独引用。")
    print("\n### EVAL_WIDE_DONE")


if __name__ == "__main__":
    main()
