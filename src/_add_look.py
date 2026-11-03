"""
合成「视觉方向」：没有作者风格时，用已命中的部件拼一句

只在一个格式里试（即梦整段式），不动其他模板。
写法要求：
  · 只用已经算出来的值（光 / 调色 / 焦段 / 质感），不编新东西
  · 明确标注"未指定作者风格"，不假装是导演
"""
import ast
import re
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ① 把 _cine_line 的选择逻辑抽成 _cine_parts（不改行为）
old_head = '''def _cine_line(c):
    """摄影层：主选一个值写进正文，备选另起一行。"""
    tags = " ".join(c.get("tags") or []).lower()'''
new_head = '''def _cine_parts(c):
    """只算值不排版：返回 {dof, tex, grade, mood, lens}。

    抽出来是为了让「视觉方向」能复用同一套选择逻辑，
    避免两处各算一套（以前焦段就是这样写岔的）。
    """
    tags = " ".join(c.get("tags") or []).lower()'''
assert old_head in s, "_cine_line 头没匹配"
s = s.replace(old_head, new_head, 1)

old_tail = '''    primary = f"摄影层：{dof}；{tex}；{grade}；{mood}；{lens}。"
    alts = ("备选（换一个即可）：" +
            " / ".join([_CINE["dof"][2], _CINE["tex"][2], _CINE["grade"][1],
                        _CINE["mood"][5], _CINE["lens"][0]]) + "。")
    return primary + "\\n" + alts'''
new_tail = '''    return {"dof": dof, "tex": tex, "grade": grade, "mood": mood, "lens": lens}


def _cine_line(c):
    """摄影层：主选一个值写进正文，备选另起一行。"""
    p = _cine_parts(c)
    primary = (f"摄影层：{p['dof']}；{p['tex']}；{p['grade']}；"
               f"{p['mood']}；{p['lens']}。")
    alts = ("备选（换一个即可）：" +
            " / ".join([_CINE["dof"][2], _CINE["tex"][2], _CINE["grade"][1],
                        _CINE["mood"][5], _CINE["lens"][0]]) + "。")
    return primary + "\\n" + alts'''
assert old_tail in s, "_cine_line 尾没匹配"
s = s.replace(old_tail, new_tail, 1)

# ② 即梦整段式：没有可信风格时，插一句「视觉方向」
old_p = '''    light = c["zh_light"] or c.get("light_default", "自然光")
    style = c["zh_style"] or ""'''
new_p = '''    light = c["zh_light"] or c.get("light_default", "自然光")
    style = c["zh_style"] or ""
    # 没有可信的作者风格时，用已命中的部件拼一个"视觉方向"。
    # 标明"未指定作者风格"——不假装是某个导演。
    _look = ""
    if not style or style.startswith("<风格"):
        _pk = _cine_parts(c)
        _bits = [x for x in (light, _pk["grade"], _pk["lens"], _pk["tex"]) if x]
        if _bits:
            _look = "视觉方向：" + "；".join(_bits[:4]) + "（未指定作者风格，按场景推）"'''
assert old_p in s, "prose 光/风格处没匹配"
s = s.replace(old_p, new_p, 1)

# ③ 放进正文：风格之后
old_a = '''    seg = [f"{light}。"] if light else []
    if style:
        seg.append(f"{style}。")'''
new_a = '''    seg = [f"{light}。"] if light else []
    if style:
        seg.append(f"{style}。")
    elif _look:
        seg.append(f"{_look}。")'''
assert old_a in s, "prose 拼接处没匹配"
s = s.replace(old_a, new_a, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  已加视觉方向（只在即梦整段式）")

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])
for q in ("一个人坐在窗前", "一个女人在菜市场挑鱼", "雨里，一个女孩抱着纸箱跑"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    print(f"\n  【{q}】")
    print("   " + out[:120])
