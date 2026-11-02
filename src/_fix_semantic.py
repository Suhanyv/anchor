"""
修正语义索引：签名要对上现有实现

现有：`_encode_texts(tok, enc, device, texts, prefix)`、`_load(model, corpus, device, ...)` 返回 st
所以语义索引要接收 st，而不是自己找模型。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

start = s.index("_SEM_CACHE = {}")
end = s.index("def _expand_query(q):")
new_fn = '''_SEM_CACHE = {}


def _sem_index(st, filename):
    """给一张词表建语义索引：每条把 zh/desc + kw 拼成一句再编码。

    只建一次，缓存在模块里（表都是几十条）。
    """
    if filename in _SEM_CACHE:
        return _SEM_CACHE[filename]
    rows = _load_ref(filename)
    if not rows:
        _SEM_CACHE[filename] = None
        return None
    try:
        names, texts = [], []
        for name, row in rows.items():
            z = row.get("zh") or row.get("desc") or ""
            kws = "、".join(row.get("kw") or [])
            texts.append(f"{z}。{kws}")
            names.append(name)
        emb = _encode_texts(st["tok"], st["enc"], st["device"], texts, "passage: ")
        _SEM_CACHE[filename] = {"names": names,
                                "rows": [rows[n] for n in names],
                                "emb": emb}
    except Exception as e:
        _SEM_CACHE[filename] = None
        return None
    return _SEM_CACHE[filename]


def _sem_top(st, filename, query, k=1):
    """语义检索一张表。返回 [(score, name)]，降序。"""
    idx = _sem_index(st, filename)
    if not idx or not (query or "").strip():
        return []
    try:
        import torch
        qe = _encode_texts(st["tok"], st["enc"], st["device"], [query], "query: ")
        with torch.no_grad():
            sims = (idx["emb"] @ qe.T).squeeze(-1).cpu().numpy()
        order = sims.argsort()[::-1][:k]
        return [(float(sims[i]), idx["names"][i]) for i in order]
    except Exception:
        return []


def _sem_row(filename, name):
    idx = _SEM_CACHE.get(filename) or {}
    for n, r in zip(idx.get("names") or [], idx.get("rows") or []):
        if n == name:
            return r
    return {}


'''
s = s[:start] + new_fn + s[end:]
ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  语义索引已改成接收 st 的签名")
