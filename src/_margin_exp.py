"""
实验：用"领先幅度"代替"关键词命中"来判断风格可信度

现在的判据：查询里出现这条的关键词 → 可信。
问题：关键词是粗的。留出集里那些句子，往往一个关键词都撞不上，
      但检索可能仍然给出了一个合理的风格。

更标准的置信度是 **margin = top1 - top2**：
    第一名明显领先 → 它自己知道是哪个
    前两名贴得很近 → 它其实在猜

这个脚本只量，不改代码：看 margin 能不能把"好匹配"和"坏匹配"分开。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
from e2e_bulk import load_cases  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

st = N._load(M, C, "cpu", S, K, MT)
corpus = st["corpus"]

cases = load_cases()
rows = []
for sec, q, split in cases:
    qe = N._encode_query(st, N._expand_query(q))
    sims = (st["doc_emb"] @ qe).numpy()
    order = sims.argsort()[::-1]
    top1, top2 = float(sims[order[0]]), float(sims[order[1]])
    it = corpus[order[0]]
    kws = list(it.get("kw_zh") or []) + [str(it.get("director_zh") or "")]
    kw_hit = any(k and k in q for k in kws)
    rows.append({"q": q, "split": split, "s1": top1, "s2": top2,
                 "margin": top1 - top2, "kw": kw_hit, "name": it.get("director_zh")})

# 分组看 margin 分布
dev = [r for r in rows if r["split"] == "dev"]
held = [r for r in rows if r["split"] == "heldout"]

def stats(rs, label):
    hit = [r["margin"] for r in rs if r["kw"]]
    miss = [r["margin"] for r in rs if not r["kw"]]
    def p(v, q):
        v = sorted(v)
        return v[int((len(v) - 1) * q)] if v else 0
    print(f"  {label}  n={len(rs)}")
    print(f"    关键词命中 {len(hit):>2} 条  margin: "
          f"中位 {p(hit,.5):.3f} 最小 {p(hit,0):.3f}")
    print(f"    关键词未中 {len(miss):>2} 条  margin: "
          f"中位 {p(miss,.5):.3f} 最大 {p(miss,1):.3f}")

print("=== margin 分布 ===")
stats(dev, "开发集")
stats(held, "留出集")

# 如果改用 margin >= 阈值 才算可信，覆盖率会变成多少
print("\n=== 若改用 margin 判据（关键词不看）===")
print("  阈值   dev可信  heldout可信")
for th in (0.01, 0.02, 0.03, 0.05, 0.08):
    a = sum(1 for r in dev if r["margin"] >= th)
    b = sum(1 for r in held if r["margin"] >= th)
    print(f"  {th:.2f}   {a/len(dev):>6.0%}   {b/len(held):>6.0%}")

print("\n=== 关键词未中、但 margin 很大的例子（说明它其实有把握）===")
for r in sorted([x for x in held if not x["kw"]], key=lambda x: -x["margin"])[:8]:
    print(f"  {r['margin']:.3f}  {r['name']:<8} {r['q'][:22]}")

print("\n### MARGIN_DONE")
