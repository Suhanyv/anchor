"""
修复 query 的正例引用：语料重建后 doc_id 会失效

场景
----
corpus_v8 删掉了 5 个 facet 的 32 条旧文档并用新 doc_id 重建，
queries_v4 里 10 条手工东方 query 的 relevant 指向已删除的 id
-> train_embed 报 KeyError: 'd0514'

做法（从宽到严，逐级回退）
----
1. 保留仍然存在的 relevant id
2. 若一条都不剩：取新语料里 (target_director, facet) 的文档
3. 还不够：取 (target_director) 的文档
4. 仍为空：丢弃该 query（并报告，不静默）
"""
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def repair(corpus_path, queries_path, out_path):
    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8")]
    queries = [json.loads(l) for l in open(queries_path, encoding="utf-8")]
    ids = {d["doc_id"] for d in corpus}

    by_dir_facet = defaultdict(list)
    by_dir = defaultdict(list)
    for d in corpus:
        if d.get("domain") not in (None, "prompt_image"):
            continue
        by_dir_facet[(d["director"], d.get("facet", "base"))].append(d["doc_id"])
        by_dir[d["director"]].append(d["doc_id"])

    fixed = dropped = 0
    out = []
    for q in queries:
        rel = list(q.get("relevant") or [])
        alive = [r for r in rel if r in ids]
        if alive:
            if len(alive) != len(rel):
                fixed += 1
            q["relevant"] = alive
            out.append(q)
            continue

        cand = by_dir_facet.get((q["target_director"], q.get("facet", "base")))
        if not cand:
            cand = by_dir.get(q["target_director"])
        if cand:
            q["relevant"] = list(cand)
            q["repaired"] = True
            fixed += 1
            out.append(q)
        else:
            dropped += 1

    with open(out_path, "w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"corpus {len(corpus)} doc / queries {len(queries)}")
    print(f"  修复 {fixed} 条，丢弃 {dropped} 条，输出 {len(out)} 条 -> {out_path}")
    return len(out)


if __name__ == "__main__":
    repair(os.path.join(ROOT, "data", "raw", "corpus_v23.jsonl"),
           os.path.join(ROOT, "data", "raw", "queries_v4.jsonl"),
           os.path.join(ROOT, "data", "raw", "queries_v4_fixed23.jsonl"))
    print("\n### REPAIR_DONE")
