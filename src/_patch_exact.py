"""
精确词命中：查询里出现索引词表中的中文词，直接采信，不靠分数

为什么需要这个
--------------
门槛标定显示正负样本分数**重叠**：

    负样本最高   混乱失序 工艺 0.505
    正样本最低   拓片 0.359 / 景泰蓝 0.362 / 屏风 0.397

任何单一阈值都分不干净。调低 -> 塞错内容；调高 -> 该填的填不上。

但这两类在**另一个维度上完全不同**：
    正样本  查询里真的写了那个词（"汝窑"、"拓片"、"卧室"）
    负样本  查询里没有任何索引词（"混乱，失序"、"柔光，浅景深"）

所以用**词表精确匹配**做前置判据：
查询包含某条目的 kw_zh（长度>=2）时，直接判定该条目命中，
**绕过分数门槛**（阈值只留给没有精确词的情况）。

这不是调参，是换信号。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_exact_hits" not in s:
    # 1) 工具函数：返回查询里精确命中的条目下标
    anchor = "def _rank(q, model_dir, corpus_path, device, topk, by, domain=\"auto\","
    assert anchor in s
    helper = '''def _exact_hits(query, rows, min_len=2):
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
    return [i for _, i in hits]


'''
    s = s.replace(anchor, helper + anchor, 1)

    # 2) 题材：精确命中的条目优先于 argmax
    old_s = """        ssims = (st["subj_emb"] @ qe).numpy()
        k = int(ssims.argmax())"""
    new_s = """        ssims = (st["subj_emb"] @ qe).numpy()
        _ex = _exact_hits(q, st["subjects"])
        k = int(ssims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(ssims[j]))"""
    assert old_s in s, "题材 argmax 处变了"
    s = s.replace(old_s, new_s, 1)

    # 3) 工艺
    old_c = """        csims = (st["craft_emb"] @ qe).numpy()
        k = int(csims.argmax())"""
    new_c = """        csims = (st["craft_emb"] @ qe).numpy()
        _ex = _exact_hits(q, st["crafts"])
        k = int(csims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(csims[j]))"""
    assert old_c in s, "工艺 argmax 处变了"
    s = s.replace(old_c, new_c, 1)

    # 4) 材质
    old_m = """        msims = (st["mat_emb"] @ qe).numpy()
        k = int(msims.argmax())"""
    new_m = """        msims = (st["mat_emb"] @ qe).numpy()
        _ex = _exact_hits(q, st["materials"])
        k = int(msims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(msims[j]))"""
    assert old_m in s, "材质 argmax 处变了"
    s = s.replace(old_m, new_m, 1)

    # 5) 场景子集也走精确命中
    old_b = """                _kk = int(_sub.argmax())"""
    new_b = """                _kk = int(_sub.argmax())
                _exs = _exact_hits(q, [st["subjects"][i] for i in _ii])
                if _exs:
                    _kk = max(_exs, key=lambda j: float(_sub[j]))"""
    assert old_b in s, "场景 argmax 处变了"
    s = s.replace(old_b, new_b, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加精确词命中；参数", len(N.LocalStyleHint.INPUT_TYPES()["required"]))
print("  _exact_hits 存在:", hasattr(N, "_exact_hits"))
