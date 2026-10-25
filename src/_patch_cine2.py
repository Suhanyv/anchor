"""
摄影层 v2：主选一个值，备选放到括号里

问题
----
v1 输出的是菜单：
    景深：浅景深（背景化开） / 中景深（环境可读）；质感：35mm 胶片颗粒 / 干净的数码质感

用户还是得自己挑。**"内容不够"的意思是要能直接粘，不是要多一个选择题。**

改法
----
正面写**一个**具体值（可直接粘），备选另起一行加「备选：」前缀。
这样正文可用，想换也有得换。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old_start = s.index("def _cine_line(c):")
old_end = s.index("def _fmt_multishot(")
new_fn = '''def _cine_line(c):
    """摄影层：主选一个值写进正文，备选另起一行。"""
    tags = " ".join(c.get("tags") or []).lower()
    kw = " ".join(c.get("kw") or "")

    def has(words):
        return any(w in tags or w in kw for w in words)

    # 主选：能从风格关键词推的就推，推不出用第一个候选
    dof = _CINE["dof"][0] if has(("close", "特写", "浅景深", "肖像")) else _CINE["dof"][1]
    tex = _CINE["tex"][0] if has(("grain", "颗粒", "film", "胶片", "旧")) else _CINE["tex"][1]
    grade = (_CINE["grade"][0] if has(("neon", "霓虹", "青橙", "teal", "cyan", "赛博"))
             else _CINE["grade"][5] if has(("natural", "自然", "纪实", "doc"))
             else _CINE["grade"][2])
    mood = _CINE["mood"][0] if has(("lonely", "孤独", "压抑", "melancholy", "冰冷")) else _CINE["mood"][3]
    lens = _CINE["lens"][2] if has(("close", "特写", "肖像", "脸")) else _CINE["lens"][1]

    primary = f"摄影层：{dof}；{tex}；{grade}；{mood}；{lens}。"
    alts = ("备选（换一个即可）：" +
            " / ".join([_CINE["dof"][2], _CINE["tex"][2], _CINE["grade"][1],
                        _CINE["mood"][5], _CINE["lens"][0]]) + "。")
    return primary + "\\n" + alts


'''
s = s[:old_start] + new_fn + s[old_end:]

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
c = N._core({"score": 0.6, "director": "X", "director_zh": "X",
             "style_tags": ["neon", "cyan"], "kw_zh": ["霓虹", "夜景"],
             "description": "neon street", "style_string": "in the style of X",
             "params": {}, "motion": "SLOW"}, None, None, None, "prompt_video", "霓虹夜色")
print(N._cine_line(c))
