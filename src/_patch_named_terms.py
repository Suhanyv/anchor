"""
点名技法/材质：逐字写了名字，就直接写进【技法】行

为什么不能靠通道
----------------
实测：查询「用顿帧，一个骑士…」得到

    工艺: 顿帧 0.1178 (下限0.52) 未过
    最终: 主体分最高 -> 只拼主体 (0.4989 > 风格 0.4449)

**点名的技法分数永远低于风格**——因为"顿帧"两个字只占查询的一小块。
赢家通吃这条规则是对的（它防的是"没有的事硬拼"），
但"用户点名了"不属于"没有的事"。

所以：点名的条目绕过通道，直接进【技法】行。
和"点名风格""点名平台"是同一条道理——**用户说了，就不看分数**。
"""
import ast
import json
import os
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_named_index_terms" not in s:
    fn = '''_IDX_CACHE = {}


def _load_index(filekey):
    """按节点的默认值取索引文件（不写死文件名，避免又一次漂移）。"""
    if filekey in _IDX_CACHE:
        return _IDX_CACHE[filekey]
    try:
        d = LocalStyleHint.INPUT_TYPES()["required"]
        p = d[filekey][1]["default"]
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    except Exception:
        rows = []
    _IDX_CACHE[filekey] = rows
    return rows


def _named_index_terms(query):
    """查询里逐字点名的技法/材质，返回 [(中文名, 一句可粘的描述)]。

    不走通道、不看分数——用户点了名就该用。
    """
    q = query or ""
    out = []
    for filekey, namekey, extrakey in (
            ("工艺文件", "craft_zh", "description"),
            ("材质文件", "mat_zh", "description")):
        for r in _load_index(filekey):
            nm = str(r.get(namekey) or "").strip()
            if len(nm) < 2 or nm not in q:
                continue
            # 英文模板要 phrase，中文模板要 description
            zh = (r.get(extrakey) or nm).split("：")[-1].strip()
            out.append((nm, zh[:60] or nm))
    return out


'''
    anchor = "def _match_ref(filename, query, kw=None):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 整段格式：技法行合并"症状手段"与"点名条目"
old = '''    _hit_s, _means = _symptom_means(query)
    if _means:
        seg.append("技法：" + "；".join(_means[:4]) + "。")'''
new = '''    _hit_s, _means = _symptom_means(query)
    _named = [zh for _n, zh in _named_index_terms(query)]
    _all = list(dict.fromkeys(_named + _means))
    if _all:
        seg.append("技法：" + "；".join(_all[:5]) + "。")'''
assert old in s, "技法行没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _named_index_terms:", hasattr(N, "_named_index_terms"))
print("  试查:", N._named_index_terms("用顿帧，一个骑士和一群人交战")[:1])
print("  试查:", N._named_index_terms("札甲上有锻打铁")[:2])
