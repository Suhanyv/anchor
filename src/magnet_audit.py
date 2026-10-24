"""
磁铁审计：谁抢了不该抢的 query

背景
----
"磁铁"指某些实体的描述用了**通用属性词**（lone / distant / mist / emptiness /
horizontal / vast），于是吸走大量语义相近但答案不同的 query。
LIMITATIONS 第七节记着四个已知磁铁（手卷 / 雾江 / 留白 / 冬季黑白），
但一直靠人工观察，没有量化。

做法
----
把四个基准的所有用例汇总（motion 25 + scene 20 + cn_genre 9 + material 15 + 新实体 24），
对每条 query 找 top-1 实体；如果它不在可接受答案里，就记一次「被抢」，
统计每个实体的「抢次数 / 抢了谁」。

抢次数高、且自己作为正确答案时命中又低的 -> 就是磁铁。
"""
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eval_motion import CASES as M_CASES        # noqa: E402
from eval_scene import CASES as S_CASES         # noqa: E402
from eval_cn_genre import CASES as G_CASES      # noqa: E402

# 新实体（v0.1.3 / v0.1.5 加的那批）——没写进独立文件，在这里内联
NEW_CASES = [
    ("一个人的脸在列车窗上反射，窗外城市飞逝", ["Satoshi Kon"]),
    ("运河城市的夜景，招牌层层叠叠，管道和水面", ["Mamoru Oshii"]),
    ("废墟街道上的巨大管道和混凝土结构", ["Katsuhiro Otomo"]),
    ("水彩画的山坡，几个很小的人在干活", ["Isao Takahata"]),
    ("空荡荡的走廊，平庸的灰光，远处有一扇开着的门", ["Kiyoshi Kurosawa"]),
    ("漏水的天花板，下面放着一个盆接水", ["Chantal Akerman"]),
    ("品红和青色霓虹里一个穿皮衣的人不动", ["Nicolas Winding Refn"]),
    ("手持跟拍一个人跑过拥挤的街道", ["William Friedkin"]),
    ("平涂的蓝色巨浪卷过几只小船，轮廓线很重", ["Ukiyo-e"]),
    ("土红色墙上飞天带着长飘带，颜料在剥落", ["Dunhuang Murals"]),
    ("金底上一个居中的曼陀罗，青金石和朱红", ["Tibetan Thangka"]),
    ("金底花园从上面看，层层平铺没有透视", ["Persian Miniature"]),
    ("一只脸很搞笑的老虎，大块平涂，周围是没画的纸", ["Minhwa"]),
    ("海报里的女人，长头发直接变成装饰线条", ["Art Nouveau"]),
    ("强光打在一只举起的手上，其余全是黑的，金色装饰", ["Baroque"]),
    ("雨夜的狭窄街道，汉字招牌层层叠叠，蒸汽", ["Cyberpunk"]),
    ("百叶窗的影子打在墙上和床上，人只有半张脸亮", ["Film Noir"]),
    ("河岸边的碎笔触，阴影里带紫，没有轮廓线", ["Impressionism"]),
    ("一张脸同时从两个角度被看到，碎成几个面", ["Cubism"]),
    ("软绵绵的钟搭在树枝上，后面是沼泽", ["Surrealism"]),
    ("红方形黄圆形蓝三角形，没有任何质感", ["Bauhaus"]),
    ("金底上平涂的银色河水，留白很大", ["Rimpa"]),
    ("白边的拍立得相纸，颜色偏绿，很柔", ["Polaroid"]),
    ("一只脸重复四次，每次不同的平涂颜色", ["Pop Art"]),
]


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

    # 汇总用例：(query, 可接受实体集合, 来源)
    cases = []
    for q, accept, *_ in M_CASES:
        cases.append((q, set(accept), "motion"))
    for q, accept, *_ in S_CASES:
        cases.append((q, set(accept), "scene"))
    for q, accept, *_ in G_CASES:
        cases.append((q, set(accept), "genre"))
    for q, accept in NEW_CASES:
        cases.append((q, set(accept), "newent"))

    print(f"模型 {os.path.basename(model)}   语料 {len(corpus)} 条")
    print(f"汇总用例 {len(cases)} 条（motion {len(M_CASES)} / scene {len(S_CASES)} / "
          f"genre {len(G_CASES)} / newent {len(NEW_CASES)}）\n")

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
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()

    de = encode([d["text_semantic"] for d in corpus], "passage: ")
    qe = encode([c[0] for c in cases], "query: ")

    steals = Counter()          # 抢了谁 -> 次数
    stolen_from = defaultdict(Counter)
    right = Counter()           # 自己作为正确答案被命中的次数
    attempts = Counter()        # 自己作为正确答案出现的次数

    for qi, (q, accept, src) in enumerate(cases):
        s = de @ qe[qi]
        best = {}
        for j, d in enumerate(dirs):
            if d not in best or s[j] > best[d]:
                best[d] = float(s[j])
        rk = sorted(best.items(), key=lambda kv: -kv[1])
        top = rk[0][0]
        for a in accept:
            attempts[a] += 1
        if top in accept:
            right[top] += 1
        else:
            steals[top] += 1
            stolen_from[top]["/".join(sorted(accept))] += 1

    print(f"{'抢次数':>6} {'实体':<26} {'被抢的用例（前 3）'}")
    print("-" * 96)
    for ent, n in steals.most_common(15):
        who = "; ".join(f"{k}×{v}" for k, v in stolen_from[ent].most_common(3))
        print(f"{n:>6} {ent[:24]:<26} {who[:56]}")

    print()
    print("=== 判读：抢得多、但自己正确率也低 -> 磁铁 ===")
    print(f"{'实体':<26} {'抢':>4} {'自己答对':>8} {'出现次数':>8}  判定")
    print("-" * 96)
    for ent, n in steals.most_common(12):
        r = right[ent]
        a = attempts[ent]
        rate = f"{r}/{a}" if a else "-"
        # 判定：抢 ≥3 且（不是正确答案 或 正确率 < 50%）
        magnet = n >= 3 and (a == 0 or r / a < 0.5)
        print(f"{ent[:24]:<26} {n:>4} {rate:>8} {a:>8}  {'磁铁 ⚠' if magnet else '正常'}")

    print("\n### MAGNET_AUDIT_DONE")


if __name__ == "__main__":
    main()
