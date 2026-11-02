"""
升级第一步：给非风格表加语义匹配能力

现在的机制：**关键词命中才触发**。一个词不在表里，所有通道同时哑火
（实测：风格空的 43 条，平均只有 1.2 个维度是具体的）。

这一步只搭基础设施，不动任何现有行为：
    `_sem_index(filename)`  给一张表建向量索引（懒加载、缓存）
    `_sem_top(filename, q, k)` 返回 [(相似度, 词条名, 行)]

阈值之后用数据定（`src/_sem_calib.py`），不拍脑袋。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

FN = '''_SEM_CACHE = {}


def _sem_index(filename):
    """给一张词表建语义索引：每条把 zh + kw 拼成一句话再编码。

    只建一次，之后缓存在模块里（表都不大，几十条）。
    """
    if filename in _SEM_CACHE:
        return _SEM_CACHE[filename]
    rows = _load_ref(filename)
    if not rows:
        _SEM_CACHE[filename] = None
        return None
    try:
        st = _load(_DEFAULT_MODEL_DIR, _DEFAULT_CORPUS, "cpu", None, None, None)
        names, texts = [], []
        for name, row in rows.items():
            z = row.get("zh") or row.get("desc") or ""
            kws = "、".join(row.get("kw") or [])
            texts.append(f"{z}。{kws}")
            names.append(name)
        import torch
        with torch.no_grad():
            emb = _encode_texts(st, texts)
        _SEM_CACHE[filename] = {"names": names, "rows": [rows[n] for n in names],
                                "emb": emb}
    except Exception:
        _SEM_CACHE[filename] = None
    return _SEM_CACHE[filename]


def _sem_top(filename, query, k=1):
    """语义检索一张表。返回 [(score, name, row)]，按分数降序。"""
    idx = _sem_index(filename)
    if not idx or not (query or "").strip():
        return []
    try:
        st = _load(_DEFAULT_MODEL_DIR, _DEFAULT_CORPUS, "cpu", None, None, None)
        import torch
        with torch.no_grad():
            qe = _encode_texts(st, [query])
        sims = (idx["emb"] @ qe.T).squeeze(-1).numpy()
        order = sims.argsort()[::-1][:k]
        return [(float(sims[i]), idx["names"][i], idx["rows"][i]) for i in order]
    except Exception:
        return []


'''
anchor = "def _expand_query(q):"
assert anchor in s, "插入点没找到"
if "def _sem_index" not in s:
    s = s.replace(anchor, FN + anchor, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  已加 _sem_index / _sem_top（尚未接入任何通道）")
