"""
重建中文 query：打破模板坍缩。

原问题：119 条 query 全是同一个模板换三个词，两两余弦 0.9385，
        与「纯模板」相似度 0.9467 —— 内容词完全被淹没。

修复策略
  1. 15 套不同句式（长短、口语/书面、直接/委婉）
  2. 三种信息形态：
       name  : 含导演名（较易，考名字跨语言映射）
       style : 只给风格词（较难，考真风格理解）
       both  : 名字 + 风格（自然）
  3. 确定性随机（固定 seed），可复现
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "query_director.jsonl")

# {kw} = 风格词串, {zh} = 中文导演名
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
]
T_STYLE = [
    "{kw}",
    "{kw} 提示词",
    "想要{kw}的画面，怎么描述",
    "提示词：{kw}",
    "{kw} 这种感觉 英文提示词怎么写",
]
T_NAME = [
    "{zh}风格提示词",
    "像{zh}那样的画面，提示词参考",
    "{zh} 镜头语言 提示词",
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(CORPUS)
    # 按导演聚合
    by_dir = {}
    for d in corpus:
        # 必须用中文关键词：英文 style_tags 会逐字命中 doc，造成数据泄漏
        by_dir.setdefault(d["director"], {"zh": d["director_zh"], "ids": [],
                                          "tags": d["kw_zh"]})
        by_dir[d["director"]]["ids"].append(d["doc_id"])

    rnd = random.Random(20250119)
    queries = []

    for i, (en, info) in enumerate(by_dir.items(), start=1):
        zh, ids, tags = info["zh"], info["ids"], info["tags"]
        kw = "、".join(tags[:3])

        # 60% both / 25% style-only / 15% name-only
        r = rnd.random()
        if r < 0.60:
            tpl, kind = rnd.choice(T_BOTH), "both"
            text = tpl.format(kw=kw, zh=zh)
        elif r < 0.85:
            tpl, kind = rnd.choice(T_STYLE), "style"
            text = tpl.format(kw=kw, zh=zh)
        else:
            tpl, kind = rnd.choice(T_NAME), "name"
            text = tpl.format(kw=kw, zh=zh)

        queries.append({
            "query_id": f"q{i:03d}",
            "query": text,
            "lang": "zh",
            "domain": "prompt_image",
            "relevant": ids,
            "target_director": en,
            "query_kind": kind,          # 便于分层看指标
            "style_tags_zh": tags,
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
    for q in queries[:6]:
        print(f"  [{q['query_kind']:<5}] {q['query']}")
    print("\n### QUERIES_REBUILT")


if __name__ == "__main__":
    main()
