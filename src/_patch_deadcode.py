"""清掉死代码：_shot_for_beat 定义了但从来没被调用"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

start = s.find("def _shot_for_beat(name, used=None):")
if start >= 0:
    end = s.find("\n\n\ndef ", start)
    if end < 0:
        end = s.find("\n\n", start)
    dead = s[start:end + 1]
    s = s[:start] + s[end + 1:]
    ast.parse(s)
    open(P, "w", encoding="utf-8").write(s)
    print(f"  删掉 _shot_for_beat（{len(dead.splitlines())} 行，从未被调用）")
else:
    print("  已经不在了")

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _shot_for_beat 还在吗:", hasattr(N, "_shot_for_beat"))
print("  剪点表", len(N._load_ref("edit_ref.json")), "条")
