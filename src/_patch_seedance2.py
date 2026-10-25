"""
修即梦格式两处：时间轴第二段太泛、缺 negative 列表

问题
----
"一个骑士手握长剑" 实测输出：

    0–2 秒：…缓慢推近。
    2–5 秒：镜头轻微跟随；缓慢地移动或变化，幅度很小，速度恒定；画面在这里发生一次变化…

第二段是**通用废话**，没有推进任何动作。用户还得自己重写。
而且整个格式没有「不要出现」这一栏——对这个镜头来说，
"不要出现清晰的多张人脸"比任何正面描述都重要。

改法
----
1. 第二段改成明确的填空提示：动作怎么继续或停下、要变形写清从什么变成什么
2. 全局约束末尾加一行「不要出现」，列为可填空位
   （仍属于官方的「全局约束」段，不新增段落）
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''    lines.append(f"0–{half} 秒：<景别>。{who}，{light}，{move}。")
    lines.append(f"{half}–{dur} 秒：镜头{ ('轻微跟随' if c['motion'] != 'STATIC' else '保持不动') }；"
                 f"{act}；画面在这里发生一次变化，其余保持不变。")
    lines.append("")'''
new = '''    lines.append(f"0–{half} 秒：<景别>。{who}，{light}，{move}。")
    # 第二段不要写"缓慢地移动"这种通用句，改成明确的填空提示：
    # 通用句会让用户以为已经写完了，其实动作一点没推进。
    lines.append(f"{half}–{dur} 秒：<写：上一段的动作怎么继续或停下；"
                 f"要变形就写清从什么变成什么>。")
    lines.append("")'''
assert old in s, "即梦时间轴段变了"
s = s.replace(old, new, 1)

old2 = '''    lines.append(f"全程保持主体清晰、背景自然虚化；{c['ar']}；"
                 f"{'轻微手持呼吸感' if c['motion'] != 'STATIC' else '机位完全固定'}；"
                 f"只使用<环境声>，不要配乐，不要字幕。")'''
new2 = '''    lines.append(f"全程保持主体清晰、背景自然虚化；{c['ar']}；"
                 f"{'轻微手持呼吸感' if c['motion'] != 'STATIC' else '机位完全固定'}；"
                 f"只使用<环境声>，不要配乐，不要字幕。")
    # negative 并入全局约束：这是这一格最容易被忽略、又最影响成败的部分
    lines.append("不要出现：<写 2-4 个真正会让这条废掉的错误，"
                 "例如多余的人、手部畸形、兵器穿模、血迹>。")'''
assert old2 in s, "即梦全局约束段变了"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  即梦格式已修 2 处")
