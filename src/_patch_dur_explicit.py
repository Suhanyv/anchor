"""
让时长能被直接指定

现在时长是按运动幅度算的（静态 3、动作 4、强动作 5、变形 6），
用户想要 10 秒、12 秒时没法表达。加一条：查询里写了「N 秒 / Ns」就用它，
平台上下限仍由 _plan_duration 卡。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''def _dur_from_query(query):
    """按运动幅度给这一镜的时长，返回 '5s' 这样的串；算不出就 None。'''
new = '''def _dur_from_query(query):
    """这一镜多长。先看用户有没有直接写秒数，再看运动幅度。

    用户写「10 秒的镜头」就该给 10 秒——以前这个数字被完全忽略，
    时长永远按运动幅度猜（静态 3、动作 4、强动作 5），想要长也表达不出来。
    平台上下限仍由 _plan_duration 卡。
    """
    _m = re.search(r"(\\d{1,2})\\s*(?:秒|s\\b|sec)", query or "", re.I)
    if _m:
        _n = int(_m.group(1))
        if 1 <= _n <= 60:
            return f"{max(3, min(_n, 30))}s"
'''
assert old in s, "时长函数没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已支持显式秒数")
for q in ("雨里，一个女孩抱着纸箱跑", "雨里，12 秒，一个女孩抱着纸箱跑",
          "做一段 8s 的镜头", "长镜头，20 秒"):
    print(f"  {q[:22]:<24} -> {N._dur_from_query(q)}")
