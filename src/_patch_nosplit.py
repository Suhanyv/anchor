"""
不再自动拆镜：超安全时长就给满 + 说明，拆不拆由人定

用户的意见
----------
"让他不再多分段输出，而是根据安全时长和内容输出"

我原来的逻辑：内容估出 15 秒 > MiniMax 安全 10 秒 -> 自动拆成 2 镜。
**那是我替用户做了剪辑决定。** 而剪辑决定不属于工具——工具不知道
这两镜之间要不要转场、要不要连续、观众该不该喘口气。

改成：
    一镜给到底，时长 = min(内容需要, 安全时长)
    超出时明说：需要多少、给了多少、差多少、建议怎么办
    不自动拆
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '''    if need <= safe:
        total, per, n = need, need, 1
        reason = f"内容约 {beats} 拍 x {_SEC_PER_BEAT:g}s = {need}s，在安全时长内"
    else:
        n = (need + safe - 1) // safe
        # 拆镜后的每镜时长也要卡下限（原来写死 3，会给 MiniMax 出 3 秒的无效参数）
        per = max(mn, need // n)
        # 若卡了下限导致总长超出上限，就再多拆一镜
        while per * n > mx:
            n += 1
            per = max(mn, need // n)
        total = per * n
        reason = (f"内容约 {beats} 拍需要 {need}s，超过该平台安全时长 {safe}s "
                  f"-> 拆成 {n} 镜，每镜 {per}s")'''
new = '''    # 不自动拆镜：一镜给到底，超出的部分只做说明，拆分与否由人决定。
    total, per, n = min(need, safe), min(need, safe), 1
    if need <= safe:
        reason = f"内容需要约 {need}s，在安全时长内"
    else:
        over = need - safe
        reason = (f"内容需要约 {need}s，超过该平台安全时长 {safe}s（差 {over}s）。"
                  f"本镜按 {safe}s 给满；超出部分建议自行删减，或另起一镜——"
                  f"**工具不替你拆**，因为拆分涉及转场与节奏，那该你来定")'''
assert old in s, "拆镜逻辑没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已去掉自动拆镜")
for plat, q in (("MiniMax", "拿起简然后变然后亮然后成册然后合上然后放下"),
                ("即梦", "拿起简然后变然后亮"),
                ("Veo", "拿起简")):
    t, per, n, line = N._plan_duration(plat, q)
    print(f"    [{plat}] {per}s x {n} 镜 = {t}s")
    print(f"       {line.split(chr(10))[0][:96]}")
