"""
自动生成候选：从"风格没匹配上"的句子里自己造文档

做法（不许碰留出集）：
    1. 取开发集里风格空的句子
    2. 用嵌入找最近的已有文档
    3. 把那句话里的**名词片段**加进这条文档的关键词，复制成一条新候选
    4. 交给 auto_learn.py 去量：留出集变好才留

这样"学"的是：这个说法该落到哪个已有风格上，而不是新造一个风格。
"""
import json
import re
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
from e2e_bulk import load_cases  # noqa: E402

RAW = r"F:\llm\data\raw"
OUT = r"F:\llm\data\eval\cand_auto.jsonl"

# 太泛、加进关键词会污染的词
STOP = set("""一个人 两个 一个 女人 男人 老人 孩子 有 在 的 了 和 与 把 被 从 到 上 下
起来 正在 忽然 一直 还是 已经 就是 什么 那 这 很 都 也 又 就 而 里 中 外 前 后""".split())


LEXICON = r"F:\llm\data\raw\object_lexicon.txt"
_LEX = [None]


def _lex():
    if _LEX[0] is not None:
        return _LEX[0]
    words = []
    try:
        for line in open(LEXICON, encoding="utf-8"):
            w = line.strip()
            if w and not w.startswith("#"):
                words.append(w)
    except Exception:
        pass
    words.sort(key=len, reverse=True)      # 最长优先
    _LEX[0] = words
    return words


def nouns(q):
    """词典最长匹配：从句子取出真正见过的物件/场所词。"""
    lex = _lex()
    body = q or ""
    taken = [False] * len(body)
    out = []
    for w in lex:
        if not w or len(w) < 2:
            continue
        i = body.find(w)
        while i >= 0:
            if not any(taken[i:i + len(w)]):
                for k in range(i, i + len(w)):
                    taken[k] = True
                if w not in out:
                    out.append(w)
            i = body.find(w, i + 1)
    return out[:3]


def main():
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    st = N._load(d["模型目录"][1]["default"], d["语料文件"][1]["default"], "cpu",
                 d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                 d["材质文件"][1]["default"])
    corpus = st["corpus"]

    dev = [q for _sec, q, split in load_cases() if split == "dev"]
    # 加上"真实使用"记下来的句子（评测句在记录时已被过滤）
    try:
        import json as _json
        p = r"F:\llm\data\raw\style_wanted.jsonl"
        seen_dev = set(dev)
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            q2 = _json.loads(line).get("query", "").strip()
            if q2 and q2 not in seen_dev:
                dev.append(q2)          # 和开发集一起当"可学"的输入
    except Exception:
        pass
    cands, seen = [], set()
    for q in dev:
        items, _m, _s, _d, _c, _mt = N._rank(
            q, d["模型目录"][1]["default"], d["语料文件"][1]["default"], "cpu", 1,
            "导演/风格聚合", "video", d["题材文件"][1]["default"],
            d["工艺文件"][1]["default"], d["材质文件"][1]["default"], True)
        it = items[0] if items else {}
        if not N._style_untrusted(it, q):
            continue          # 这条已经能命中，不用补
        # 找最近的文档（用扩展查询，和检索一致）
        st2 = N._load(d["模型目录"][1]["default"], d["语料文件"][1]["default"], "cpu",
                      d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                      d["材质文件"][1]["default"])
        qe = N._encode_query(st2, N._expand_query(q))
        sims = (st2["doc_emb"] @ qe.numpy()).numpy() if hasattr(qe, "numpy") else None
        if sims is None:
            import torch
            sims = (st2["doc_emb"] @ qe).numpy()
        k = int(sims.argmax())
        src = corpus[k]
        key = (src.get("director"), src.get("doc_id"))
        if key in seen:
            continue
        seen.add(key)
        nn = nouns(q)
        if not nn:
            continue
        cands.append({
            "doc_id": f"a{len(cands)+1:04d}",
            "domain": "prompt_video", "lang": "zh", "facet": "风格",
            "director": src.get("director"), "director_zh": src.get("director_zh"),
            "country": src.get("country", ""), "era": src.get("era", ""),
            "style_tags": list(src.get("style_tags") or [])[:4],
            "kw_zh": list(dict.fromkeys(list(src.get("kw_zh") or []) + nn)),
            "description": src.get("description", ""),
            "text_semantic": (src.get("description", "") + "、" + "、".join(nn)),
        })

    with open(OUT, "w", encoding="utf-8") as f:
        for c in cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"  生成候选 {len(cands)} 条 -> {OUT}")
    for c in cands[:6]:
        print(f"    {c['director_zh']}  +kw {c['kw_zh'][-4:]}")


if __name__ == "__main__":
    main()
