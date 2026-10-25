"""
摄影层：补上「风格+色彩 / 情绪 / 技术」这三个空槽

依据
----
开源提示词库 `cinematic-video-prompt-skill`（Rylaispirit）的公式：

    [景别+角度], [主体+外观], [具体动作], [环境+天气],
    [光线], [运镜], [风格+色彩], [情绪], [技术]

我们原来只到「光线」就断了。后三项全空，而"技术"恰恰是
`shallow depth of field, 35mm film grain` 这类决定质感的词。

它还有几条规则值得照搬（其中一条印证了我们的共用块设计）：
    · 一段只写一种运镜
    · 一段只写一个主动作
    · 光线必须与天气/时间一致
    · 风格 / 色彩 / 情绪 三者必须指向同一个方向
    · **技术类关键词不超过 8 个**（写多了互相抵消）
    · 同一个故事里角色描述保持一致

设计决定：给建议值，不给空括号
------------------------------
空括号 `<焦段>` 用户还得自己想；给 `<35–50mm 或 85mm 浅景深>` 才是帮忙。
所以每个槽位都带 2–3 个候选值，按风格关键词优先填、填不上给建议。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_cine_line" not in s:
    fn = '''# 摄影层候选值：按"常见且有效"排序，给用户挑，不是让他从零想。
_CINE = {
    "dof": ("浅景深（背景化开）", "中景深（环境可读）", "深景深（全部清晰）"),
    "tex": ("35mm 胶片颗粒", "干净的数码质感", "轻微颗粒 + 低对比"),
    "grade": ("青橙对比", "冷青灰", "暖金", "低饱和", "单色调（红）", "自然色"),
    "mood": ("压抑", "疏离", "温柔", "紧绷", "空", "疲惫"),
    "lens": ("35mm 广角", "50mm 标准", "85mm 中焦", "135mm 长焦压缩"),
}


def _cine_line(c):
    """生成「摄影层」一行：给候选值，能按风格关键词推的就推。"""
    tags = " ".join(c.get("tags") or []).lower()
    kw = " ".join(c.get("kw") or [])

    def pick(key, hint_words, fallback_idx=0):
        for w in hint_words:
            if w in tags or w in kw:
                return _CINE[key][fallback_idx]
        return " / ".join(_CINE[key][:2])

    grade = pick("grade", ("neon", "霓虹", "青橙", "teal", "cyan"), 0)
    if not grade or grade not in _CINE["grade"]:
        grade = " / ".join(_CINE["grade"][:2])
    parts = [
        f"景深：{pick('dof', ('close', '特写', '浅景深'), 0)}",
        f"质感：{pick('tex', ('grain', '颗粒', 'film', '胶片'), 0)}",
        f"调色：{grade}",
        f"情绪：{pick('mood', ('lonely', '孤独', '压抑', 'melancholy'), 0)}",
        f"焦段：{pick('lens', ('close', '特写'), 2)}",
    ]
    return "摄影层（技术词不超过 8 个）：" + "；".join(parts) + "。"


'''
    anchor = "def _fmt_multishot(shots, item, subj, craft, mat, domain, fmt=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 挂进共用的中文格式：即梦 / 可灵 / MiniMax / 多镜头共用块
ANCHORS = [
    # 即梦：全局约束之后
    ('    # negative 并入全局约束：这是这一格最容易被忽略、又最影响成败的部分\n'
     '    lines.append("不要出现：<写 2-4 个真正会让这条废掉的错误，"',
     '    lines.append(_cine_line(c))\n'
     '    # negative 并入全局约束：这是这一格最容易被忽略、又最影响成败的部分\n'
     '    lines.append("不要出现：<写 2-4 个真正会让这条废掉的错误，"'),
    # MiniMax：不要出现之前
    ('        "不要出现：错字、元素变形、重复主体、水印、字幕。",\n    ])',
     '        _cine_line(c),\n        "不要出现：错字、元素变形、重复主体、水印、字幕。",\n    ])'),
    # 多镜头共用块
    ('        "        只使用<环境声>，不要配乐，不要字幕。",',
     '        "        " + _cine_line(c),\n        "        只使用<环境声>，不要配乐，不要字幕。",'),
]
for a, b in ANCHORS:
    if a in s:
        s = s.replace(a, b, 1)
        print("  已挂摄影层:", a.split("\n")[0][:44])
    else:
        print("  ⚠️ 未匹配:", a.split("\n")[0][:44])

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  摄影层:", hasattr(N, "_cine_line"))
