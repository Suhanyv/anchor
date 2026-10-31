"""
节拍匹配改成按优先级

`_match_ref` 是按表顺序找第一个命中的——「抱着纸箱跑」会先撞上「拥抱」。
节拍表加了 `_priority`，匹配时按它排。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''def _scene_beats(query):
    """动作 → 节拍。返回 (第二段, 收尾) 或 ("", "")。

    每条输出以前都挂着同一句「<写：动作怎么继续或停下…>」，
    等于把"这一镜怎么发展"整个交回给人。而动作的推进是可枚举的：
    跑就跑远、打就收势、坐就换重心。填不出仍留占位符。
    """
    row = _match_ref("beat_ref.json", query, [])
    if not row:
        return "", ""
    return (row.get("mid") or ""), (row.get("end") or "")'''
new = '''def _scene_beats(query):
    """动作 → 节拍。返回 (第二段, 收尾) 或 ("", "")。

    每条输出以前都挂着同一句「<写：动作怎么继续或停下…>」，
    等于把"这一镜怎么发展"整个交回给人。而动作的推进是可枚举的：
    跑就跑远、打就收势、坐就换重心。填不出仍留占位符。

    按 `_priority` 排，不按表顺序：实测「抱着纸箱跑」先撞上「拥抱」，
    输出成"手臂收紧、两个人的头靠近"——抱着东西和拥抱是两件事。
    """
    rows = _load_ref("beat_ref.json")
    q = query or ""
    order = rows.get("_priority") or []
    names = [n for n in order if n in rows] + \\
            [n for n in rows if n not in order and not n.startswith("_")]
    for name in names:
        row = rows.get(name) or {}
        if any(k in q for k in (row.get("kw") or [name])):
            return (row.get("mid") or ""), (row.get("end") or "")
    return "", ""'''
assert old in s, "节拍函数没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已改成按优先级")
for q in ("雨里，一个女孩抱着纸箱跑", "拥抱在一起", "雨里，空镜，只剩地面上的水痕"):
    mid, end = N._scene_beats(q)
    print(f"  {q[:16]:<18} mid={mid[:26]}")
