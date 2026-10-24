"""修复 CHANGELOG.md：按版本号倒序重排，并补上 v0.1.6

起因：之前多次用 PowerShell here-string 往文件里插内容，
引号被 shell 吃掉，导致标题跑到中间、版本顺序错乱、v0.1.6 丢失。
从现在起：凡是要写文件内容，一律用 write/edit 工具或本脚本，不经过 shell 拼接。
"""
import json
import re
from pathlib import Path

P = Path(r"F:\llm\CHANGELOG.md")

V016 = """## v0.1.6 — 按平台输出不同格式（2026-10-25）

### 核心观念

提示词不是一个字符串，是**面向某个平台的表达**。同一个镜头：

    Seedance 2.5   要中文五段式，含【时间线】
    MiniMax H3     要中文整段自然语言，不编号
    图像 / SD      要英文逗号串 + 独立负向，**没有时间轴**

格式错了，内容再对也是白给。

### 节点参数：`输出结构` 换成 `输出格式`（5 选 1）

| 格式 | 用于 | 语言 | 时间轴 |
|---|---|---|---|
| 片段（英文）| 任何 | 英 | 无 |
| 结构化（英文）| 任何 | 英 | 无（视频另有 Action 行）|
| Seedance 2.5（中文）| 视频 | 中 | **三段** |
| MiniMax H3（中文）| 视频 | 中 | 段落内 |
| SD 正负向（英文）| 图像 | 英 | 无 |

**域与格式不匹配会自动回落**并说明（「Seedance 是视频格式，当前是图片域 -> 回落到结构化」）。

### 两个设计上的坑（都已修）

1. **中文模板里塞英文**：第一版把检索到的英文描述当主体填进 `【主体】`，
   得到 `【主体】a woman's face in extreme close-up...，出现在<场景>`——对中文平台是废的。
   -> 改为**主体用用户的原话**，英文只出现在 `风格锚定：` 那一行。
2. **同一组词说两遍**：MiniMax 那段里「光线与质感是 X」和「整体走 X」重复。
   -> 光/质感优先用材质与工艺通道，两者都没命中才回落到风格关键词。

视频的时间轴按该实体的建议时长自动切三段（1/3、2/3 处）；图像完全不生成时间轴。

### 文档

`docs/OUTPUT_FORMATS.md`：格式清单、为什么视频必须有时间轴、中文格式为什么用你的原话，
以及**平台格式的可信度声明**——只对核实过的 Seedance / MiniMax / SD 提供格式，
其它平台宁可不支持也不瞎猜。

---

"""


def main():
    text = P.read_text(encoding="utf-8")
    # 去掉所有标题行，稍后统一加一个
    body = "\n".join(l for l in text.splitlines() if l.strip() != "# 更新日志")

    # 按 "## v0.1.x" 切段
    parts = re.split(r"(?m)^(?=## v0\.1\.)", body)
    header_extra = ""
    sections = {}
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"## v0\.1\.(\d+)", p)
        if m:
            sections[int(m.group(1))] = p
        else:
            header_extra += p + "\n\n"

    # 补 v0.1.6
    if 6 not in sections:
        sections[6] = V016.strip()

    out = ["# 更新日志", ""]
    for v in sorted(sections, reverse=True):
        out.append(sections[v])
        out.append("")
        out.append("---")
        out.append("")
    if header_extra.strip():
        out.append(header_extra.strip())

    P.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")

    # 校验
    txt = P.read_text(encoding="utf-8")
    found = re.findall(r"(?m)^## (v0\.1\.\d+)", txt)
    print("  版本顺序:", found)
    print("  有标题:", txt.startswith("# 更新日志"))
    print("  行数:", len(txt.splitlines()))
    if 0 in sections:
        print("  v0.1.0 保留: 是")


if __name__ == "__main__":
    main()
