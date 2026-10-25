"""
两处改进：
1) 参考表补词（收/退/合 等常见动作）
2) 多镜头改成**逐镜分配时长**，不再取最大值

为什么逐镜分配
--------------
原来三镜都按"最长的那一镜"给时长 = 3 镜各 5 秒。但：

    镜头一 站着，手按剑柄      3 秒够了
    镜头二 劈下 + 格挡 + 推开   5 秒
    镜头三 收剑 + 身影退开      4 秒

**三镜内容不一样，时长就该不一样。** 统一给 5 秒等于让静态镜头浪费 2 秒，
而那 2 秒模型会自己加戏。

用户要的是"自行检测并划分时间"——那就得**一镜一个数**。
"""
import ast
import json
import os
import sys

# ---- 1) 参考表补词 ----
REF = r"F:\llm\data\raw\duration_ref.json"
with open(REF, encoding="utf-8") as f:
    ref = json.load(f)
add = {"action": ["收", "退", "合", "转", "走到", "停在", "叩", "握住"],
       "strong": ["抽", "甩", "掷", "翻", "跨"],
       "micro": ["点头", "摇头", "皱眉", "垂下", "抬起"]}
for cls, words in add.items():
    cur = ref["classes"][cls]["words"]
    for w in words:
        if w not in cur:
            cur.append(w)
with open(REF, "w", encoding="utf-8") as f:
    json.dump(ref, f, ensure_ascii=False, indent=2)
print("  参考表已补词")

# ---- 2) 多镜头逐镜分配 ----
P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''    # 每镜时长按各镜自己的内容估，取最大 —— 逐镜生成时它们互不相干
    _per = max([_plan_duration(fmt, s)[1] for s in shots if s] or
               [_plan_duration(fmt, " ".join(shots))[1]])
    _t, _n, _dline = 0, 0, ""
    if True:
        _mx, _safe, _src, _mn = _limit_of(fmt)
        _n = len(shots)
        _per = max(_mn, min(_per, _mx))
        _t = _per * _n
        _dline = (f"【时长】每镜 {_per} 秒 x {_n} 镜 = {_t}s。"
                  f"（{fmt or '通用'} 上限 {_mx}s / 最短 {_mn}s）")'''
new = '''    # 逐镜分配时长：每镜按自己的运动幅度算，不是一刀切
    _mx, _safe, _src, _mn = _limit_of(fmt)
    _pers = []
    for _sh in shots:
        _sec, _kind = _ref_duration(_sh) if _sh else (4, "空槽")
        _pers.append((max(_mn, min(int(_sec), _mx)), _kind))
    _t = sum(p for p, _ in _pers)
    _dline = (f"【时长】逐镜分配，合计 {_t}s。"
              f"（{fmt or '通用'} 上限 {_mx}s / 最短 {_mn}s；按运动幅度分配，"
              f"静态给 3 秒、强动作给 5 秒、变形给 6 秒）")'''
assert old in s, "多镜头时长块没匹配"
s = s.replace(old, new, 1)

# 逐镜行带上各自时长
old2 = '''    for i, sh in enumerate(shots, 1):
        body = sh.strip() or "<写这一镜的动作：只有 1-2 个动作，写清从什么变成什么>"
        out.append(f"【镜头 {i}】{body}")'''
new2 = '''    for i, sh in enumerate(shots, 1):
        body = sh.strip() or "<写这一镜的动作：只有 1-2 个动作，写清从什么变成什么>"
        _sec, _kind = _pers[i - 1]
        out.append(f"【镜头 {i}】（{_sec} 秒 · {_kind}）{body}")'''
assert old2 in s, "逐镜行没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已改为逐镜分配")
for q in ("骑士站在石地中央，手按剑柄", "一个对手入画劈下，他横剑格挡",
          "他收剑，前景虚焦身影退开", "竹简慢慢变成全息册子"):
    print(f"    {q[:20]:<22} -> {N._ref_duration(q)}")
