"""
来源标注从正文移到调试信息

用户的意见：提示词里不要再输出"【库】""【编】"这类标注。

对——那些字会混进提示词，粘贴到平台就成了画面内容的一部分
（模型会把"【编】"当成要画的东西）。

改法：
    正文   干净，只有画面描述
    调试   【来源】逐镜列出 库=什么 / 编=什么
    （来源标注本身仍然保留，只是放对位置）
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# 1) 逐镜行不再带标签
old = '''        _tags = (globals().get('_PROP_TAGS') or [])
        _tag = f"  {_tags[i-1]}" if i - 1 < len(_tags) else ""
        out.append(f"【镜头 {i}】（{_sec} 秒 · {_kind}）{body}{_tag}")'''
new = '''        out.append(f"【镜头 {i}】（{_sec} 秒 · {_kind}）{body}")'''
assert old in s, "逐镜行没匹配"
s = s.replace(old, new, 1)

# 2) 多镜头分支把来源写进 dbg
old2 = '''            dbg = f"【多镜头】{_tag}（平台 {_pf}）\\n" + dbg
            return (_ms, dbg)'''
new2 = '''            dbg = f"【多镜头】{_tag}（平台 {_pf}）\\n" + dbg
            # 来源只进调试，不进正文（正文里的"【编】"会被模型画出来）
            _tg = globals().get("_PROP_TAGS") or []
            if _tg:
                _lines = "\\n".join(
                    f"  镜头{i+1}  {t}" for i, t in enumerate(_tg))
                dbg = f"【来源】\\n{_lines}\\n" + dbg
                globals()["_PROP_TAGS"] = []   # 用完清掉，避免串到下一次
            return (_ms, dbg)'''
assert old2 in s, "多镜头返回处没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已把来源移到调试信息")
