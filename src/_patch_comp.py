"""接构图表：点名就写一句「构图：…」"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old1 = '        "shot": _match_shot(query),'
new1 = ('        "shot": _match_shot(query),\n'
        '        # 构图：原来完全空着的一维\n'
        '        "comp_zh": ((_match_ref("composition_ref.json", query, kw) or {})\n'
        '                    .get("zh", "")),')
assert old1 in s and '"comp_zh"' not in s, "core 插入点异常"
s = s.replace(old1, new1, 1)

old2 = '''    _shot = c.get("shot") or {}
    if _shot.get("zh"):'''
new2 = '''    _comp = c.get("comp_zh") or ""
    if _comp:
        seg.append(f"{_comp}。")
    _shot = c.get("shot") or {}
    if _shot.get("zh"):'''
assert old2 in s, "正文插入点没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已接构图")
for q in ("对称构图，一个道士站在院子里", "一个女孩跑", "留白，雪原上一个人"):
    r = N._match_ref("composition_ref.json", q, [])
    print(f"  {q[:16]:<18} -> {(r or {}).get('zh','(未命中)')[:30]}")
