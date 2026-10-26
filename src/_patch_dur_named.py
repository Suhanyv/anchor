"""
两处改动

① 时长接线：格式化函数和时长表用了两个来源
-----------------------------------------------
现象：`② 相拥` 表说 3 秒，正文却写 "0 到 4 秒 / 4 到 8 秒"。

原因：`_core` 里的 `dur` 取自文档的 `params.duration`（那条风格样例建议的时长），
而时长表按**这一镜的运动幅度**另算一套（`_ref_duration`）。两套并存，谁也没管谁。

改法：`_core` 里的 dur 改成以 `_ref_duration(query)` 为准（这是我们自己的判断），
文档的 params.duration 只在算不出时兜底。

② 风格可点名：用户写了"用皮影"，就不该看那 0.19 的分数
-------------------------------------------------------
和"精确词命中""平台识别"同一条逻辑：**用户点名了，比余弦相似度更硬。**

做法：查风格索引里有没有实体的中文名/英文名逐字出现在查询里；
有就只在这些实体的文档里取最高分，直接当风格结果。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ---------- ① 时长接线 ----------
old = '''        "ar": params.get("ar") or ("21:9" if domain == "prompt_video" else "2.35:1"),
        "dur": params.get("duration") or "6s",'''
new = '''        "ar": params.get("ar") or ("21:9" if domain == "prompt_video" else "2.35:1"),
        # 时长以"这一镜的运动幅度"为准（我们自己的表），
        # 文档里的 params.duration 只是那条风格样例的建议，不该覆盖它。
        "dur": _dur_from_query(query) or (params.get("duration") or "6s"),'''
assert old in s, "_core 的 dur 行没匹配"
s = s.replace(old, new, 1)

# 新增 _dur_from_query（放在 _core 之前）
if "_dur_from_query" not in s:
    helper = '''def _dur_from_query(query):
    """按运动幅度给这一镜的时长，返回 '5s' 这样的串；算不出就 None。"""
    try:
        sec, kind = _ref_duration(query)
    except Exception:
        return None
    if kind == "未识别" or not sec:
        return None
    # 通用上限 10 秒；平台上下限由 _plan_duration 再卡一次
    return f"{max(3, min(int(sec), 10))}s"


'''
    anchor = "def _core(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, helper + anchor, 1)

# ---------- ② 风格可点名 ----------
if "_named_style" not in s:
    fn = '''def _named_style(q, corpus):
    """查询里是否逐字点了某个风格实体的名。返回该实体的下标列表或 []。"""
    if not q:
        return []
    names = {}
    for i, d in enumerate(corpus):
        for key in ("director_zh", "director"):
            nm = str(d.get(key) or "").strip()
            # 单字名太容易撞（"雪""火"），只认 2 字以上
            if len(nm) >= 2 and nm in q:
                names.setdefault(nm, []).append(i)
    if not names:
        return []
    # 名字长的优先（"皮影戏" 胜过 "皮影"）
    best = max(names, key=len)
    return names[best]


'''
    anchor2 = "def _rank(q, model_dir, corpus_path, device, topk, by, domain=\"auto\","
    assert anchor2 in s
    s = s.replace(anchor2, fn + anchor2, 1)

# 在 _rank 里，风格结果出来之前截住
old2 = '''    if by == "导演/风格聚合":'''
new2 = '''    # 用户逐字点了风格名 -> 只在这些实体的文档里取最高分（不看分数绝对值）
    _named = _named_style(q, corpus)

    if by == "导演/风格聚合":'''
assert old2 in s, "_rank 聚合分支没匹配"
s = s.replace(old2, new2, 1)

# 聚合时若点名了，就只保留点名的实体
old3 = '''        best = {}
        for i in allowed:
            d = corpus[i]'''
new3 = '''        best = {}
        _pool = [i for i in allowed if i in set(_named)] if _named else allowed
        if _named and not _pool:
            _pool = allowed          # 点名的实体不在本域里，退回全池
        for i in _pool:
            d = corpus[i]'''
assert old3 in s, "聚合循环没匹配"
s = s.replace(old3, new3, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  语法 OK；_dur_from_query:", hasattr(N, "_dur_from_query"),
      " _named_style:", hasattr(N, "_named_style"))
