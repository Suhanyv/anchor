"""
让精确词命中绕过分数门槛

上一处补丁只让精确命中的条目在 argmax 里优先，但**门槛仍然拦着它**：
拓片 0.359 精确命中了「拓片」这个词，却过不了 0.52 的门槛，仍然不触发。

这一处改门槛判定：

    旧：score > 风格分  且  score >= 该通道门槛
    新：score > 风格分  且  (精确词命中 或 score >= 该通道门槛)

理由：查询里逐字写了那个词，是比余弦相似度更强的证据。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# 1) 各通道记下 exact 标记
REPL = [
    ('        subj = {"score": float(ssims[k]), "en": s["subject_en"],',
     '        subj = {"exact": bool(_ex), "score": float(ssims[k]), "en": s["subject_en"],'),
    ('        craft = {"score": float(csims[k]), "en": c["craft_en"],',
     '        craft = {"exact": bool(_ex), "score": float(csims[k]), "en": c["craft_en"],'),
    ('        mat = {"score": float(msims[k]), "en": m["mat_en"],',
     '        mat = {"exact": bool(_ex), "score": float(msims[k]), "en": m["mat_en"],'),
]
for a, b in REPL:
    assert a in s, f"找不到: {a[:40]}"
    s = s.replace(a, b, 1)

# 2) 门槛判定加 exact 旁路
old = """            if obj and obj["score"] > top_style and obj["score"] >= floors[name]:"""
new = """            if (obj and obj["score"] > top_style
                    and (obj.get("exact") or obj["score"] >= floors[name])):"""
assert old in s, "门槛判定行变了"
s = s.replace(old, new, 1)

# 3) 调试行标出精确命中
old2 = """        dbg = (f"最终: {name}分最高且过门槛 -> 只拼{name} "
                   f"({sc:.4f} > 风格 {top_style:.4f})\\n" + dbg)"""
new2 = """        dbg = (f"最终: {name}分最高{'（精确词命中）' if obj.get('exact') else ''}"
                   f" -> 只拼{name} ({sc:.4f} > 风格 {top_style:.4f})\\n" + dbg)"""
if old2 in s:
    s = s.replace(old2, new2, 1)
    print("  调试行已加精确标记")
else:
    print("  ⚠️ 调试行格式不同，跳过（不影响功能）")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  语法 OK")
