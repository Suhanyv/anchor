"""
把「画面材质」和「机位锁死」写进正文

① 媒介式风格：正文加一句「画面：整幅是水墨，宣纸纤维可见…」
② 机位锁死：实测那条视频自己切了三个镜头，
   「镜头极缓推近」太弱，要明确写「一镜到底，不切镜，机位不换」。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ① 在风格段之后插入画面材质句
old1 = '''    seg.append(f"{who}。")
    seg.append(f"0 到 {half} 秒，{who}，{move}。")'''
new1 = '''    seg.append(f"{who}。")
    # 媒介式风格：风格名对视频模型几乎无效，必须另给一句画面材质
    _med = c.get("medium_zh") or ""
    if _med:
        seg.append(f"{_med}。")
    seg.append(f"0 到 {half} 秒，{who}，{move}。")'''
assert old1 in s, "风格段没匹配"
s = s.replace(old1, new1, 1)

# ② 机位锁死：加进全局约束
old2 = '''    seg.append(f"{c['ar']}，全程保持主体清晰、背景自然虚化。")'''
new2 = '''    # 机位锁：实测那条视频自己切了三个镜头，「极缓推近」拦不住。
    _lock = ("一镜到底，不切镜，机位不换位置" if c.get("motion") in ("STATIC", "SLOW")
             else "只有一种运动，不追加第二个机位")
    seg.append(f"{c['ar']}，{_lock}，全程保持主体清晰、背景自然虚化。")'''
assert old2 in s, "全局约束没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已改：画面材质 + 机位锁")
