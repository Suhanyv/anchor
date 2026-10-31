"""
把镜头类型写进正文，并且按类型决定「能不能动」

关键：上次「一镜到底，不切镜，机位不换位置」把跟拍也禁掉了，
模型只好自己切。跟拍本来就该动——**锁定要跟镜头类型走，不是一刀切。**
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ① core 里带上镜头类型
old1 = '        "medium_zh": _entry_medium(item)[0],'
new1 = ('        "shot": _match_shot(query),\n'
        '        "medium_zh": _entry_medium(item)[0],')
assert old1 in s, "core 插入点没匹配"
s = s.replace(old1, new1, 1)

# ② 正文：点名了镜头类型就用它的机位描述
old2 = '''    seg.append(f"0 到 {half} 秒，{who}，{move}。")'''
new2 = '''    # 点名的镜头类型优先：它是机位的具体写法，比"推近/固定"细
    _shot = c.get("shot") or {}
    if _shot.get("zh"):
        seg.append(f"机位：{_shot['zh']}。")
        seg.append(f"0 到 {half} 秒，{who}，画面从这里开始。")
    else:
        seg.append(f"0 到 {half} 秒，{who}，{move}。")'''
assert old2 in s, "时间轴没匹配"
s = s.replace(old2, new2, 1)

# ③ 机位锁：跟拍允许动
old3 = '''    _lock = ("一镜到底，不切镜，机位不换位置" if c.get("motion") in ("STATIC", "SLOW")
             else "只有一种运动，不追加第二个机位")'''
new3 = '''    # 锁定要跟镜头类型走：跟拍本来就该动，一刀切会逼模型自己切镜（实测）
    _moves = bool((c.get("shot") or {}).get("allows_move")) or \\
        c.get("motion") not in ("STATIC", "SLOW")
    _lock = ("一镜到底，不切镜，只有一种运动，不追加第二个机位" if _moves
             else "一镜到底，不切镜，机位不换位置")'''
assert old3 in s, "机位锁没匹配"
s = s.replace(old3, new3, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已接：镜头类型 + 按类型解锁")
