"""
① + ②：条目可以声明「我不适用于哪些词」（not 字段）

实测三个错位：
    出租车「停着」→ 给了侧滑/尾尘（行驶风险）
    海上渔船      → 给了"雨打在铁皮上、车流压过路面"（城市雨声）和"纸箱穿模"
    坐「长椅」    → 给了"手撑住地面"（坐地上）

做法：匹配时先看 not，命中就跳过这条，继续找下一条。
"""
import ast
import json
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''    for name, row in table.items():
        for k in (row.get("kw") or [name]):
            if k and k in q:
                return row'''
new = '''    for name, row in table.items():
        # not：这一条不适用于哪些语境。命中就跳过，继续找下一条。
        # 实测：出租车「停着」不该拿到侧滑和尾尘；海上的雨不是街道的雨。
        if any(w in q for w in (row.get("not") or [])):
            continue
        for k in (row.get("kw") or [name]):
            if k and k in q:
                return row'''
assert old in s, "_match_ref 主循环没匹配"
s = s.replace(old, new, 1)
ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  _match_ref 支持 not 字段")

RAW = r"F:\llm\data\raw"


def patch(fn, key, nots):
    p = f"{RAW}\\{fn}"
    d = json.load(open(p, encoding="utf-8"))
    if key not in d:
        print(f"  ✗ {fn} 里没有 {key}")
        return
    d[key]["not"] = nots
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  {fn} · {key} -> not {nots}")


# 行驶类：停着就不适用
patch("sound_ref.json", "引擎", ["停着", "停下", "停靠", "泊车", "熄火"])
patch("risk_ref.json", "赛车", ["停着", "停下", "停靠", "泊车", "熄火"])
# 城市雨：海上/船上不适用
patch("sound_ref.json", "雨", ["海上", "船上", "渔船", "海面", "甲板"])
patch("risk_ref.json", "雨", ["海上", "船上", "渔船", "海面", "甲板"])
# 空气：海上不该说"地面"
patch("atmosphere_ref.json", "雨", ["海上", "船上", "渔船", "甲板"])

# 坐·桌椅补充"长椅 / 椅 / 石阶"
p = f"{RAW}\\beat_ref.json"
d = json.load(open(p, encoding="utf-8"))
kw = list(d["坐·桌椅"]["kw"])
for w in ("长椅", "椅子", "石阶", "台阶", "沙发", "床沿"):
    if w not in kw:
        kw.append(w)
d["坐·桌椅"]["kw"] = kw
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  坐·桌椅 kw:", kw)
