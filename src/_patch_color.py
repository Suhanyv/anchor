"""
调色改由色表决定，不再用写死的候选

以前 `_cine_line` 里只有三档：青橙 / 自然色 / 暖金。
现在 15 档，并且命中时会把「色调：…」写进正文。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ① core 里带色调
old1 = '        "angle_zh": ((_match_ref("camera_angle_ref.json", query, []) or {})\n                     .get("zh", "")),'
new1 = (old1 + '\n'
        '        # 色调：命中就给 short 填进摄影层，desc 另起一句\n'
        '        "color_row": (_match_ref("color_ref.json", query, []) or {}),')
assert old1 in s and '"color_row"' not in s, "core 插入点异常"
s = s.replace(old1, new1, 1)

# ② 摄影层：色表优先
old2 = '''    _glz = c.get("genrelook_zh") or ""'''
new2 = '''    # 色表优先：命中就用它，别再用写死的三档
    _cr = c.get("color_row") or {}
    if _cr.get("short"):
        grade = _cr["short"]
    _glz = c.get("genrelook_zh") or ""'''
assert old2 in s, "摄影层插入点没匹配"
s = s.replace(old2, new2, 1)

# ③ 正文：加一句色调描述
old3 = '''    # 机位角度：观众从哪个位置看
    _ag = c.get("angle_zh") or ""
    if _ag:
        seg.append(f"{_ag}。")'''
new3 = '''    # 机位角度：观众从哪个位置看
    _ag = c.get("angle_zh") or ""
    if _ag:
        seg.append(f"{_ag}。")
    # 色调：调色是一句完整的话，不只是摄影层里两个字的标签
    _cd = (c.get("color_row") or {}).get("desc") or ""
    if _cd:
        seg.append(f"{_cd}。")'''
assert old3 in s, "正文插入点没匹配"
s = s.replace(old3, new3, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  色表", len(N._load_ref("color_ref.json")), "条，已接入摄影层与正文")
for q in ("跳漂法，一个士兵在战壕里", "黑白，一个人站着", "一个女孩在雨里跑"):
    r = N._match_ref("color_ref.json", q, [])
    print(f"  {q[:16]:<18} -> {(r or {}).get('short','(未命中)')}")
