"""
把数量接进主体：两个武士 -> two samurai in layered armour

只改"前面加不加数量"，不改短语本身。
"""
import ast
import json
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_quantity_of" not in s:
    fn = '''def _quantity_of(query):
    """查询里的数量词 -> (中文前缀, 英文前缀)。单数返回 ("", "")。"""
    q = query or ""
    table = _load_ref("quantity_ref.json")
    # 长的先匹配（"一群群" 优先于 "一群"）
    for k in sorted(table, key=len, reverse=True):
        if k and k in q:
            row = table[k]
            return str(row.get("zh") or ""), str(row.get("en") or "")
    return "", ""


def _apply_quantity(phrase, en_prefix):
    """把英文数量拼到短语前，去掉原来的冠词。"""
    if not phrase or not en_prefix:
        return phrase
    for art in ("a ", "an ", "the "):
        if phrase.lower().startswith(art):
            phrase = phrase[len(art):]
            break
    return f"{en_prefix} {phrase}"


'''
    anchor = "def _quantity_of(" if False else "def _named_index_terms(query):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 在 _core 里应用
old = '''    # 图生视频：外观已在首帧里。清空 kw（影响 zh_style）——'''
new = '''    # 数量：两个武士 != 一个武士，构图与景别全变
    _qzh, _qen = _quantity_of(query)
    if _qen and subj:
        subj = dict(subj)
        subj["phrase"] = _apply_quantity(subj.get("phrase") or "", _qen)
    if _qzh and subj:
        subj = dict(subj)
        subj["zh"] = _qzh + str(subj.get("zh") or "")

    # 图生视频：外观已在首帧里。清空 kw（影响 zh_style）——'''
assert old in s, "_core \u63d2\u5165\u70b9\u6ca1\u5339\u914d"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _quantity_of:", hasattr(N, "_quantity_of"))
for q in ("两个武士在雪地对决", "一群记者围住一个人", "三个机器人在草地上", "一个男孩站着"):
    print(f"  {q[:14]:<16} -> {N._quantity_of(q)}")
