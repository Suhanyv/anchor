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

节点参数 13 个，常用的就三个：`中文描述`、`域`（自动/图片/视频）、`候选数`。
输出接到 `CLIPTextEncode.text` 即可。

> ⚠️ 首次运行会加载模型 + 编码全部文档，约 30–60 秒；之后每次 15–60 ms（纯 CPU，不占显存）。

### 方式二：HTTP 服务

```bash
python src/serve_style.py --port 8848 --corpus data/raw/corpus_v16.jsonl --model models/e5-director-c18

curl -X POST http://127.0.0.1:8848/style-hint \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{"query":"霓虹夜色，慢门，暧昧的感觉","topk":3}'
```

> 注意：服务端目前**只有风格通道**，节点有多通道。见 LIMITATIONS 第八节第 6 条。

### 方式三：直接调函数

```python
import sys; sys.path.insert(0, "comfyui")
import local_style_hint as N

out, debug = N.LocalStyleHint().run(
    "雪林里女子拉弓搭箭，冷白风雪",
    model_dir   = "models/e5-director-c18",
    corpus_path = "data/raw/corpus_v16.jsonl",
    subject_path= "data/raw/subjects_v4.jsonl",
    craft_path  = "data/raw/crafts_v3.jsonl",
    material_path="data/raw/materials_v4.jsonl",
    use_material=True,
    device="cpu", domain="自动", mode="导演/风格聚合",
    topk=1, append="", include_original=False,
)
print(out)     # 提示词片段
print(debug)   # 各通道打分与最终裁决
```

---

## 架构：四个索引 + 一条裁决规则

```
              ┌─ 风格索引  796 条 / 129 实体 ──→ in the style of <导演>, <标签>
              ├─ 题材索引   40 条 /  20 题材  ──→ a knight in plate armour on a horse
中文 query ───┼─ 工艺索引   32 条 /  16 工艺  ──→ rendered as a cyanotype print
              └─ 材质索引  109 条 /  23 材质  ──→ …, 暗角，画面边缘压暗
                        ↓
                赢家通吃：谁分最高谁说话；风格最高则什么内容都不拼
                每渠道另有绝对下限（风格低分时会误开，所以必须有）
```

**为什么四个索引而不是一个？** 实测把工艺塞进风格索引会让场景 −5pp、材质 −7pp。
共享向量空间里任何新增都会稀释已有维度，只有正交通道不互相伤害。

**为什么赢家通吃？** 10 条测试里，正确答案 9 次就是分最高的那个渠道；
而"相对比值"（渠道分 ≥ 风格分 × 0.95）在风格分低时会全部误开。

---

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
  url    = {https://github.com/<your-account>/anchor}
}
```
