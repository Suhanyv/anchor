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


def nouns(q):
    """粗略取名词片段：按标点切开，取 2-4 字的连续汉字段"""
    segs = re.split(r"[，。、；：！？\s]+", q)
    out = []
    for seg in segs:
        seg = re.sub(r"^(一个|两个|三个|那位|这位)", "", seg)
        for m in re.finditer(r"[\u4e00-\u9fff]{2,6}", seg):
            w = m.group(0)
            if w in STOP or len(w) < 2:
                continue
            if w not in out:
                out.append(w)
    return out[:4]


def main():
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    st = N._load(d["模型目录"][1]["default"], d["语料文件"][1]["default"], "cpu",
                 d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                 d["材质文件"][1]["default"])
    corpus = st["corpus"]

    dev = [q for _sec, q, split in load_cases() if split == "dev"]
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
