"""
修：镜头类型名被 _strip_cmd 吃掉一个字

现象：「背面跟拍一个女孩…」输出成「背面跟 女孩…」，
因为"跟拍"里的字被当真成了指令词。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''        "subject_zh": _szh,'''
new = '''        "subject_zh": _szh,'''
assert old in s

# 在 _core 里：点名了镜头类型时，用它替换掉被剥伤的正文
old2 = '''    if _sec.get("phrase") and subject_phrase:'''
new2 = '''    # 镜头类型被点名时，正文里那个被剥伤的名字（"背面跟"）要恢复成本来的说法
    _shotn = _match_shot_name(query)
    if _shotn:
        _szh = _szh.replace(_shotn[1], _shotn[0])
    if _sec.get("phrase") and subject_phrase:'''
assert old2 in s, "插入点没匹配"
s = s.replace(old2, new2, 1)

if "_match_shot_name" not in s:
    fn = '''def _match_shot_name(query):
    """返回 (完整名, 被剥伤的残留) —— 用来把正文修回来。"""
    rows = _load_ref("shot_ref.json")
    q = query or ""
    for name, row in rows.items():
        for k in (row.get("kw") or [name]):
            if k and k in q:
                # 被剥伤的样子：k 去掉一个字
                for i in range(len(k)):
                    broken = k[:i] + k[i + 1:]
                    if len(broken) >= 2 and broken in q:
                        return k, broken
                return k, k
    return "", ""


'''
    anchor = "def _match_shot(query):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加 _match_shot_name")
for q in ("雨里，背面跟拍一个女孩抱着纸箱跑", "只拍脚下的水花"):
    print("   ", q[:16], "->", N._match_shot_name(q))
