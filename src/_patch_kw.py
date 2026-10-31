"""
新四张表不再接收风格关键词

实测：「一个女孩在雨里跑」被判成群像镜头，因为风格检索到黑泽明，
而他的关键词里有「群像」——**风格的标签把景别拽了进来**。
构图表同理（"动态构图"这种标签会误触发）。

查询原话点名才算。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

TABLES = ("composition_ref.json", "face_light_ref.json",
          "genre_look_ref.json", "shot_size_ref.json")
n = 0
for t in TABLES:
    old = f'_match_ref("{t}", query, kw)'
    new = f'_match_ref("{t}", query, [])'
    if old in s:
        n += s.count(old)
        s = s.replace(old, new)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print(f"  改了 {n} 处")

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
rows = N._load_ref("shot_size_ref.json")
r = N._match_ref("shot_size_ref.json", "一个女孩在雨里跑", ["群像", "雨"])
print("  带风格关键词也不再命中:", (r or {}).get("zh", "(未命中)")[:18])
r2 = N._match_ref("shot_size_ref.json", "大特写，一只手", [])
print("  查询自己点名仍然命中:", (r2 or {}).get("zh", "")[:18])
