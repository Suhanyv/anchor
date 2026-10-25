"""
为「简牍 / 帛书」补训练 query

为什么必须补
------------
v23 加了两实体 12 条文档，但实测：
    「一卷竹简摊开在桌上」  -> 修好了（风格分 0.2516 -> 0.3177）
    「一个人拿起桌上的竹简」-> 仍然判成「武侠竹林」
    「帛书」               -> 仍然判成 Minhwa

原因今天已经验证过三次：**新增维度只加文档没用，查询侧要覆盖才学得到**
（视频运镜那次：文档侧加运镜 0 收益，加 query 才 +24pp）。

这批 query 的关键是**把"竹简/木牍/简册/帛书/丝帛"这些词真的说进训练数据**，
否则模型不知道这个中文词对应那批英文文档。
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from lang_templates import TRAIN_ZH  # noqa: E402

CORPUS = os.path.join(ROOT, "data/raw/corpus_v23.jsonl")
BASE_Q = os.path.join(ROOT, "data/raw/queries_v4_fixed23c.jsonl")
OUT_Q = os.path.join(ROOT, "data/raw/queries_medium_v23.jsonl")
MERGED = os.path.join(ROOT, "data/raw/queries_v4_fixed23m.jsonl")

TARGETS = {"Bamboo Slips", "Silk Manuscript"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    rnd = random.Random(20261025)
    corpus = load(CORPUS)
    groups = {}
    for d in corpus:
        if d["director"] in TARGETS:
            groups.setdefault(d["director"], []).append(d)

    qs = []
    for who, docs in groups.items():
        ids = [d["doc_id"] for d in docs]
        kws = []
        for d in docs:
            kws.extend(d.get("kw_zh") or [])
        kws = list(dict.fromkeys(kws))
        if len(kws) < 2:
            continue
        who_zh = docs[0].get("director_zh", who)
        # 每个句式 2 条；另外单独补 3 条"只说名字"的短 query
        for ti, tpl in enumerate(TRAIN_ZH):
            for _ in range(2):
                pick = rnd.sample(kws, min(3, len(kws)))
                qs.append({
                    "query_id": f"qm{len(qs):05d}",
                    "query": tpl.format(kw="、".join(pick)),
                    "lang": "zh", "domain": "prompt_image",
                    "relevant": ids, "target_director": who, "facet": "base",
                    "query_kind": "style", "template_id": f"medium:{ti}",
                    "template": tpl,
                })
        for short in (who_zh, f"{who_zh}的样子", f"一卷{who_zh}"):
            qs.append({
                "query_id": f"qm{len(qs):05d}",
                "query": short,
                "lang": "zh", "domain": "prompt_image",
                "relevant": ids, "target_director": who, "facet": "base",
                "query_kind": "style", "template_id": "medium:short",
                "template": "{kw}",
            })

    with open(OUT_Q, "w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"  新实体 query: {len(qs)} 条（覆盖 {len(groups)} 个实体）")

    base = load(BASE_Q)
    merged = base + qs
    with open(MERGED, "w", encoding="utf-8") as f:
        for q in merged:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"  合并 {len(base)} + {len(qs)} = {len(merged)}"
          f"（新实体占 {len(qs)/len(merged):.0%}）")
    print("### MEDIUM_QUERIES_DONE")


if __name__ == "__main__":
    main()
