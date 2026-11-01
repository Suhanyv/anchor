"""
加「时代混搭提示」

赛博朋克 + 道士僵尸 = 科技道术，是成立的混搭，不该拦。
但工具应该注意到，并说一声——这样你知道它不是没看见。

只写进调试块，不进正文：正文里说"你混了两个年代"是废话。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

FN = '''_MODERN_LOOKS = ("赛博朋克", "科技黑色", "蒸汽波", "反乌托邦", "梦核", "伪纪录")
_PERIOD_WORDS = ("道士", "僵尸", "符", "竹简", "甲", "剑", "江湖", "武侠",
                 "官服", "书案", "马车", "灯笼", "寺院")


def _mashup_note(query, subj):
    """类型片和主体不在同一个年代时给一句提示。不改内容，只提醒。"""
    q = query or ""
    _gl = _match_ref("genre_look_ref.json", q, []) or {}
    gz = _gl.get("zh") or ""
    if not any(m in gz for m in _MODERN_LOOKS):
        return ""
    if any(w in q for w in _PERIOD_WORDS):
        return "时代混搭：类型片偏现代，主体偏古装——成立的话（科技道术）可以留，"
        return "不成立就换一个类型片"
    return ""


'''
anchor = "def _match_shot_name(query):"
assert anchor in s, "插入点没找到"
if "def _mashup_note" not in s:
    s = s.replace(anchor, FN + anchor, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  已加 _mashup_note")
