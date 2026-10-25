"""
时长表 v3：补上「最短时长」这个维度

查到的硬数据
-----------
MiniMax H3（Hailuo 3）官方文档：
    · durations from **4 to 15 seconds**
    · Any integer from 4 to 15 seconds (**default 5**)
    · 768P / 2K，24 fps
可灵 4.0 官方页面：
    · videos **up to 30 seconds** long
Runway Gen-4：官方帮助页 403，取不到 -> 保持保守值并标注

为什么要补下限
--------------
我原来只给了上限和安全值，随便给个 3 秒。
但 MiniMax 最短就是 4 秒——**3 秒是个无效参数，提交会失败或被改**。
下限和上限一样是硬约束。

顺带一个巧合
------------
MiniMax 官方默认值是 5 秒，和我们的"1 拍 = 2.5 秒 -> 简单内容约 5 秒"对上了。
这不是我算得准，是两边都按"一个动作能撑多久"在估。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old_start = s.index("_MODEL_LIMITS = {")
old_end = s.index("}", s.index('"通用"', old_start)) + 1
new_table = '''# (上限, 经验安全, 依据, 最短)
_MODEL_LIMITS = {
    # ---- 闭源：上限为官方值 ----
    "即梦":      (30, 30, "官方单段最长 30s；使用者实测长时长仍稳", 4),
    "Seedance":  (30, 30, "同上", 4),
    "MiniMax":   (15, 10, "官方 4–15s（任意整数，默认 5）；"
                          "使用者实测 10s 后开始崩", 4),
    "可灵":      (30, 10, "官方 up to 30s；安全值未核实，保守取 10", 3),
    "Veo":       (8, 8, "官方固定 8 秒单镜", 8),
    "Runway":    (10, 5, "官方帮助页 403 未取到，保守取 10/5", 5),

    # ---- 开源：安全时长 = 训练帧数 / 帧率 ----
    "HunyuanVideo": (5, 5, "训练 129 帧 @24fps ≈ 5.4s（模型卡）", 3),
    "混元":         (5, 5, "同上：129 帧 @24fps ≈ 5.4s", 3),
    "Wan":          (5, 5, "训练 81 帧 @16fps ≈ 5.1s（模型卡）", 3),
    "CogVideoX":    (10, 5, "官方表 5s 或 10s；5s 稳，10s 为上限", 5),
    "Mochi":        (3, 3, "README 示例 31 帧；长时长未核实", 3),
    "LTX":          (10, 10, "LTX-2 官方 <=10s 连续（带音频）；"
                             "60s 为蒸馏版宣称值", 4),

    "通用": (10, 6, "无平台信息时的默认", 3),
}'''
s = s[:old_start] + new_table + s[old_end:]

# _limit_of 返回 4 元组
s = s.replace('''def _limit_of(platform):
    for k, v in _MODEL_LIMITS.items():
        if k in (platform or ""):
            return v
    return _MODEL_LIMITS["通用"]''',
'''def _limit_of(platform):
    for k, v in _MODEL_LIMITS.items():
        if k in (platform or ""):
            return v
    return _MODEL_LIMITS["通用"]''', 1)

# _plan_duration 里解包与钳制
s = s.replace('    mx, safe, src = _limit_of(platform)',
              '    mx, safe, src, mn = _limit_of(platform)', 1)
s = s.replace('''    need = int(round(beats * _SEC_PER_BEAT))
    need = max(3, min(need, mx))''',
'''    need = int(round(beats * _SEC_PER_BEAT))
    need = max(mn, min(need, mx))   # 下限也是硬约束：低于它提交无效''', 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  表已更新为 4 元组，共", len(N._MODEL_LIMITS), "项")
for plat, q in (("MiniMax", "拿起简"), ("Veo", "拿起简"), ("可灵", "拿起简"),
                ("CogVideoX", "拿起简")):
    print("  " + N._plan_duration(plat, q)[3].split("\n")[0][:100])
