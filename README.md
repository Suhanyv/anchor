# 锚 · Anchor

> ## ⚠️ v0.1 研究预览（research preview）
>
> **这个项目的评测集很小，请不要把它当作横向比较的基准。**
>
> - 场景基准只有 **20 题**，全部由作者从真实提示词中拆解而来
> - 真人用户 query 只有 **2–3 条**
> - 因此 **top1 55% / 材质 47%** 这些数字的**置信区间很宽**，只应看作"它能跑起来、方向对"
>
> 我们明确知道这不够。**欢迎提交你用过的真实中文描述（脱敏即可）来扩充评测集。**
> 缺陷清单见 [LIMITATIONS.md](LIMITATIONS.md)，比本文件重要。

**中文描述 → 英文的电影风格提示词片段。**

你写「远远的镜头，一条草船在江上，有个老渔夫在划」，
它给你：

```
a small boat on grey river water, mist banked on the surface, ink-wash far peaks,
in the style of Hou Hsiao-hsien, very long static shot, misty river with one distant boat,
slow push-in, steady drift
```

不是整段提示词，是**风格那一段**。主体、叙事、调度留给你自己。

---

## 它做什么 / 不做什么

| 做 | 不做 |
|---|---|
| 给风格命名（哪个导演、哪个视觉传统）| 不替你写叙事和调度 |
| 给题材短语（骑士 / 雪原 / 杂货铺）| 不支持代码、科技类内容 |
| 给材质与光（拉丝金属上的高光 / 暗角）| 不保证生成的图一定像 |
| 给工艺媒介（蓝晒 / 铜版 / 金缮）| 不做图像生成 |

**真实水平：场景锚定 top1 = 55%，top3 = 70%。**
请先读 [LIMITATIONS.md](LIMITATIONS.md) —— 比这个文件重要。

---

## 快速开始

**模型不需要下载。** 权重不进 git，但可以在干净克隆里用 **1.5 分钟从数据重建**（已实测）：

```bash
git clone <repo> && cd anchor
pip install torch --index-url https://download.pytorch.org/whl/cu130   # Windows 必须这样装
pip install -r requirements.txt
bash src/reproduce.sh                      # 重建模型 + 冒烟测试
bash src/reproduce.sh --bench              # 顺带跑全部基准
```

> 为什么这么做：465 MB 的权重两分钟就能复现，别人自己训一遍也比下载我们的更能验证结果。
> 详见 [models/MODEL_CARD.md](models/MODEL_CARD.md)。

### 方式一：ComfyUI 节点（推荐）

```bash
# 1. 把节点目录放进 ComfyUI 的 custom_nodes
cp -r comfyui/  <ComfyUI>/custom_nodes/prompt_style_local/

# 2. 需要 python 包
pip install torch transformers

# 3. 把工作流拖进 ComfyUI
#    comfyui/workflow_style_hint.json
```

节点参数 16 个，常用三个：`中文描述`、`任务`（文生视频/图生视频/参考生视频）、
`输出格式`（默认「自动」会从描述里认平台，比如写了"sd2.5"就出即梦格式）。
输出接到 `CLIPTextEncode.text` 即可。

> ⚠️ 首次运行会加载模型 + 编码全部文档，约 30–60 秒；之后每次 15–60 ms（纯 CPU，不占显存）。

### 文档索引

| 文档 | 什么时候看 |
|---|---|
| [docs/OUTPUT_FORMATS.md](docs/OUTPUT_FORMATS.md) | 输出格式有哪几种、什么时候用哪种 |
| [docs/PLATFORM_MATRIX.md](docs/PLATFORM_MATRIX.md) | 每个平台的上限/时间轴/安全时长；以及各平台内容的实测结论 |
| [docs/FORMAT_SAMPLES.md](docs/FORMAT_SAMPLES.md) | 同一个镜头在 14 种格式下长什么样（并排对比）|
| [docs/LOCAL_LLM_DIRECTOR.md](docs/LOCAL_LLM_DIRECTOR.md) | 本地小模型能不能自己写分镜（三轮实验与结论）|
| [STATUS.md](STATUS.md) | 全部实验记录（六十九节）|
| [CORRECTIONS.md](CORRECTIONS.md) | **读任何数字之前先看这份** |
| [LIMITATIONS.md](LIMITATIONS.md) | 已知缺陷 |

### 方式二：HTTP 服务

**服务端和节点是同一套实现**——服务直接调 `comfyui/local_style_hint.py` 的 `run()`，
所以四通道和 14 种输出格式**天然一致**，不会漂。

