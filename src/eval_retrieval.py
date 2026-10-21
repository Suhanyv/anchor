"""
检索评测：分域 × 分语言的 Recall@k / MRR@10 / NDCG@10

设计要点
  * 不报"平均跨语言分数" —— 必须分域、分语言对，否则德语的问题会被掩盖
  * 支持 e5 系列的 query:/passage: 前缀
  * 输出 (query_lang -> doc_lang) 维度的矩阵

数据格式（jsonl）
  corpus.jsonl : {"doc_id": str, "text": str, "lang": "en|zh|ja|ko|de", "domain": str}
  queries.jsonl: {"query_id": str, "query": str, "lang": "zh", "domain": str,
                  "relevant": ["doc_id", ...]}

用法
  python eval_retrieval.py --make-sample            # 生成冒烟测试数据
  python eval_retrieval.py                          # 跑评测
"""
import argparse
import json
import os
import random
from collections import defaultdict

import numpy as np

DATA = r"F:\llm\data\sample"
SAMPLE_TOPICS = [
    # (id, {lang: text})
    ("t01", {"en": "cyberpunk city at night, neon signs, heavy rain, cinematic lighting",
             "zh": "赛博朋克城市夜景，霓虹灯招牌，大雨，电影级光照",
             "ja": "サイバーパンクの夜景、ネオンサイン、大雨、シネマティックな光",
             "ko": "사이버펑크 도시 야경, 네온 사인, 폭우, 영화적 조명",
             "de": "Cyberpunk-Stadt bei Nacht, Neonreklame, starker Regen, filmische Beleuchtung"}),
    ("t02", {"en": "watercolor illustration of a quiet mountain village in morning mist",
             "zh": "水彩插画，晨雾中的宁静山村",
             "ja": "水彩イラスト、朝霧の中の静かな山村",
             "ko": "수채화 일러스트, 아침 안개 속의 조용한 산촌",
             "de": "Aquarellillustration eines stillen Bergdorfs im Morgennebel"}),
    ("t03", {"en": "debounce user input before firing an API request",
             "zh": "在发起 API 请求前对用户输入做防抖",
             "ja": "APIリクエスト前にユーザー入力をデバウンスする",
             "ko": "API 요청 전에 사용자 입력을 디바운스하기",
             "de": "Benutzereingabe entprellen, bevor eine API-Anfrage gesendet wird"}),
    ("t04", {"en": "isometric pixel art of a tiny coffee shop, warm orange light",
             "zh": "等距像素画，小小的咖啡店，温暖橙色灯光",
             "ja": "アイソメトリックなドット絵の小さな喫茶店、温かいオレンジ色の光",
             "ko": "아이소메트릭 픽셀 아트, 작은 커피숍, 따뜻한 주황색 조명",
             "de": "Isometrische Pixelart eines kleinen Cafés, warmes oranges Licht"}),
    ("t05", {"en": "how to split a large logfile into rotated chunks on linux",
             "zh": "在 Linux 上如何把大日志文件按大小切割轮转",
             "ja": "Linuxで大きなログファイルをサイズで分割ローテーションする方法",
             "ko": "Linux에서 큰 로그 파일을 크기별로 분할 순환하는 방법",
             "de": "Wie man eine große Logdatei unter Linux nach Größe rotierend aufteilt"}),
]


def make_sample(seed=0):
    os.makedirs(DATA, exist_ok=True)
    rnd = random.Random(seed)
    corpus, queries = [], []
    for tid, texts in SAMPLE_TOPICS:
        for lang, text in texts.items():
            corpus.append({"doc_id": f"{tid}-{lang}", "text": text, "lang": lang, "domain": "sample"})
    # 干扰项：每语言各造 30 条噪音文档，避免"候选集太小"导致指标虚高
    noise_zh = ["红烧肉的家常做法", "如何更换汽车轮胎", "股票市场的基本面分析", "婴儿奶粉冲泡温度",
                "古典钢琴曲推荐", "装修涂料选购指南", "马拉松训练计划", "猫咪掉毛怎么办"]
    noise_en = ["how to bake sourdough bread", "replacing brake pads on a sedan", "basics of bond valuation",
                "best hiking trails in autumn", "understanding the offside rule"]
    for i in range(30):
        corpus.append({"doc_id": f"n-zh-{i}", "text": noise_zh[i % len(noise_zh)] + f" 编号{i}",
                       "lang": "zh", "domain": "sample"})
        corpus.append({"doc_id": f"n-en-{i}", "text": noise_en[i % len(noise_en)] + f" no.{i}",
                       "lang": "en", "domain": "sample"})
    # 中文 query -> 各语言文档
    for tid, texts in SAMPLE_TOPICS:
        queries.append({"query_id": f"q-{tid}-zh", "query": texts["zh"], "lang": "zh",
                        "domain": "sample", "relevant": [f"{tid}-{l}" for l in texts]})

    with open(os.path.join(DATA, "corpus.jsonl"), "w", encoding="utf-8") as f:
        for r in corpus:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(DATA, "queries.jsonl"), "w", encoding="utf-8") as f:
        for r in queries:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"sample written: {len(corpus)} docs, {len(queries)} queries -> {DATA}")
    print("NOTE: 这是冒烟测试数据，指标无实际意义，只验证管线。")


