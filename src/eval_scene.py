"""
场景式评测：query 里**不许出现 facet 自己的关键词**

为什么要单独建这个集子
----------------------
现有 2100 条 query 是用 facet 自己的 kw_zh 造的（「留白、空旷」「雾江、孤舟」），
所以它们天然会命中对的实体 —— 83.7% 测的是「关键词能不能路由到实体」。

真实用户不这么写。真实 query 描述的是**一个场景**，不含任何 facet 关键词。
实测（来自用户两条真实提示词）：
    「女骑士骑着披甲战马在无边草原全速疾驰，远景全身，跟随镜头」
        -> 第 1 名 雾江孤舟（Misty River Lone Boat），Villeneuve 前 5 都没有
    「广阔荒原，一个孤独骑士，低地平线，人很小」
        -> 第 1 名 留白构图，第 2 名 雾江孤舟
原因：留白/雾江的签名太通用（emptiness all around / lone / distant），
     成了"空旷磁铁"，会吸走一切孤单空旷的 query。

本集规则
--------
1. query 用中文口语描述场景，**不含 facet 关键词**
2. 每题标注**一个或多个可接受的答案**（真实场景常有多个对答案）
3. 指标：可接受答案中最好的那个排在第几（rank），以及 top1/top3/top5 命中率
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bench", "eval_scene.json")
MAXLEN = 128

# (query, [可接受答案], 备注/来源)
CASES = [
    # ---- 来自 prompt_real_02（用户标注 Denis Villeneuve style）----
    ("女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头",
     ["Denis Villeneuve", "Christopher Nolan", "Ridley Scott"], "prompt_02"),
    ("广阔荒原上只有一个孤独骑士，低地平线，人很小，史诗感",
     ["Denis Villeneuve", "Christopher Nolan", "Terrence Malick"], "prompt_02"),
    ("钢铁盔甲的反光，侧光，深影，冷硬质感",
     ["Denis Villeneuve", "Michael Haneke", "David Fincher"], "prompt_02"),
    ("沙尘弥漫的苍茫大地，巨大的东西压着地平线",
     ["Denis Villeneuve", "Christopher Nolan"], "prompt_02"),

    # ---- 来自 prompt_real_01（机制：躲在植被里偷看，被发现）----
    ("女骑士骑马慢慢走向镜头，有人蹲在草丛里偷看她，她突然发现了",
     ["Alfred Hitchcock"], "prompt_01"),
    ("从树枝后面看过去，前景有草叶挡住画面，像有人藏着",
     ["Alfred Hitchcock"], "prompt_01"),
    ("一个人突然转头直视镜头，好像发现有人在看",
     ["Alfred Hitchcock"], "prompt_01"),

    # ---- 东方实体在**该命中**时能不能命中（对照）----
    ("云雾里的江面，一条小船，远山一层层没入雾中",
     ["Misty River Lone Boat"], "东方-应命中"),
    ("大片空白，中间只有一个很小的东西，四周什么都没有",
     ["Liubai Negative Space"], "东方-应命中"),
    ("一根树枝从画面右下角伸进来，其余都是空的",
     ["One-Corner Composition"], "东方-应命中"),
    ("绢本上画的花鸟，笔很细，颜色很淡",
     ["Song Academy Realism"], "东方-应命中"),
    ("红柱子、宫灯、讲究的唐代宫廷",
     ["Tang Court"], "题材-应命中"),

    # ---- 其他场景（检验通用能力）----
    ("雨夜的街道，霓虹倒映在积水里",
     ["Wong Kar-wai", "Martin Scorsese", "Ridley Scott"], "通用"),
    ("一个杯子放在桌上，光从下面打上来，让人紧张",
     ["Alfred Hitchcock"], "通用-机制"),
    ("两个人隔着桌子面对面坐着，房间完全对称",
     ["Park Chan-wook", "Stanley Kubrick", "Wes Anderson"], "通用"),

    # ---- 来自 prompt_real_06（10 秒一镜到底：学校→杂货铺→CRT→教室）----
    # 注意：这批题是在我按 prompt_06 补过语料**之后**才加进基准的，
    #     单看 c11 的分数偏乐观。正确读法是**对比 c10 与 c11**：
    #     同一批题、两个语料，差异才是补的内容的真实效果。
    ("放假后空无一人的学校，黑色铁门敞开，地面斑驳阳光",
     ["Yasujiro Ozu", "Hirokazu Kore-eda", "Hou Hsiao-hsien", "Edward Yang"], "prompt_06"),
    ("杂货铺门口的老式CRT电视机，屏幕上是纯黑白雪花点",
     ["Tsai Ming-liang", "Jia Zhangke", "Hirokazu Kore-eda"], "prompt_06"),
    ("女生坐在窗边拉小提琴，柔和偏白的光，空气里有尘埃光束",
     ["Yasujiro Ozu", "Hirokazu Kore-eda", "Hou Hsiao-hsien"], "prompt_06"),
    ("走廊里的荧光灯管，地砖上有一摊水渍",
     ["Tsai Ming-liang", "Hirokazu Kore-eda"], "prompt_06"),
    ("玻璃幕墙反射城市天际线，外墙挂满空调外机",
     ["Edward Yang", "Denis Villeneuve"], "prompt_06"),
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


def _check_model(m_path):
    """模型目录不存在时给出可执行的提示，别让 HF 抛「Repo id must use alphanumeric chars」。"""
    if not os.path.isdir(m_path):
        raise SystemExit(
            f"模型目录不存在：{m_path}\n"
            f"先重建：python src/train_embed.py --epochs 6 --dev-ratio 0.01 "
            f"--select-mode final --corpus data/raw/corpus_v16.jsonl "
            f"--queries data/raw/queries_v4_fixed16.jsonl "
            f"--out-dir models/e5-director-c18"
        )
    return m_path


def run(corpus_path, model_path, label):
    corpus = load(corpus_path)
    enc = Enc(model_path)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")
    qe = enc([c[0] for c in CASES], "query: ")
    S = de @ qe.T
    dirs = [d["director"] for d in corpus]

    rows = []
    hit1 = hit3 = hit5 = 0
    print(f"\n=== {label} ===")
    print(f"{'#':>2} {'排名':>4} {'top1':<30} 查询")
    print("-" * 108)
    for qi, (q, accept, src) in enumerate(CASES):
        best = {}
        for j, d in enumerate(dirs):
            if d not in best or S[j][qi] > best[d]:
                best[d] = float(S[j][qi])
        rk = sorted(best.items(), key=lambda kv: -kv[1])
        names = [k for k, _ in rk]
        ranks = [names.index(a) + 1 for a in accept if a in names]
        r = min(ranks) if ranks else 999
        rows.append({"query": q, "accept": accept, "rank": r,
                     "top1": rk[0][0], "top5": names[:5], "src": src})
        if r == 1:
            hit1 += 1
        if r <= 3:
            hit3 += 1
        if r <= 5:
            hit5 += 1
        flag = "" if r <= 5 else "   <<< 落空"
        print(f"{qi+1:>2} {r:>4} {rk[0][0][:28]:<30} {q[:52]}{flag}")

    n = len(CASES)
    print("-" * 108)
    print(f"  top1 {hit1}/{n} = {hit1/n:.0%}    top3 {hit3}/{n} = {hit3/n:.0%}"
          f"    top5 {hit5}/{n} = {hit5/n:.0%}")
    return {"label": label, "n": n, "top1": hit1 / n, "top3": hit3 / n,
            "top5": hit5 / n, "rows": rows}


def main():
    m_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "e5-director-c18")
    c_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
    _check_model(m_path)
    res = run(c_path, m_path, f"{os.path.basename(m_path)} + {os.path.basename(c_path)}")

    print("\n=== 落空的题（rank > 5）===")
    for r in res["rows"]:
        if r["rank"] > 5:
            print(f"  [{r['src']}] {r['query'][:52]}")
            print(f"      期望之一进入前5: {r['accept']}")
            print(f"      实际前5: {r['top5']}")
            print()

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"report -> {OUT}")
    print("\n### EVAL_SCENE_DONE")


if __name__ == "__main__":
    main()
