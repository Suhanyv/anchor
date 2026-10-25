"""
收紧精确词命中：只认「条目名」与「长度>=3 的关键词」

问题
----
放宽之后召回 28/28，但误触发 3/10：

    柔光，浅景深      -> 命中（某材质的 kw 里写了"柔光"）
    复古，颗粒感很强   -> 命中（某材质的 kw 里写了"颗粒"）
    霓虹夜色，慢门…    -> 命中（霓虹灯管的 kw 里有"霓虹"）

根因是**数据问题**：部分 kw_zh 放了泛用风格词（柔光/颗粒/霓虹），
它们是形容词或泛指，不是"这个东西的名字"。

规则
----
精确命中只认两类：
    1. 条目名本身（subject_zh / craft_zh / mat_zh），任意长度
    2. kw_zh 且长度 >= 3

"汝窑""拓片"是名字 -> 仍然命中；
"柔光""颗粒""霓虹"是 2 字泛用词 -> 不再命中，
回到分数通道（它们本来也不该被当成内容）。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''def _exact_hits(query, rows, min_len=2):
    """查询里逐字包含某个条目的中文关键词时，返回这些条目的下标。

    只认长度 >= min_len 的词，避免一字词（如"玉""雪"）到处误命中。
    命中的条目按关键词长度排序，长的优先（"汝窑天青"胜过"汝窑"）。
    """
    if not query:
        return []
    hits = []
    for i, r in enumerate(rows):
        for kw in (r.get("kw_zh") or []):
            kw = str(kw).strip()
            if len(kw) >= min_len and kw in query:
                hits.append((len(kw), i))
                break
    hits.sort(key=lambda x: -x[0])
    return [i for _, i in hits]'''

new = '''def _exact_hits(query, rows, min_len=3):
    """查询里逐字包含条目名、或包含长度 >= min_len 的关键词时，返回这些条目的下标。

    为什么不所有关键词都认：
    部分条目的 kw_zh 里放了泛用风格词（"柔光""颗粒""霓虹"），
    它们是形容词或泛指，会把纯风格查询误判成"命中了某材质"。

    所以只认两类：
        1. 条目名本身（*_zh 字段），任意长度
        2. kw_zh 且长度 >= min_len（默认 3）

    命中的条目按匹配词长度排序，长的优先。
    """
    if not query:
        return []
    hits = []
    for i, r in enumerate(rows):
        name = str(r.get("subject_zh") or r.get("craft_zh") or r.get("mat_zh") or "").strip()
        best = 0
        if name and name in query:
            best = len(name)
        for kw in (r.get("kw_zh") or []):
            kw = str(kw).strip()
            if len(kw) >= min_len and kw in query and len(kw) > best:
                best = len(kw)
        if best:
            hits.append((best, i))
    hits.sort(key=lambda x: -x[0])
    return [i for _, i in hits]'''

assert old in s, "找不到 _exact_hits 原实现"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已收紧精确命中规则")
print("  _exact_hits 存在:", hasattr(N, "_exact_hits"))
