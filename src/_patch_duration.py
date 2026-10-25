"""
时长规划：按「模型安全时长 × 内容需要」决定每镜多长

为什么需要
----------
同一个 20 秒：
    即梦 Seedance  撑得住（上限 30 秒）
    MiniMax H3     10 秒以后开始崩（上限 15 秒）

**"能生成"和"能看"不是一回事**，而后者只有实测知道。

两条约束同时成立才给时长
------------------------
    可用时长 = min(模型安全时长, 内容撑得住的时长)

内容撑不住的信号（官方指南里也提过：内容密度太少模型会自由补充）：
    · 一个动作 3–5 秒就够，写长了模型自己加戏
    · 每多一拍（变形 / 转折 / 新主体入画）约 +2.5 秒
    · 人多、交互多 -> 更难，宁可短

超出安全时长 -> **拆镜**，不是硬撑。

数据性质
--------
平台上限：官方公开值。
安全时长：**使用者实测的经验值**，标注清楚来源；未核实的一律保守取小。
这张表会随实测更新，不是定论。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_MODEL_LIMITS" not in s:
    fn = '''# 平台时长：max=官方上限，safe=经验上仍能看的时长，src=依据
# 未核实的 safe 一律保守取小 —— 宁可建议短一点，也别让它崩在中段。
_MODEL_LIMITS = {
    "即梦":      (30, 30, "上限官方 30s；使用者实测长时长仍稳"),
    "Seedance": (30, 30, "同上"),
    "MiniMax":  (15, 10, "上限 15s；使用者实测 10s 后开始崩"),
    "可灵":     (30, 10, "上限官方 30s；安全值未核实，保守取 10"),
    "Veo":      (8, 8, "官方固定 8 秒单镜"),
    "Runway":   (10, 5, "未核实，保守取 5"),
    "混元":     (10, 5, "未核实，保守取 5"),
    "通用":     (10, 6, "无平台信息时的默认"),
}

# 每拍的秒数：一拍 = 一个可分辨的动作或变化
_SEC_PER_BEAT = 2.5


def _limit_of(platform):
    for k, v in _MODEL_LIMITS.items():
        if k in (platform or ""):
            return v
    return _MODEL_LIMITS["通用"]


def _est_beats(q):
    """粗估内容需要几拍。宁可高估：低估会让长镜头太空。"""
    t = q or ""
    beats = 1
    # 显式转折词
    for w in ("然后", "接着", "随后", "最后", "变成", "逐渐", "再", "又"):
        beats += t.count(w)
    # 箭头也是转折
    beats += t.count("→") + t.count("->")
    # 人或物一多，交互成本上来
    if any(w in t for w in ("一群", "多人", "人群", "众人", "交战", "混战")):
        beats += 2
    # 已分镜的描述：拍数就是镜数
    n_shot = sum(1 for i in range(1, 10) if f"镜头{'一二三四五六七八九'[i-1]}" in t)
    if n_shot >= 2:
        beats = max(beats, n_shot)
    return max(1, min(beats, 8))


def _plan_duration(platform, q, asked=None):
    """返回 (建议总时长, 每镜时长, 镜数, 说明行)"""
    mx, safe, src = _limit_of(platform)
    beats = _est_beats(q)
    need = int(round(beats * _SEC_PER_BEAT))
    need = max(3, min(need, mx))

    if need <= safe:
        total, per, n = need, need, 1
        reason = f"内容约 {beats} 拍 x {_SEC_PER_BEAT:g}s = {need}s，在安全时长内"
    else:
        n = (need + safe - 1) // safe
        per = max(3, need // n)
        total = per * n
        reason = (f"内容约 {beats} 拍需要 {need}s，超过该平台安全时长 {safe}s "
                  f"-> 拆成 {n} 镜，每镜 {per}s")

    line = (f"【时长】建议 {per} 秒/镜 x {n} 镜 = {total}s。"
            f"（{platform or '通用'} 上限 {mx}s，经验安全 {safe}s；{reason}）")
    if src:
        line += f"\\n        依据：{src}。"
    return total, per, n, line


'''
    anchor = "def _cine_line(c):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 接进输出：多镜头共用块 + 图生视频 + 常规分发的 dbg
A1 = ('        f"【共用】{("；".join([x for x in (light, style) if x]))}。{ar}。",',
      '        f"【共用】{("；".join([x for x in (light, style) if x]))}。{ar}。",\n'
      '        "        " + _plan_duration(fmt, " ".join(shots))[3],')
if A1[0] in s:
    s = s.replace(A1[0], A1[1], 1)
    print("  已接多镜头共用块")
else:
    print("  ⚠️ 多镜头共用块未匹配")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
for plat, q in (("即梦", "一个骑士和一群人交战"), ("MiniMax", "竹简慢慢变成全息册子"),
                ("Veo", "一个男孩在卧室里"), ("可灵", "拿起竹简然后变形然后成册")):
    print(" ", N._plan_duration(plat, q)[3].split("\n")[0])
