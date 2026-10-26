"""
修一个复合词误判：鲸鱼女孩 → 命中了"鲸"

现象
----
查询「一个男孩和一个鲸鱼女孩在卧室里相拥」，Veo 格式输出：

    a whale's back breaking the surface, water sheeting off it
    in a small bedroom, the bed unmade

**鲸鱼浮出水面，出现在卧室里。**

原因：鲸的 kw_zh 里有"鲸鱼"，而"鲸鱼女孩"包含"鲸鱼" -> 精确词命中
-> 主体 = 鲸 -> 拼上"背露出水面、水淌下来"那句动作描述。

这类错叫**复合词误判**：用户写的是一个组合词（鲸鱼+女孩），
我们只认出了前半截，并把整句具体动作拼了进来。

改法
----
不是删掉"鲸"（那会让鲸鱼相关查询全丢），而是：
1. 从 kw_zh 里去掉"鲸鱼"这种过短的泛称，只保留更专的词
   （蓝鲸 / 座头鲸 / 抹香鲸 / 鲸群）
2. 保留"鲸"但要标成短词——现有的两字黑名单机制不适合（鲸是实体不是形容词）

所以这里只做第 1 步：把宽泛的"鲸鱼"从词表里去掉。
"鲸鱼"单独出现时仍然能通过分数匹配（0.5+），只是不再走精确词旁路。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "subjects_v12.jsonl")
OUT = os.path.join(RAW, "subjects_v13.jsonl")

rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
n = 0
for r in rows:
    if r.get("subject_zh") == "鲸":
        before = list(r.get("kw_zh") or [])
        kw = [w for w in before if w not in ("鲸鱼", "鲸 鱼")]
        for extra in ("蓝鲸", "座头鲸", "抹香鲸", "鲸群", "鲸背"):
            if extra not in kw:
                kw.append(extra)
        r["kw_zh"] = kw
        r["text_semantic"] = (f"{r.get('description','')}，鲸，{'、'.join(kw)}")
        n += 1
        print(f"  {r['doc_id']}  鲸  kw: {before} -> {kw}")

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  subjects_v12 -> v13 : {len(rows)} 条，改了 {n} 条")
print("\n### WHALE_FIX_DONE")
