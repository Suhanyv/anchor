"""
按时长表更新：开源模型的"安全时长"= 训练帧数换算的秒数

查到的硬数据（抓模型卡，见 E:\\external\\research\\models\\）
------------------------------------------------------------
    HunyuanVideo   720px1280px**129f**   @24fps ≈ 5.4s
    Wan2.1         num_frames=**81**      @16fps ≈ 5.1s
    CogVideoX      官方表：**5 seconds or 10 seconds**
    Mochi          README 示例 num_frames=**31**
    LTX-2          官方 **≤10s** 连续（带同步音频）；
                   v0.9.8 蒸馏版宣称支持 **60s**（宣称值，非训练长度）

一个明显的规律
--------------
**开源模型的可用时长普遍在 5 秒上下**，因为训练帧数是硬约束，
超过去就是外推，必崩。闭源平台（即梦/可灵 30s）能长好几倍，
是因为它们在训练与后处理上另有投入。

所以"安全时长"对开源模型不是经验值，是**设计参数**；
对闭源平台才需要实测。
"""
import ast
import os
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old_start = s.index("_MODEL_LIMITS = {")
old_end = s.index("}", s.index('"通用"', old_start)) + 1
new_table = '''_MODEL_LIMITS = {
    # ---- 闭源：上限是官方值，安全时长靠实测 ----
    "即梦":      (30, 30, "官方上限 30s；使用者实测长时长仍稳"),
    "Seedance":  (30, 30, "同上"),
    "MiniMax":   (15, 10, "上限 15s；使用者实测 10s 后开始崩"),
    "可灵":      (30, 10, "官方 3–30s；安全值未核实，保守取 10"),
    "Veo":       (8, 8, "官方固定 8 秒单镜"),
    "Runway":    (10, 5, "未核实，保守取 5"),

    # ---- 开源：安全时长 = 训练帧数 / 帧率，是设计参数不是经验值 ----
    "HunyuanVideo": (5, 5, "训练 129 帧 @24fps ≈ 5.4s（模型卡）"),
    "混元":         (5, 5, "同上：129 帧 @24fps ≈ 5.4s"),
    "Wan":          (5, 5, "训练 81 帧 @16fps ≈ 5.1s（模型卡）"),
    "CogVideoX":    (10, 5, "官方表 5s 或 10s；5s 稳，10s 为上限"),
    "Mochi":        (3, 3, "README 示例 31 帧；长时长未核实，保守取小"),
    "LTX":          (10, 10, "LTX-2 官方 ≤10s 连续（带音频）；60s 为蒸馏版宣称值"),

    "通用": (10, 6, "无平台信息时的默认"),
}'''
s = s[:old_start] + new_table + s[old_end:]

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  时长表已更新，共", len(N._MODEL_LIMITS), "项")

# 追加文档
doc = r"F:\llm\docs\PLATFORM_MATRIX.md"
t = open(doc, encoding="utf-8").read()
if "开源模型的安全时长" not in t:
    sec = """
### 补充：开源模型的安全时长是「设计参数」，不是经验值

抓了各模型卡（2026-10-25）：

| 模型 | 训练/官方规格 | 换算 | 来源 |
|---|---|---|---|
| HunyuanVideo | 720px1280px **129f** | @24fps ≈ **5.4s** | 腾讯模型卡 |
| Wan2.1 | `num_frames=81` | @16fps ≈ **5.1s** | Wan2.1 README |
| CogVideoX | 官方表「**5 seconds or 10 seconds**」 | 5s 稳 / 10s 上限 | CogVideo README |
| Mochi | README 示例 `num_frames=31` | ≈1s（示例值） | Mochi README |
| LTX-2 | 官方「**≤10s** 连续（带音频）」 | 10s | LTX README |
| LTX v0.9.8 蒸馏 | 宣称「up to **60 seconds**」 | **宣称值，非训练长度** | LTX README |

**规律：开源模型的可用时长普遍在 5 秒上下。** 训练帧数是硬约束，
超过就是外推，所以会"崩"。闭源平台（即梦/可灵 30s）能长好几倍，
是因为训练与后处理另有投入——**这不是同一个量级的工程。**

所以：
- **开源** -> 安全时长可以直接从帧数算，不需要实测
- **闭源** -> 只有实测知道（`MiniMax 10s 后崩` 就是实测值）

> 提醒：LTX 那个 60 秒是蒸馏版的宣称，不等于训练长度。
> 宣称值不进表，表里只写「能支撑的时长」。

"""
    t = t.replace("## 一、闭源平台", sec + "---\n\n## 一、闭源平台", 1)
    open(doc, "w", encoding="utf-8").write(t)
    print("  文档已追加开源时长表")
else:
    print("  文档已有")
