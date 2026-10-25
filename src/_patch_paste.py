"""
多镜头补“可直接粘贴”版：N 个完整提示词，每段自带共用块

问题
----
逐镜单独问工具时，每镜各自检索风格：
    镜头1 -> 影像论文、文字拼贴
    镜头2 -> 火柴盒贴画
    镜头3 -> 军阵、黄昏、尘土
**三次生成三种美术风格，剪不到一起。**

共用块能防这个，但前提是用户真的把共用块贴进每一镜。
所以多镜头模式该直接给出**每一镜都能单独粘的完整提示词**，
而不是只给三行摘要让人自己去拼。

输出结构
--------
    【规划】共用块 + 逐镜一行 + 时长          <- 看全局
    【可直接粘贴】镜头 1 / 2 / 3 的完整提示词  <- 拿去生成
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''    out.append("")
    out.append("（共用块只写一次：逐镜重复风格会让各次生成色调不一致，剪不到一起。）")
    return "\\n".join(out)'''
new = '''    out.append("")
    out.append("（上面是规划。下面每一镜都是完整可粘的——"
               "因为即梦一次只出一镜，共用块必须贴进每一段。）")
    out.append("")
    out.append("━━━ 可直接粘贴 ━━━")
    out.append("")
    _look = "；".join([x for x in (light, style) if x]) or "<风格与光线>"
    _cine = _cine_line(c).split("\\n")[0]
    for i, sh in enumerate(shots, 1):
        _sec, _kind = _pers[i - 1]
        body = sh.strip() or "<写这一镜的动作>"
        a = max(1, _sec // 3)
        b = max(a + 1, _sec * 2 // 3)
        out.append(f"—— 镜头 {i} · {_sec} 秒 ——")
        out.append(f"{_look}。{ar}。")
        out.append("")
        out.append(f"0–{a} 秒：{body}，动作从这里开始，机位一动不用。")
        out.append(f"{a}–{b} 秒：<写这一步怎么继续；有变化就写清从什么变成什么>。")
        out.append(f"{b}–{_sec} 秒：<收束，停在什么画面上>。")
        out.append("")
        out.append(f"{_cine}")
        out.append("只使用<环境声>，不要配乐，不要字幕。")
        out.append("不要出现：<2-4 个会让这条废掉的错误>。")
        out.append("")
    return "\\n".join(out)'''
assert old in s, "多镜头结尾处没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加「可直接粘贴」版")
