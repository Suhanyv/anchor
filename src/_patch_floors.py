"""
按标定结果重设门槛：全部上调到 0.52（场景 0.43）

标定数据（bench/floor_calibration.json）
----------------------------------------
    通道      正样本中位  正样本最低  负样本最高
    subject    0.566      0.397      0.498
    craft      0.571      0.359      0.505
    material   0.617      0.522      0.473
    scene      0.632      0.433      0.376

正负样本确实重叠，单一门槛分不干净。但两种错误代价不对称：

    漏掉  -> 输出占位符 + 低置信警告，用户自己补  （安全）
    误判  -> 往提示词里塞进不相干的内容            （有害）

所以选高门槛：守 0.52，放弃 4-6 个弱正样本，换掉 0 个误判。

顺带修掉的真实 bug
------------------
"混乱，失序" 这种纯风格描述，工艺分 0.505 —— 在旧门槛 0.44 上会命中，
于是输出里会冒出一个不相干的工艺。这是真的会把提示词写坏。
"""
import ast
import json
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

PAIRS = [
    ("SUBJECT_FLOOR = 0.36", "SUBJECT_FLOOR = 0.52"),
    ("CRAFT_FLOOR = 0.44", "CRAFT_FLOOR = 0.52"),
    ("MAT_FLOOR = 0.40", "MAT_FLOOR = 0.52"),
    ("SCENE_FLOOR = 0.36", "SCENE_FLOOR = 0.43"),
]
for a, b in PAIRS:
    assert a in s, f"找不到 {a}"
    s = s.replace(a, b, 1)
    print(f"  {a}  ->  {b.split('= ')[1]}")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("\n  当前门槛：")
for k in ("SUBJECT_FLOOR", "CRAFT_FLOOR", "MAT_FLOOR", "SCENE_FLOOR",
          "SUBJECT_TIE_MARGIN"):
    print(f"    {k} = {getattr(N, k)}")
