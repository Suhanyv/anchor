"""
③ 风格标签退出技术表的匹配

现象：「雪天，一个猎人蹲在树后」拿到升降镜头，
因为检索到的风格是程小东，他的标签里有「下降」，
而运镜表拿风格标签去匹配了。

规则：**风格是作者，不是画面的指令。** 技术表只认查询原话。
（光的匹配暂时保留 kw——那是早期设计，改它会牵动太多，
但运镜、景别、构图、角度、色调、光学、镜头、剪辑这些新表一律只认原话。）
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '_mv = _match_ref("motion_ref.json", query, c.get("kw") or [])'
new = ('# 运镜只认查询原话：风格标签里可能有「下降」这种词，\n'
       '    # 会把"蹲着"变成一个升降镜头（实测）。\n'
       '    _mv = _match_ref("motion_ref.json", query, [])')
assert old in s, "运镜那行没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已改：运镜不再接受风格标签")
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])
out, _ = N.LocalStyleHint().run(
    "雪天，一个猎人蹲在树后", M, C, S, K, MT, True, "文生视频", False,
    "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
print("  " + out[:130])
