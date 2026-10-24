"""
中国类型片检索测试：补实体之前 / 之后

为什么单独做一个测试
--------------------
LIMITATIONS 第五节说"缺中国商业类型片实体"，靠的是什么？
靠的是一条实测：「金色佛掌压制巨眼」最高分是索伦蒂诺 0.28，正确答案根本不在库里。
那只是 1 条。要做成可对比的基准，至少 6 条，覆盖 5 个新实体，再加 1 条对照。

这批 query 的特点
-----------------
1. 写成**用户会真说的话**（中文口语，不是关键词堆）
2. 不出现导演名（否则等于查字典，测不出检索）
3. 每条给若干可接受答案（同一导演的不同拼写/其它合理答案）
4. 另设 3 条**不该被新实体抢走**的对照（西方导演的场景），防止补数据把旧能力带坏

用法：
    python src/eval_cn_genre.py                       # 默认 c18 + v16
    python src/eval_cn_genre.py models/e5-director-c19 data/raw/corpus_v17.jsonl
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (中文 query, [可接受导演], 说明)
CASES = [
    ("巨大的行星发动机立在冰原上，底下有一列车队开过去，天是灰的",
     ["Frant Gwo"], "郭帆 · 巨构与冰封地表"),
    ("质子战舞，一群年轻武士穿着青铜纹重甲在校场上齐舞，火把照明",
     ["Wuershan"], "乌尔善 · 仪式群舞"),
    ("老客栈里两拨人隔着一张桌子对峙，木楼梯上一层灰，谁也不动",
     ["King Hu"], "胡金铨 · 客栈对峙"),
    ("白衣女子乘着薄雾从树梢上飘下来，袖子很长，枫叶在飞",
     ["Ching Siu-tung"], "程小东 · 威亚飘逸"),
    ("红莲一样的火焰从脚下炸开，把少年整个人包住，水墨那一类特效",
     ["Jiaozi"], "饺子 · 三维动画火焰"),
    ("一只青铜纹样的巨兽从城墙后面立起来，黄昏，脚下全是烟",
     ["Wuershan"], "乌尔善 · 巨兽与青铜"),
    # ---- 对照：这些不该被新实体抢走 ----
    ("霓虹夜色，慢门，暧昧的感觉", ["Wong Kar-wai"], "对照 · 王家卫"),
    ("两个人面对面坐着，房间完全对称，一个点在正中", ["Stanley Kubrick"], "对照 · 库布里克"),
    ("广阔的荒原上只有一个孤独骑士，地平线很低", ["Denis Villeneuve", "Terrence Malick"],
     "对照 · 维伦纽瓦/马利克"),
]

NEW_ENTITIES = {"Frant Gwo", "Wuershan", "King Hu", "Ching Siu-tung", "Jiaozi"}


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "e5-director-c18")
    corpus_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")

    if not os.path.isdir(model):
        raise SystemExit(f"模型目录不存在：{model}")

    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8") if l.strip()]
    dirs = [d["director"] for d in corpus]
    has_new = sorted(NEW_ENTITIES & set(dirs))
    print(f"模型 {os.path.basename(model)}   语料 {os.path.basename(corpus_path)} "
          f"({len(corpus)} 条)")
    print(f"语料中的新实体: {has_new if has_new else '（无 —— 这就是问题）'}\n")

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
    qe = encode([c[0] for c in CASES], "query: ")

    print(f"{'查询':<30} {'期望':<18} {'实得':<18} 名次")
    print("-" * 92)
    n_genre = n_ctrl = ok_genre = ok_ctrl = 0
    for qi, (q, accept, note) in enumerate(CASES):
        s = de @ qe[qi]
        best = {}
        for j, d in enumerate(dirs):
            if d not in best or s[j] > best[d]:
                best[d] = float(s[j])
        rk = sorted(best.items(), key=lambda kv: -kv[1])
        names = [k for k, _ in rk]
        ranks = [names.index(a) + 1 for a in accept if a in names]
        r = min(ranks) if ranks else 999
        is_genre = accept[0] in NEW_ENTITIES
        mark = "✅" if r == 1 else ("◐" if r <= 3 else "❌")
        print(f"{q[:28]:<30} {accept[0][:16]:<18} {rk[0][0][:16]:<18} "
              f"{r if r != 999 else '不在库'} {mark}")
        if is_genre:
            n_genre += 1
            ok_genre += (r == 1)
        else:
            n_ctrl += 1
            ok_ctrl += (r == 1)

    print("-" * 92)
    print(f"中国类型片: {ok_genre}/{n_genre} 命中第一")
    print(f"对照组    : {ok_ctrl}/{n_ctrl} 命中第一")
    print(f"\n### CN_GENRE_EVAL_DONE")


if __name__ == "__main__":
    main()
