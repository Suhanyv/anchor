"""
精确词命中：从「按长度」改成「按黑名单」

问题
----
为了让 `柔光` `颗粒` `霓虹` 这类**泛用词**不误触发，我把精确命中的门槛设成
"关键词长度 >= 3"。副作用是 `黑子`（2 字）这种**准确的名词**也被挡了：

    "我想要在太空中，拍摄太阳的黑子"  ->  太阳黑子进不来，扩库前后输出一模一样

长度不是"是否具体"的判据。`黑子` 比 `柔光` 具体得多。

改法
----
允许 2 字关键词命中，但排除一张**泛用词黑名单**（形容词/泛指光效）。
黑名单只收真正造成过误触发的词，不预先把所有形容词都塞进去——
那样又会把 `冰` `雪` `雾` 这类正确的短名词误杀。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''def _exact_hits(query, rows, min_len=3):'''
new = '''# 泛用词黑名单：这些 2 字词出现在查询里不代表"点名了某个条目"
_EXACT_STOP = {
    "柔光", "硬光", "颗粒", "霓虹", "光斑", "高光", "反光", "阴影", "暗角",
    "色彩", "色调", "质感", "氛围", "情绪", "风格", "画面", "镜头", "构图",
}


def _exact_hits(query, rows, min_len=2):'''
assert old in s, "_exact_hits 签名变了"
s = s.replace(old, new, 1)

# 长度判定改为：2 字词必须在黑名单外
old2 = '''            if len(kw) >= min_len and kw in query and len(kw) > best:'''
new2 = '''            if (len(kw) >= min_len and kw in query and len(kw) > best
                    and not (len(kw) == 2 and kw in _EXACT_STOP)):'''
assert old2 in s, "命中判定行变了"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  黑名单", len(N._EXACT_STOP), "词；min_len=2")
