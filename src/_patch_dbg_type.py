"""调试行补 type：主体那一行要能看出是「场景」还是「物件」

起因：写测试脚本时无法从调试信息判断命中的是场景还是物件，
导致判读逻辑只能靠猜，最后写出了「期望实得一样却标 ❌」的错。

顺带对人也有用：一眼看出这条走的是场景通道还是主体通道。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = """        dbg = (f"主体: {subj['zh']} {subj['score']:.4f} (下限{SUBJECT_FLOOR}) \""""
assert old in s, "主体调试行变了"

new = """        _t = "场景" if subj.get("type") == "scene" else "物件"
        dbg = (f"主体[{_t}]: {subj['zh']} {subj['score']:.4f} (下限{SUBJECT_FLOOR}) \""""
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加 type 标记")
