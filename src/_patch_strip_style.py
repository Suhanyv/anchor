"""
点名风格时，"用X"这句话要从句子里剔掉

现象
----
查询「用皮影，一个人拿起桌上的竹简，变成全息册子」
输出：「皮影：皮影、剪影、透光。用皮影，一个人拿起桌上的竹简…」

**"用皮影"原样留在正文里。** 对模型来说这是画面上的字，不是指令。

改法
----
`_strip_cmd` 已经在剥"用…做/生成"这类指令词，但"用皮影"里的"皮影"是风格名，
不在指令词表里，所以整句留下了。

这里补一步：点名风格之后，把"用<那个名字>"从主体文本里去掉。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_strip_style_mention" not in s:
    fn = '''def _strip_style_mention(q, item):
    """把"用<风格名>"这类点名从文本里去掉（风格已经体现在别处了）。"""
    import re
    t = q or ""
    for key in ("director_zh", "director"):
        nm = str((item or {}).get(key) or "").strip()
        if len(nm) >= 2:
            t = re.sub(r"用?\\s*" + re.escape(nm) + r"\\s*(那种|式|风格)?\\s*[，,、]?\\s*", "", t)
    return t.strip(" ，,、") or (q or "")


'''
    anchor = "def _core(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# subject_zh 用剥过的
old = '''        "subject_zh": _strip_cmd(query),'''
new = '''        "subject_zh": _strip_style_mention(_strip_cmd(query), item),'''
assert old in s, "subject_zh 行没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加 _strip_style_mention")
for q, nm in (("用皮影，一个人拿起桌上的竹简", {"director_zh": "皮影"}),
              ("布列松那种静默，两个人拥抱", {"director_zh": "布列松"}),
              ("一个人拿起桌上的竹简", {"director_zh": "皮影"})):
    print(f"    {q[:20]:<22} -> {N._strip_style_mention(q, nm)}")