def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def ndcg_at_k(ranked, relevant, k):
    rel = set(relevant)
    dcg = sum(1.0 / np.log2(i + 2) for i, d in enumerate(ranked[:k]) if d in rel)
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(len(rel), k)))
    return dcg / ideal if ideal > 0 else 0.0


def evaluate(corpus, queries, model_name, batch_size, k, out_path, query_prefix, passage_prefix):
    from sentence_transformers import SentenceTransformer
    import torch

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"loading {model_name} on {dev} ...")
    model = SentenceTransformer(model_name, device=dev)

    # 字段自适应：text / description / prompt 都认
    field = None
    for cand in ("text", "description", "prompt"):
        if corpus and cand in corpus[0]:
            field = cand
            break
    if field is None:
        raise SystemExit(f"corpus 没有可用的文本字段，keys={list(corpus[0].keys())}")
    print(f"using doc field: {field}")
    doc_texts = [d[field] for d in corpus]
    print(f"encoding {len(doc_texts)} docs ...")
    doc_emb = model.encode(doc_texts, batch_size=batch_size, normalize_embeddings=True,
                           show_progress_bar=False, convert_to_numpy=True,
                           prompt=passage_prefix or None)
    q_texts = [q["query"] for q in queries]
    print(f"encoding {len(q_texts)} queries ...")
    q_emb = model.encode(q_texts, batch_size=batch_size, normalize_embeddings=True,
                         show_progress_bar=False, convert_to_numpy=True,
                         prompt=query_prefix or None)

    sims = q_emb @ doc_emb.T
    doc_lang = np.array([d["lang"] for d in corpus])
    doc_lang_of = {d["doc_id"]: d["lang"] for d in corpus}

    # 分组：domain × query_lang × doc_lang
    # 关键：recall 的分母必须是「该语言下的相关文档数」，否则跨语言横向比较失真
    groups = defaultdict(list)
    for qi, q in enumerate(queries):
        order = np.argsort(-sims[qi])
        for dl in sorted(set(doc_lang)):
            rel_in_lang = [r for r in q["relevant"] if doc_lang_of.get(r) == dl]
            if not rel_in_lang:          # 该语言没有相关文档 -> 不统计，而不是记 0
                continue
            sub = [i for i in order if doc_lang[i] == dl]
            ranked = [corpus[i]["doc_id"] for i in sub[:k]]
            rel_set = set(rel_in_lang)
            hit = [d for d in ranked if d in rel_set]
            groups[(q.get("domain", "-"), q.get("lang", "?"), dl)].append({
                "recall": len(hit) / len(rel_in_lang),
                "mrr": (1.0 / (ranked.index(hit[0]) + 1)) if hit else 0.0,
                "ndcg": ndcg_at_k(ranked, rel_in_lang, k),
            })

    print()
    print("=" * 82)
    print(f"{'domain':<10} {'q_lang':<8} {'doc_lang':<10} {'n':>4} {'Recall@' + str(k):>10} {'MRR@10':>9} {'NDCG@' + str(k):>9}")
    print("=" * 82)
    results = []
    for key in sorted(groups):
        rows = groups[key]
        r = {
            "domain": key[0], "query_lang": key[1], "doc_lang": key[2], "n": len(rows),
            f"recall@{k}": round(float(np.mean([x["recall"] for x in rows])), 4),
            "mrr@10": round(float(np.mean([x["mrr"] for x in rows])), 4),
            f"ndcg@{k}": round(float(np.mean([x["ndcg"] for x in rows])), 4),
        }
        results.append(r)
        print(f"{r['domain']:<10} {r['query_lang']:<8} {r['doc_lang']:<10} {r['n']:>4} "
              f"{r[f'recall@{k}']:>10.4f} {r['mrr@10']:>9.4f} {r[f'ndcg@{k}']:>9.4f}")
    print("=" * 82)
    print("注意：不要看总体平均 —— 只看上面分语言对的行，德语那行才是真相。")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": model_name, "k": k, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {out_path}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(DATA, "corpus.jsonl"))
    ap.add_argument("--queries", default=os.path.join(DATA, "queries.jsonl"))
    ap.add_argument("--model", default="intfloat/multilingual-e5-small")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--query-prefix", default="query: ")
    ap.add_argument("--passage-prefix", default="passage: ")
    ap.add_argument("--make-sample", action="store_true")
    ap.add_argument("--out", default=r"F:\llm\bench\eval_scores.json")
    a = ap.parse_args()

    if a.make_sample:
        make_sample()
    else:
        corpus = load_jsonl(a.corpus)
        queries = load_jsonl(a.queries)
        print(f"corpus={len(corpus)}  queries={len(queries)}")
        evaluate(corpus, queries, a.model, a.batch_size, a.k, a.out,
                 a.query_prefix, a.passage_prefix)
        print("\n### EVAL_DONE")
