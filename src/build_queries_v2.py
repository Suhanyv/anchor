"""
扩展 query 集：119 -> 595（每位导演 5 条）

目的：把评测误差从 ±18pp 压到 ±6pp。
      119 条时每折 dev 只有 5-6 条 style query，任何结论都在噪声里。

做法
  * 模板扩到 27 套（长短、口语/书面、不同工具名）
  * 每位导演 5 条，混合 both / style / name
  * 关键词随机取 2-3 个，避免固定顺序
  * 保持 query_kind，便于分层看指标
"""
import json
import os
import random

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "query_director.jsonl")

# ---- both：风格词 + 导演名
T_BOTH = [
    "想要那种{kw}的感觉，像{zh}的电影，提示词怎么写",
    "{zh}那种{kw}的风格，AI 画图提示词",
    "怎么写出{kw}的画面？类似{zh}",
    "求一个{zh}风格的提示词，要{kw}",
    "{kw}——这种风格叫什么？想找{zh}那样的",
    "帮我生成一段提示词，要{kw}，参考{zh}",
    "{zh}的片子那种{kw}，用 midjourney 怎么描述",
    "有没有{kw}的提示词模板，像{zh}那种",
    "我想要的画面是{kw}，类似{zh}的镜头",
    "做视频的话{kw}这种感觉怎么 prompt，像{zh}",
    "最近在学{zh}的拍法，{kw}那类镜头该怎么写提示词",
    "sora 里能做出{zh}那种{kw}吗？提示词求参考",
    "可灵/即梦里想要{kw}，{zh}那种调子，怎么prompt",
    "业余党求教：{kw}的效果，{zh}风格的提示词有没有模板",
    "{kw}。想要接近{zh}出来的效果",
]
# ---- style：只给风格词
T_STYLE = [
    "{kw}",
    "{kw} 提示词",
    "想要{kw}的画面，怎么描述",
    "提示词：{kw}",
    "{kw} 这种感觉 英文提示词怎么写",
    "只想要{kw}，不说导演风格怎么写",
    "{kw} 的 midjourney 关键词",
    "{kw} 英文怎么说才出效果",
]
# ---- name：只给导演名
T_NAME = [
    "{zh}风格提示词",
    "像{zh}那样的画面，提示词参考",
    "{zh} 镜头语言 提示词",
    "模仿{zh}的构图，怎么prompt",
    "{zh}那种味道 英文关键词",
]

PER_DIR = 5

# 全局模板索引 -> 用于「模板级留出」实验（整段句式留作 dev，检验换说法的泛化）
TPL_INDEX = {t: i for i, t in enumerate(T_BOTH + T_STYLE + T_NAME)}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    by_dir = {}
    for d in corpus:
        k = d["director"]
        by_dir.setdefault(k, {"zh": d["director_zh"], "ids": [], "kw": d["kw_zh"]})
        by_dir[k]["ids"].append(d["doc_id"])

    rnd = random.Random(20260120)
    queries = []
    qi = 0
    for en, info in by_dir.items():
        zh, ids, kws = info["zh"], info["ids"], info["kw"]
        # 每位导演 5 条：3 both / 1 style / 1 name
        plan = ["both", "both", "both", "style", "name"]
        used = set()
        for kind in plan:
            qi += 1
            # 关键词随机取 2-3 个
            n_kw = rnd.choice([2, 3, 3])
            kw = "、".join(rnd.sample(kws, min(n_kw, len(kws))))
            if kind == "both":
                pool = [t for t in T_BOTH if t not in used] or T_BOTH
            elif kind == "style":
                pool = [t for t in T_STYLE if t not in used] or T_STYLE
            else:
                pool = [t for t in T_NAME if t not in used] or T_NAME
            tpl = rnd.choice(pool)
            used.add(tpl)
            queries.append({
                "query_id": f"q{qi:04d}",
                "query": tpl.format(kw=kw, zh=zh),
                "lang": "zh",
                "domain": "prompt_image",
                "relevant": ids,
                "target_director": en,
                "query_kind": kind,
                "template_id": f"{kind}:{TPL_INDEX[tpl]}",
                "template": tpl,
            })

    with open(OUT, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(q["query_kind"] for q in queries)
    lens = [len(q["query"]) for q in queries]
    print(f"queries: {len(queries)} -> {OUT}")
    print(f"  kind: {dict(c)}")
    print(f"  长度: 均值 {sum(lens)/len(lens):.1f} 字, 最短 {min(lens)}, 最长 {max(lens)}")
    print("\n样例：")
    for kind in ("both", "style", "name"):
        ex = [q["query"] for q in queries if q["query_kind"] == kind][:3]
        for e in ex:
            print(f"  [{kind:<5}] {e}")
    print("\n### QUERIES_V2_DONE")


if __name__ == "__main__":
    main()