```bash
python src/serve_style.py --port 8848          # 默认读 v21 语料 + c27 模型
```

```bash
# 健康检查：文档数、模型、通道、可用格式
curl http://127.0.0.1:8848/health

# 出提示词（format 可选，默认「结构化（英文）」）
curl -X POST http://127.0.0.1:8848/style-hint \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{"query":"霓虹夜色，慢门，暧昧的感觉",
       "topk":3,"domain":"video",
       "format":"即梦 Seedance 2.5（中文）"}'

# 只看原始检索结果（不套模板），用于排查
curl -X POST http://127.0.0.1:8848/search \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{"query":"一个杯子就让人紧张","topk":5}'
```

`domain` 接受 `auto` / `image` / `video` / `any`，也接受中文的 自动/图片/视频/不限。
`format` 取值见 `/health` 的 `formats` 字段（14 种，含即梦/可灵/MiniMax/Veo 等）。

### 方式三：直接调函数

```python
import sys; sys.path.insert(0, "comfyui")
import local_style_hint as N

node = N.LocalStyleHint()

# 位置参数，顺序见下方「参数表」
out, debug = node.run(
    "雪林里女子拉弓搭箭，冷白风雪",      # 中文描述
    "models/e5-director-c22",              # 模型目录
    "data/raw/corpus_v19.jsonl",           # 语料
    "data/raw/subjects_v4.jsonl",          # 题材索引
    "data/raw/crafts_v3.jsonl",            # 工艺索引
    "data/raw/materials_v4.jsonl",         # 材质索引
    True,                                  # 启用材质
    "结构化",                               # 输出结构：片段 / 结构化
    "cpu",                                 # 设备
    "自动",                                 # 域：自动 / 图片 / 视频 / 不限
    "导演/风格聚合",                        # 匹配方式
    1,                                     # 候选数
    "",                                    # 追加到
    False,                                 # 包含原文
)
print(out)     # 提示词（片段 或 结构化文本）
print(debug)   # 各通道打分与最终裁决
```

结构化输出的样子（图像）：

```
Subject:  a knight in plate armour on a horse, castle walls behind
Style:    Robert Eggers, candle-lit darkness, historical authenticity, hard-key monochrome
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened
```

视频是另一套（必须说清镜头怎么动、多长、画幅）：

```
Shot:     slow push-in, 5s, 21:9
Action:   two figures crossing in mid-air above a forest canopy, robes tangling
Style:    Ching Siu-tung, wire-work flight, sleeves and ribbons, drifting mist
Negative: scene change, camera shake, zoom pumping, fast cutting, jump cuts
```

### 参数表（16 个）

| # | 参数 | 取值 |
|---|---|---|
| 1 | 中文描述 | 你的中文描述 |
| 2 | 模型目录 | `models/e5-director-c27` |
| 3 | 语料文件 | `data/raw/corpus_v21.jsonl` |
| 4 | 题材文件 | `data/raw/subjects_v12.jsonl` |
| 5 | 工艺文件 | `data/raw/crafts_v6.jsonl` |
| 6 | 材质文件 | `data/raw/materials_v11.jsonl` |
| 7 | 启用材质 | True / False |
| 8 | **任务** | **文生视频**（万物都写）/ **图生视频**（只写动作，外观交给首帧）/ **参考生视频**（写清每条素材职责）|
| 9 | 提案分镜 | True：只给了"想要 N 个镜头"时，按建立/交手/收自动编排；False：出空槽 |
| 10 | **输出格式** | **自动（识别平台）** + 14 种，见 [格式清单](docs/OUTPUT_FORMATS.md) |
| 11 | 设备 | cpu / cuda |
| 12 | 域 | 自动 / 图片 / 视频 / 不限 |
| 13 | 匹配方式 | 导演/风格聚合 / 原样提示词 |
| 14 | 候选数 | 1–5 |
| 15 | 追加到 | 附加在末尾的固定文本 |
| 16 | 包含原文 | 把中文原话拼在最前 |

**最常用的三个**：`中文描述`、`任务`、`输出格式`（默认"自动"就会从你的描述里认平台）。

### 三个可编辑的数据表（改它们不用改代码）

| 文件 | 管什么 |
|---|---|
| `data/raw/duration_ref.json` | 每镜多长：静态 3 秒 / 动作 4 秒 / 强动作 5 秒 / 变形 6 秒 |
| `data/raw/moderation_ref.json` | 平台 × 内容类别能不能过（每格带实测者与日期）|
| `data/raw/prefs.jsonl` | 你对产出方案的偏好记录（品味数据的原料）|



