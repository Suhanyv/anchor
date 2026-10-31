"""
加 shot_size_auto：两个主体时自动补「两人镜头」

为什么：昨天加了第二主体（道士 + 僵尸），但两方仍然各写各的。
一个画面里同时有两个人，才看得出他们之间的关系——距离、平衡、谁在躲。
这是唯一一处"没人点名也主动补"的地方，所以写清依据。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

FN = '''def shot_size_auto(subj, query):
    """两个主体同框时补一句两人镜头。认不出第二个人就返回空。"""
    if not ((subj or {}).get("second") or {}).get("zh"):
        return ""
    row = _load_ref("shot_size_ref.json").get("两人镜头") or {}
    return row.get("zh", "")


'''
anchor = "def _match_shot_name(query):"
assert anchor in s, "插入点没找到"
if "def shot_size_auto" not in s:
    s = s.replace(anchor, FN + anchor, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  shot_size_auto:", hasattr(N, "shot_size_auto"))
print("  表里", len(N._load_ref("shot_size_ref.json")), "种景别")
