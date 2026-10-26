"""
生成格式对照表：同一个镜头，13 种活格式各出一版

目的
----
节点下拉里有 14 个选项，选之前根本不知道差别。
这张表用**同一个中文描述**跑一遍全部格式，把结果并排放，
让人一眼看出"Veo 没有时间轴""MiniMax 是七行""可灵是一段散文"。

产物
----
    docs/FORMAT_SAMPLES.md
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v4.jsonl")
K = os.path.join(ROOT, "data/raw/crafts_v3.jsonl")
MT = os.path.join(ROOT, "data/raw/materials_v4.jsonl")

# 一个视频镜头 + 一个图像描述
CASES = [
    ("一个男孩和一个鲸鱼女孩在卧室里相拥", "视频", "prompt_video"),
    ("雨夜的街道，霓虹倒映在积水里，一个人走过", "图片", "prompt_image"),
]

# 格式 -> (适用说明, 出处)
INFO = {
    "片段（英文）": ("任何平台都能吃的底料，接在主体后面", "通用"),
    "结构化（英文）": ("人看的分栏文本，排查用", "通用"),
    "通用五面（英文，模型无关）": ("不知道选哪个时的保底", "OpenMontage / CMU 论文"),
    "即梦 Seedance 2.5（中文）": ("四段式 + 连续整数秒时间轴", "即梦官方指南"),
    "即梦 Seedance · 关键帧（中文）": ("第一句声明帧顺序", "即梦官方指南"),
    "MiniMax H3（中文）": ("七行模板，素材用 @1 @2", "MiniMax 官方指南"),
    "混元 HunyuanVideo（中文八段）": ("主体/运动/场景/景别/运镜/光照/风格/氛围", "腾讯 Prompt Handbook"),
    "Runway Gen-4（英文，≤60 词）": ("只写运动，不写外观", "Runway 官方指南"),
    "可灵 4.0（中文，七要素）": ("一段散文，七要素按序", "可灵官方指南"),
    "可灵·多镜头（中文）": ("先环境再分镜，每镜不同任务", "可灵官方指南"),
    "可灵 4.0·关键帧（中文）": ("按时间段写关键帧之间发生了什么", "可灵官方指南"),
    "Veo 3（英文，8 秒单镜）": ("五行短句，固定 8 秒，没有时间轴", "Veo 官方指南"),
    "Sora 2（已停服 · 仅存档）": ("八模块；平台已停止服务", "CSDN 社区总结（非官方）"),
    "SD 正负向（英文）": ("图像专用，正向+负向两行", "通用做法"),
}


# --- 统一路径：以节点默认值为准，避免脚本与部署漂移 ---
try:
    from paths import DEFAULTS as _PATHS
    M, C = _PATHS["model"], _PATHS["corpus"]
    S, K, MT = _PATHS["subjects"], _PATHS["crafts"], _PATHS["materials"]
except Exception:
    pass


def main():
    node = N.LocalStyleHint()
    fmts = node.INPUT_TYPES()["required"]["输出格式"][0]

    out = ["# 格式对照表", ""]
    out.append("> 同一个中文描述，14 种格式各跑一遍。**内容相同，形状不同。**")
    out.append("> 由 `src/gen_format_samples.py` 自动生成，模型 c27 / 语料 v21。")
    out.append("")

    # 总览表
    out.append("## 一、总览")
    out.append("")
    out.append("| 格式 | 什么时候用 | 出处 |")
    out.append("|---|---|---|")
    for f in fmts:
        use, src = INFO.get(f, ("—", "—"))
        out.append(f"| `{f}` | {use} | {src} |")
    out.append("")

    # 逐格式样例
    for qi, (q, dlabel, dom) in enumerate(CASES, 1):
        out.append(f"## {'二' if qi == 1 else '三'}、样例：{dlabel}")
        out.append("")
        out.append(f"**输入描述**：`{q}`")
        out.append("")
        for f in fmts:
            try:
                # 任务 / 提案分镜 是后加的，不传会 TypeError（样例会变成 30 条报错）
                task = "图生视频" if "图生" in f else "文生视频"
                text, dbg = node.run(q, M, C, S, K, MT, True, task, False, f,
                                     "cpu", dlabel, "导演/风格聚合", 1, "", False)
            except Exception as e:  # noqa: BLE001
                text, dbg = f"（出错：{type(e).__name__}: {e}）", ""
            head = next((l for l in dbg.split("\n") if l.startswith("【格式】")), "")
            out.append(f"### {f}")
            out.append("")
            if head:
                out.append(f"> {head}")
                out.append("")
            out.append("```text")
            out.append(text.rstrip())
            out.append("```")
            out.append("")

    # 判读
    out.append("## 四、怎么选")
    out.append("")
    out.append("```")
    out.append("要时间轴、要分段变化      -> 即梦 Seedance / 可灵 4.0 / MiniMax H3")
    out.append("只要一个 8 秒的瞬间       -> Veo 3（五行，没有分段）")
    out.append("要最短、只写运动          -> Runway Gen-4（≤60 词）")
    out.append("出图像而不是视频          -> SD 正负向")
    out.append("平台没在列表里            -> 通用五面（保底，任何模型都能吃）")
    out.append("")
    out.append("中文平台优先用中文格式；英文模型（Veo/Runway/SD）用英文格式。")
    out.append("混用会让模型解析变差，这不是风格问题，是语言问题。")
    out.append("```")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## 五、三条通用于所有平台的规律")
    out.append("")
    out.append("今天读的六份材料（含四份官方指南）里，三家独立提到了同一件事：")
    out.append("")
    out.append("1. **一个镜头只写一种运动** —— 不要「推进+旋转+拉远」同时出现")
    out.append("   （可灵：运镜太多画面乱；OpenMontage：dolly ≠ zoom，pan ≠ truck）")
    out.append("2. **必须写清「镜头最后停在哪」** —— 可灵、即梦、MiniMax 都单列了这条")
    out.append("3. **必须写清「哪些东西不变」** —— 人物身份、服装、Logo、场景结构")
    out.append("")
    out.append("**这不是某个平台的偏好，是这几个模型的共同失败模式。**")

    p = os.path.join(ROOT, "docs", "FORMAT_SAMPLES.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"  已写 {p}")
    print(f"  格式 {len(fmts)} 种 x 样例 {len(CASES)} 个")
    print("### FORMAT_SAMPLES_DONE")


if __name__ == "__main__":
    main()