---

## 架构：四个索引 + 一条裁决规则

```
              ┌─ 风格索引 1045 条 / 175 实体 ──→ in the style of <导演>, <标签>
              ├─ 题材索引  294 条 /  88 项  ──→ a knight in plate armour on a horse
              │                                （含"场景"一支：卧室/沙滩/窗台/天桥…）
中文 query ───┼─ 工艺索引  125 条 /  47 项  ──→ rendered as a cyanotype print
              └─ 材质索引  305 条 /  69 项  ──→ …, 暗角，画面边缘压暗
                        ↓
                赢家通吃：谁分最高谁说话；风格最高则什么内容都不拼
                每渠道另有绝对下限（风格低分时会误开，所以必须有）
                近似平局（差 0.015 内）判题材赢——具体物件比技法更该当主体
                精确词命中可越过下限（查询里逐字写了词，比余弦相似度更硬）
```

**为什么四个索引而不是一个？** 实测把工艺塞进风格索引会让场景 −5pp、材质 −7pp。
共享向量空间里任何新增都会稀释已有维度，只有正交通道不互相伤害。

**为什么场景单独一支？** 填充率审计发现：查"东西"（汝窑、雪中庭院）能填满，
查"场面"（在卧室相拥、在沙滩奔跑）全是占位符——**因为四个通道里没有"地点"**。
加上场景支之后 Veo 从 57% → 79%，混元 21% → 43%。


**为什么赢家通吃？** 10 条测试里，正确答案 9 次就是分最高的那个渠道；
而"相对比值"（渠道分 ≥ 风格分 × 0.95）在风格分低时会全部误开。

---

> **读这些数字前先看 CORRECTIONS.md。**
> 语料增长会让候选池变大，top-1 自然下降——那不是模型退步。
> 任何语料变了的对比都必须用 src/bench_fair.py 同时报**绝对**与**受控**两组数。

## 实测数字

| 基准 | 结果 | 说明 |
|---|---|---|
| 场景锚定（20 题，真实提示词拆解）| **top1 55% / top3 70%** | ✅ 最接近真实使用 |
| 材质/光（15 概念，文档级）| 47% | 词面判分，是下界 |
| 关键词锚定（2100 条新句式）| 83.7% | ⚠️ 与训练分布同源，仅用于回归 |
| 四语（10 概念）| 中 70 / 日 40 / 韩 40 / 德 50 | 后三者是零样本基线 |
| 5 折 CV（模板整段留出）| style 0.2526 → 0.7398 | 抗模板记忆的证明，见 `bench/` |

---

## 仓库结构

```
src/            63 个脚本：构建语料、训练、评测、诊断、服务
comfyui/        ComfyUI 节点（自包含，13 参数）
data/raw/       语料与索引（.jsonl，CC-BY-4.0）
bench/          全部评测结果与诊断报告（.json）
models/         e5-director-c18（MIT）；另有若干实验版本
STATUS.md       61 节开发日志，含每一次失败与自我更正
LIMITATIONS.md  已知缺陷（先读这个）
NOTICE          第三方来源与许可
```

---

## 三个可复用的方法

这个项目最大的产出可能不是模型，是三条被实测反复验证的规律：

**① 零样本索引必须说用户的语言**
给条目加一个中文名，工艺识别 60% → 100%（15 分钟）。
而训练过的语料不需要——跨语言对齐是学出来的。
*先怀疑表示形式，再怀疑数据量。*

**② 多通道冲突时，先量所有渠道的分**
正确答案往往就是分最高的那个。一条"赢家通吃"胜过 N 条两两互斥规则。

**③ 一个基准涨、另一个跌时，信离真实使用更近的那个**
关键词基准 83.7%→91.6% 的同时，场景基准 55%→45%。
前者与训练数据同源，后者来自真实提示词。**信后者。**

---

## 许可

| 资产 | 许可 |
|---|---|
| 代码 | [Apache-2.0](LICENSE) |
| 语料与索引 | [CC-BY-4.0](LICENSE-DATA.md) |
| 模型权重 | MIT（继承 intfloat/multilingual-e5-small）|

第三方来源见 [NOTICE](NOTICE)。

---

## 引用

```bibtex
@misc{anchor2026,
  title  = {Anchor: vertical cross-lingual retrieval for cinematic style prompts},
  year   = {2026},
  note   = {Chinese query to English style-prompt fragments; 796-doc corpus,
            four-index architecture, scene-anchored top1 55\%},
  url    = {https://github.com/Suhanyv/anchor}
}
```
