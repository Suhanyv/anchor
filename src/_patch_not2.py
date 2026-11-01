"""
补齐三处：
1. `_scene_risks` 自己遍历表，没走 _match_ref —— 所以 not 对它无效
2. 排除词补「停在」（"停在桥上"不等于"停着"）
3. 长椅要有自己的节拍：坐桌前写字 ≠ 坐公园长椅
"""
import ast
import json
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# 1) risks 也认 not
old = '''    for name, row in rows.items():
        if any(k in q for k in (row.get("kw") or [name])):
            rs = [r for r in (row.get("risk") or []) if r not in
                  [x for p in pools for x in p]]'''
new = '''    for name, row in rows.items():
        # not 对风险表同样有效：海上的雨不该带出「纸箱穿模」（实测）
        if any(w in q for w in (row.get("not") or [])):
            continue
        if any(k in q for k in (row.get("kw") or [name])):
            rs = [r for r in (row.get("risk") or []) if r not in
                  [x for p in pools for x in p]]'''
assert old in s, "risks 循环没匹配"
s = s.replace(old, new, 1)
ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  _scene_risks 支持 not")

RAW = r"F:\llm\data\raw"

# 2) 排除词补「停在」
for fn, key in (("sound_ref.json", "引擎"), ("risk_ref.json", "赛车")):
    p = f"{RAW}\\{fn}"
    d = json.load(open(p, encoding="utf-8"))
    ns = list(d[key].get("not") or [])
    for w in ("停在", "泊", "靠边"):
        if w not in ns:
            ns.append(w)
    d[key]["not"] = ns
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  引擎/赛车 排除词:", ns)

# 3) 坐·长椅
p = f"{RAW}\\beat_ref.json"
d = json.load(open(p, encoding="utf-8"))
d["坐·长椅"] = {
    "kw": ["长椅", "石阶", "台阶", "沙发", "床沿", "公园椅"],
    "mid": "上身微微前倾，手放在膝上或垂在两腿之间，脚踩着地面",
    "end": "停在这个姿势上，只有手上或脚边的动静",
}
# 从 坐·桌椅 里把这些词拿掉
d["坐·桌椅"]["kw"] = [w for w in d["坐·桌椅"]["kw"]
                       if w not in ("长椅", "石阶", "台阶", "沙发", "床沿")]
# 顺序：坐·桌椅 → 坐·长椅 → 坐
order = list(d.keys())
order.remove("坐·长椅")
i = order.index("坐·桌椅") + 1
order.insert(i, "坐·长椅")
d2 = {k: d[k] for k in order}
json.dump(d2, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  加了 坐·长椅，顺序:", [k for k in d2 if not k.startswith("_")][:8])

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
d3 = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d3["模型目录"][1]["default"], d3["语料文件"][1]["default"]
S, K, MT = (d3["题材文件"][1]["default"], d3["工艺文件"][1]["default"],
            d3["材质文件"][1]["default"])
for q in ("深夜，一辆出租车停在桥上", "海上，一艘渔船在暴风雨里",
          "一个老人坐在公园长椅上喂鸽子", "一个道士坐在桌前写字"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    snd = [x for x in out.split("。") if x.startswith("只使用")]
    rk = [x for x in out.split("。") if x.startswith("不要出现")]
    bt = [x for x in out.split("。") if x.startswith(("2 到", "3 到"))]
    print(f"\n  【{q[:16]}】")
    print("    声 " + (snd[0][:40] if snd else "?"))
    print("    险 " + (rk[0][:44] if rk else "?"))
    print("    节 " + (bt[0][:40] if bt else "?"))
