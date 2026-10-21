# 项目状态交接（下次从这里接）

> 目标：垂直**跨语言检索**模型（中文 query → 英/日/德/韩 文档）
> 领域：科技 · 图像提示词 · 视频提示词 · 代码

---

## 一、环境：已完全就绪 ✅

| 组件 | 版本 / 位置 |
|---|---|
| Python | 3.12.10 @ `F:\llm\python312` |
| 虚拟环境 | `F:\llm\.venv` |
| PyTorch | **2.9.1+cu130**（CUDA 可用，CC 8.9） |
| transformers | 5.20.1 |
| sentence-transformers | 6.1.0 |
| datasets / accelerate | 5.1.0 / 1.15.0 |
| HF 镜像 | `hf-mirror.com`（在 `env.ps1` 里） |

**C 盘零占用** —— 所有缓存/临时文件都在 F 盘。

启动环境：
```powershell
. F:\llm\env.ps1
F:\llm\.venv\Scripts\python.exe <你的脚本>
```

---

## 二、实测硬件基线（已测，不要重测）

### 算力
| dtype | 峰值 |
|---|---|
| bf16 | **31.26 TFLOPS** |
| fp16 | 31.27 TFLOPS |
| fp32 | 9.14 TFLOPS |
| 显存带宽 | **240.9 GB/s** |

### 训练吞吐（fwd+bwd, bf16 autocast）
| 配置 | 参数 | seq | bs | 样本/秒 | 显存 | 备注 |
|---|---|---|---|---|---|---|
| MiniLM 6L | 22.6M | 256 | 128 | 539.9 | 3.57 GB | 最优 |
| BERT-base | 109.3M | 256 | **32** | **97.7** | 4.62 GB | **甜点** |
| BERT-base | 109.3M | 256 | 64 | ⚠️ 62.4 | 7.79 GB | 断崖 |
| reranker | 109.5M | 512 | **16** | **44.5** | 4.61 GB | **甜点** |
| reranker | 109.5M | 512 | 32 | ⚠️ 25.4 | 7.79 GB | 断崖 |

### 两个必须记住的结论
1. **8GB 的真实可用上限约 7.8 GB**（开局系统已占 1.07 GB）。一旦逼近就性能腰斩，**batch 不是越大越好**。
2. **系统内存只剩 4.8 GB free**（总 15.7 GB，开机被占 11 GB）→ **这是比显存更紧急的瓶颈**，升到 32GB 是性价比最高的升级。

### 热表现：好消息
稳态 **31 TFLOPS / 82°C / 101W，60 秒内零衰减**。笔记本可以连续跑几小时不掉速。
（开机首 10 秒的 45 TFLOPS 是 boost 时钟，不是真实算力。）

---

## 三、tokenizer 实测结论（已验证，直接采用）

| 发现 | 数据 | 决策 |
|---|---|---|
| 提示词参数吃掉 token | 带参数 35 token vs 不带 20 token（**参数占 43%**） | **参数拆成结构化字段走属性过滤，不进语义空间** |
| 代码 tokenizer 不可用 | `def`→`de\|f`，`None`→`No\|ne` | **代码域必须独立模型（代码专用 tokenizer）** |
| 德语复合词被切碎 | `Donaudampfschiff...` → 1 词 7 token | **德语强制 compound splitting** |
| 中文够用 | 0.839 token/字 | 不优化，沿用 e5 词表 |
| 多语词表对英文低效 | 约 1.67 token/词 | **「翻译+英文模型」必须作为 baseline 对照** |

---

## 四、已完成的脚本

| 文件 | 作用 |
|---|---|
| `F:\llm\bench\bench.py` | 硬件基准（TFLOPS/带宽/吞吐/热降频） |
| `F:\llm\bench\pdl.py` | 并行分段下载器（断点续传） |
| `F:\llm\bench\fixjoin.py` | 分块补齐 + SHA256 校验 |
| `F:\llm\src\tokenizer_check.py` | tokenizer 切分质量检查 |
| `F:\llm\src\eval_retrieval.py` | 分域×分语言检索评测（含 `--make-sample`） |

**评测管线已验证可跑通**（GPU 加载 e5-small → 编码 → 分语言打分 → 落盘）。

---

## 五、下一步：只差一个东西

**30 条真实中文 query** —— 用户会真实敲进搜索框的那句话。

```
F:\llm\data\raw\query_zh.txt     # 一行一条，不用标注
```

为什么必须要它：query 是唯一无法合成的数据。用大模型从文档反推 query 是"看着答案出题"，会天然偏向文档用词，和真实分布差很远。

**有了这 30 条**，就能启动「自主选数据」闭环：
```
教师伪标签(bge-m3) → 三信号筛选 → 训练 → 固定人标集评测 → 再挖掘
```

---

## 六、待写代码

1. `mine_interesting.py` —— 三信号打分（margin / novelty / 教师置信）+ 双峰采样
2. `active_loop.py` —— 冷启动 → 挖掘 → 训练 → 评测 循环
3. `parse_prompt.py` —— 提示词参数/描述分离器（用 43% 那组数据做校验）
4. `train_embed.py` —— 对比学习（含 batch 内平行语料，防跨语言对齐遗忘）

---

## 七、铁律（写在这里防止以后忘）

> **数据可以自选，评测绝对不能自选。**

评测集必须固定、来自真实 query、人标相关性。否则会得到漂亮曲线和完全错误的能力判断。

---

## 八、导演提示词语料 + 真实基线（2026-01 更新）

### 语料
来源：BFI《视与听》2022 导演票选 + 影史公认名单
产出：`F:\llm\data\raw\prompt_director.jsonl` (357 条) / `query_director.jsonl` (119 条)
覆盖 119 位导演，每条含 description / params / prompt 三段（参数与语义分离）

### 三次评测：一次比一次干净
| 版本 | 改动 | Recall@10 | 结论 |
|---|---|---|---|
| v1 | 单一模板 query | 0.1625 | ❌ 模板坍缩，测的是噪声 |
| v2 | 多模板但用了英文 style_tags | 0.6891 | ❌ **数据泄漏**（英文词逐字命中 doc） |
| **v3** | 多模板 + **中文**关键词 | **0.2269** | ✅ 真实基线 |

### 诊断证据（v1 为什么假）
- query 两两余弦 **0.9385**
- 与「纯模板」相似度 **0.9467** —— 不含任何内容的空模板比真实 query 之间还像
- query 内容词占比仅 27.7%

### v3 分层结果（关键发现）
| query 类型 | n | Recall@10 |
|---|---|---|
| style（只给中文风格词） | 28 | **0.3810** |
| both（风格词+导演名） | 71 | 0.2160 |
| **name（只给中文导演名）** | 20 | **0.0500** ← 低于随机(8.4%) |

**结论：模型完全无法把中文译名映射到英文原名**（"斯科塞斯" → "Martin Scorsese" 失败），
所以带人名的 query 反而拉低指标；而中文风格词 → 英文风格词是对齐的。

### 下一步优先级
1. 人名别名表（中文译名 ↔ 英文原名），确定性解决，成本极低
2. 训练时加入人名平行对
3. 修 doc 侧：固定尾巴占 45.2%，应做模板去重

---

## 九、别名归一化 2x2 消融（关键更正）

### 先撤回一个错误结论
之前说「模型无法把中文译名映射到英文原名」——**错了**。
真实原因：`description` 字段里根本没有导演名（名字只在 `prompt` 的 "in the style of X" 里），
所以 name 类 query 无从匹配。**别名表补的是文档里不存在的信号，当然零收益。**

### 2x2 消融结果
| 组合 | 文档字段 | query | Recall@10 | name类 | both类 | style类 |
|---|---|---|---|---|---|---|
| A | description | 原始 | 0.2269 | 0.0500 | 0.2160 | 0.3810 |
| B | description | 归一化 | 0.2269 | 0.0500 | 0.2160 | 0.3810 |
| C | text_semantic | 原始 | 0.4258 | 0.3167 | 0.4883 | 0.3452 |
| **D** | **text_semantic** | **归一化** | **0.7367** | **0.7167** | **0.8967** | 0.3452 |

- A→B: **+0.0%**（别名单独无效，证实假设）
- A→C: +87.7%（文档含名字）
- A→D: **+224.7%**（两者超叠加）
- name 类: 0.05 → 0.7167（14 倍）

### ⚠️ 但这个 73.67% 不能当能力指标
D 的高分主要来自**人名匹配**，不是风格理解。真正的跨语言视觉理解应看 **style 类 = 0.3452**。
注意 style 类在 C/D 反而略降（0.3810→0.3452）——加名字稀释了风格信号。

**结论：以后盯 style 类指标，不要看总体平均。** 这是继 v2 泄漏之后的第二次自我提醒。

### 下一步
训练目标应明确设为：**提升 style 类（0.3452）**，而不是追总体数字。

---

## 十、训练结果（5 折交叉验证）

配置：multilingual-e5-small / seq128 / batch32 / lr2e-5 / InfoNCE(in-batch + 4 hard negatives)
每 5 epoch 重挖 hard negatives（模型自选"感兴趣"的样本）

| fold | 训练前 style | 训练后 style | 训练前 overall | 训练后 overall |
|---|---|---|---|---|
| 0 | 0.5556 | 1.0000 | 0.5067 | 0.8667 |
| 1 | 0.3333 | 1.0000 | 0.3333 | 0.9167 |
| 2 | 0.3333 | 0.8333 | 0.5417 | 0.9028 |
| 3 | 0.2667 | 0.4000 | 0.3623 | 0.6522 |
| 4 | 0.2000 | 0.6667 | 0.3768 | 0.8406 |

- **style 提升：mean +44.22pp, std 19.35pp**（5 折全部为正）
- style 均值 0.3378 -> 0.7800
- overall 均值 0.4242 -> 0.8358
- 单折训练耗时 1.7 分钟

### 必须记住的两个偏差
1. **每折 dev 只有 5-6 条 style query** -> 单点误差 ±17pp，std 19.35pp 主要是抽样噪声
2. **"best epoch" 是在同一 dev 上挑的** -> 报告值偏乐观（选择偏差）
   诚实估计：真实提升大概 **+25~40pp**，不是 +44

### 结论
方向得到确认（5/5 折为正），但**量级不可信**。
唯一瓶颈是 **query 数量太少（119 条）**，不是算力——训练一轮只要 1.7 分钟。
下一步：把 query 扩到 500+，误差才能压到 ±6pp。

---

## 十一、当前进度（暂停点）

### 已完成
- 环境：torch 2.9.1+cu130 / CUDA 可用 / F 盘（USB，曾掉线一次，已恢复）
- 语料：119 导演 / 357 条提示词（description + text_semantic + params 三分离）
- query：119 条（both 71 / style 28 / name 20）
- 别名表：325 条（大陆/港台/繁体/简称）
- 2x2 消融完成
- 5 折 CV 完成：style 0.3378 -> 0.7800（mean +44.22pp, std 19.35pp，**幅度偏乐观**）
- 模型：`F:\llm\models\e5-small-director-v1`（465MB）

### 已写好但未运行
- `build_queries_v2.py`：119 -> 595 条 query（27 套模板，每位导演 5 条）
- `train_embed.py` 新增 `--select-mode final`（固定 epoch，消除选择偏差）与 `--skip-save`

### 下次开工命令（约 20 分钟）
```powershell
. F:\llm\env.ps1
$vpy = "F:\llm\.venv\Scripts\python.exe"
& $vpy F:\llm\src\build_queries_v2.py          # 595 条 query
& $vpy F:\llm\src\alias_norm.py                # 重建别名归一化
for ($f=0; $f -lt 5; $f++) {
  & $vpy F:\llm\src\train_embed.py --epochs 6 --batch-size 32 --lr 2e-5 `
      --n-folds 5 --fold $f --select-mode final --skip-save --log-suffix "_cv2_$f"
}
```

### 待办优先级
| 优先级 | 事项 |
|---|---|
| P0 | 跑上面这套：595 query + final 模式，得到无偏且误差 ±6pp 的结论 |
| P1 | 扩到日/德/韩（需网络恢复，当前 hf-mirror DNS 解析失败） |
| P2 | 加科技域、代码域 |
| P3 | 真·主动学习循环（三信号：margin / novelty / 教师置信） |

### 关键教训（别再犯）
1. 模板会吃掉语义空间（query 两两余弦 0.9385 时指标无意义）
2. 小心数据泄漏：英文 style_tags 逐字命中 doc，虚高 69%
3. 文档字段要包含真实内容（导演名），否则指标被压
4. 人名匹配撑高的总分不可信，**只看 style 类指标**
5. dev 只有 5-6 条样本时，±17pp 都是噪声

---

## 十二、595 query + 无偏 5 折 CV（P0+P1 完成）

配置：595 query / text_semantic 文档 / 6 epoch 固定 / select-mode=final（无选择偏差）/ 5 折

| fold | base_style | post_style | delta | base_all | post_all |
|---|---|---|---|---|---|
| 0 | 0.2778 | 0.7917 | +0.5139 | 0.4500 | 0.9500 |
| 1 | 0.3611 | 0.8333 | +0.4722 | 0.4639 | 0.9639 |
| 2 | 0.2361 | 0.7222 | +0.4861 | 0.3978 | 0.9440 |
| 3 | 0.1806 | 0.6528 | +0.4722 | 0.4034 | 0.9300 |
| 4 | 0.1884 | 0.8696 | +0.6812 | 0.3789 | 0.9687 |

- **style delta: mean +52.51pp, std 8.89pp**（此前 119 query 时 std 19.35pp -> 误差确实减半）
- style 均值 **0.2488 -> 0.7739**
- overall 0.4188 -> 0.9513 / both 0.4966 -> 1.0000 / name 0.3550 -> 0.9831

### 可信度
119 条 style query 跨 5 折各用一次，池化 SE≈0.039 -> **2σ ≈ ±7.7pp**。
+52.5pp 远超噪声，方向与量级都成立。且已去掉 dev 选 epoch 的选择偏差。

### 但仍有三个必须记住的保留
1. **both=1.0000、name=0.9831 已饱和** -> 这两类被人名匹配过度决定，不可当能力
2. **query 全部由 27 套模板生成** -> 所谓"held-out"只是换了关键词组合，**模板本身都见过**
3. 因此 0.7739 是"同模板新关键词"上的成绩，不等于真实用户 query 的表现

### 下一步（P1.5）
**模板级划分**：整段模板留作 dev，训练只见到其他模板 -> 检验"换一种说法"的泛化能力。
这是当前数据条件下最接近真实泛化的做法。

---

## 十三、模板级留出：证明学到的是语义而非模板（P1.5 完成）

28 套句式模板（both 15 / style 8 / name 5），整段模板分到同一折，训练从未见过这些句式。

| 划分方式 | style 前 | style 后 | delta | overall 后 |
|---|---|---|---|---|
| 同模板内留出 query（宽松） | 0.2488 | 0.7739 | +52.51pp ± 8.89 | 0.9513 |
| **整段模板留出（严格）** | 0.2526 | **0.7398** | **+48.72pp ± 8.44** | 0.9267 |

### 关键结论
严格留出后只掉 **4.3pp**（52.5 -> 48.7）。
**若模型靠记忆模板，此处应崩到 0.3 以下。没有崩 -> 学到的是跨语言语义对齐。**

### 完整实验账本（严格度递增）
| # | 设置 | style delta | 说明 |
|---|---|---|---|
| 1 | 119 query / best-epoch | +44.22pp ± 19.35 | 有选择偏差 + 抽样噪声大 |
| 2 | 595 query / final-epoch / 同模板 | +52.51pp ± 8.89 | 偏差已除，误差减半 |
| 3 | **595 query / final / 模板整段留出** | **+48.72pp ± 8.44** | **当前最严格，结论最可信** |

### 仍然存在的保留（不可忽略）
1. both(≈1.0) / name(≈0.9+) 已饱和 -> 人名匹配过度决定，**只有 style 是真能力指标**
2. 28 套模板全部由我一次性写成，句式分布单一；真实用户说法差异更大
3. 语料仅 357 doc / 119 导演，干净但小
4. loss 2.27->0.20 在 2 轮内完成，过拟合明显，但 CV 证明仍泛化

### 下一步
- P2：**真实用户 query**（唯一无法合成的部分，需要你提供）
- P3：扩日/德/韩（需网络；当前 hf-mirror DNS 解析失败，只能离线用缓存）
- P4：加科技域 / 代码域
- P5：真·主动学习循环（margin / novelty / 教师置信三信号）

---

## 十四、真实用户 query 检验（关键发现）

生产版：全部 590 query 训练 6 epoch -> `F:\llm\models\e5-director-prod`

| # | query | 类型 | base 排名 | 微调后排名 |
|---|---|---|---|---|
| Q1 | 王家卫的风格 | 纯名字 | 93/119 | **1** |
| Q2 | 想要黑泽明那种色彩鲜艳，整体有秩序又有混乱的效果 | 名字+描述 | 40/119 | **1** |
| Q3 | 色彩鲜艳，整体有秩序又有混乱的效果 | 纯描述(无名字) | 74/119 | 37 |
| Q4 | 霓虹夜色，慢门，暧昧的感觉 | 纯描述(无名字) | 68/119 | **1** |

### 核心结论：模型学到了，瓶颈在语料
- **Q4 证明风格理解是真的**：完全没有名字，仅凭"霓虹/慢门/暧昧"就排到第 1，
  Top-8 是王家卫、斯科塞斯、迈克尔·曼、卡朋特 —— 全是霓虹夜戏导演
- **Q3 失败是语料覆盖问题，不是模型问题**：
  用户说黑泽明"色彩鲜艳、有秩序又有混乱"，而我语料给他写的是
  ``monochrome contrast``（黑白）。**语料和用户认知冲突。**
- Q1/Q2 的成功含很大比例的人名匹配（训练确实学会了 中文译名 -> 英文原名）

### 由此得到的关键设计缺陷
**每个导演只给了一个固定签名。** 但导演是多面的：
黑泽明既有 1950s 黑白雨戏（七武士/罗生门），也有 1980s 浓烈色彩（乱/影武者）。
单一签名必然漏掉一半用户的描述方式。

### 下一步：多面签名
每位导演 2-3 个 facet（黑白+色彩 / 早期+晚期 / 静态+动态），每个 facet 生成文档。
这样 Q3 那类描述也能命中。

### 其他数字
- base 模型所有分数挤在 0.797-0.799（完全无区分度，短 query 下坍缩）
- 微调后拉开 0.17-0.48，Q4 最高 0.4822

---

## 十五、多面签名语料 v2（完成）

`corpus_v2.jsonl` 477 doc（base 357 + extra 120），40 位导演追加第二面。
`queries_v2b.jsonl` 477 query（每个 facet 3 条：both/style/name）。
关键：relevant 只指该 facet 的文档 -> 要求区分同一导演的不同面。

### 模板级留出 5 折（v2）
| 指标 | v1 单面 | v2 多面 |
|---|---|---|
| style 前 | 0.2526 | 0.2667 |
| style 后 | 0.7398 | 0.7154 |
| delta | +48.72pp ± 8.44 | +44.87pp ± **4.46** |
| overall 后 | 0.9267 | 0.8623 |

绝对值不可直接比：v2 的 relevant 只含对应 facet（更严格），所以更低是预期的；方差减半是真收益。

### 真实 query 三模型对照（评测量 = corpus_v2 477 doc）
| query | baseline | v1单面 | v2多面 |
|---|---|---|---|
| 王家卫的风格（纯名字） | 57 | **1** | **1** |
| 黑泽明…色彩鲜艳秩序混乱（名字+描述） | 16 | **1** | **1** |
| 色彩鲜艳，有秩序又有混乱（纯描述） | 5 | 2 | 2 |
| 霓虹夜色，慢门，暧昧（纯描述） | 46 | **1** | **1** |
| 黑白、大雨、群像（纯描述） | 1 | 2 | **1** |

### 两个重要更正
1. **Q3 的提升主要来自语料，不是训练**
   baseline 在 v1 语料上排 74 名，在 v2 语料上排 **5** 名。
   -> 语料补上"浓烈色彩/秩序混乱"这一面后，连未训练的模型都能匹配。
   -> **之前把 Q3 归因于"模型学不会"是错的，本质是语料缺面。**
2. **v1 -> v2 在真实 query 上几乎无差别**（只 Q5 从 2 到 1）。
   说明 5 条真实 query 不足以体现多面语料的价值，需要更多真实 query 才能判断。

### 当前能力边界（5 条真实 query）
- 训练后：5/5 全部进前 2 名
- baseline：2/5 严重失败（57、46 名）—— 纯名字映射、霓虹风格词
- **训练的价值集中在"名字映射"和"风格词->作者"**，而"文档覆盖"决定上限

### 下一步
1. **更多真实 query（20-30 条）** —— 当前最大的信息缺口，5 条无法支撑结论
2. 扩日/德/韩（需网络）
3. 加科技域/代码域

---

## 十六、两阶段架构补完：reranker（完成）

网络不可达 HF，无法下载 bge-reranker-base。
解法：用已缓存的 multilingual-e5-small 当骨干自建交叉编码器（零下载）。
`src/train_rerank.py`：query+passage 拼接过编码器 -> mean pool -> Linear(1) -> BCE。

### 协议
模板级留出 5 折；**stage-1 固定用未训练 e5**（隔离 reranker 净贡献）；每 query 3 正 + 4 难负(top-20 内挖)。

### 结果（5 折均值）
| 指标 | rerank 前 | rerank 后 | 变化 |
|---|---|---|---|
| recall@10 | 0.3500 | 0.3710 | +2.10pp |
| mrr@10 | 0.3386 | 0.3725 | +3.39pp |
| top1 | 0.2510 | 0.2813 | +3.02pp |
| 首个相关平均排名 | 2.89 | 2.74 | -0.14 |
（折间噪声大；4/5 折 MRR 升，fold 0 反而退）

### 关键诊断：瓶颈在 stage-1 召回，不在精排
未训练 e5 的召回上限：
| k | recall@k |
|---|---|
| 1 | 0.0832 |
| 5 | 0.2544 |
| 10 | 0.3487 |
| 20 | 0.4472 |
| 50 | 0.6157 |
| 100 | 0.7575 |

- **55.3% 的相关文档根本没进 top-20** -> reranker 再强也救不回来
- 用 top-20 时 reranker 的 recall@10 上限是 0.4472，实得 0.3710
  -> 吃下了剩余空间的 22.6%，方向对但空间本就有限
- 而**已训练**的 bi-encoder recall@10 = 0.7154（见第十三节）远高于未训练 0.3487
  -> 说明提升主要来自 stage-1 训练，reranker 只是边际补丁

### 结论
两阶段架构已完整（召回 + 精排）。**架构不再是瓶颈。**
reranker 在已训练 retriever 之上的增益尚未测（需每折重训 bi-encoder 以免泄漏）。
当前瓶颈：**语料覆盖 + 真实 query 数量**。

### 参数解析器（顺带完成）
`src/parse_prompt.py`：477 条全部解析成功，抽 ar/v/style/duration。
- 字符省 14.4%，**token 省 20.5%**
- 修正：43% 那组是在**短描述**上测的；本语料描述很长(130+字符)所以稀释。
  真实用户提示词更短 -> 生产环境参数占比更高，分离更有价值。

---

## 十七、希区柯克「机制化 facet」实验 —— 本次最重要的发现

假设：多面签名按**机制**拆（可复用画面装置）优于按**情绪**拆（suspense/voyeurism 这类影评术语）。
做法：给 Hitchcock 加 5 个机制 facet × 3 doc = +15 doc，配 10 条**手工用户口吻**中文 query。

三种对照：
- A: v2 模型 @ corpus_v2（无机制文档）
- B: v2 模型 @ corpus_v3（有文档，模型没训过）
- C: v3 模型 @ corpus_v3（文档 + 训练）

| 组 | 平均排名 | 中位 | 前3命中 |
|---|---|---|---|
| A 无文档 | 27.70 | 16 | 1/10 |
| B 有文档未训练 | 2.00 | 1 | 9/10 |
| **C 文档+训练** | **1.00** | **1** | **10/10** |

### 归因分解
- **文档覆盖贡献 (A->B)：−25.70 名**
- **机制训练贡献 (B->C)：−1.00 名**
- -> **语料覆盖占约 96% 的收益，训练只占 4%**

### 为什么有效：描述语言必须和用户同层
旧签名（影评语言）：``suspense framing, subjective camera, high contrast``
  -> 用户说"一个杯子就让人紧张"，与它零重叠 -> A 组排 49 名
新 facet（机制语言）：``a glass of milk carried up a dark staircase lit from below``
  -> 具体名词直接对得上 -> B 组排 2 名

**结论：用影评术语写文档 = 用户永远搜不到。facet 必须用用户会说的那种具体名词来写。**

### 对项目路线的影响（重要）
之前把大量精力放在模型训练/调参（+44.87pp 的 CV）。
但这次证明：**15 条精心设计的文档，比两个月的模型工程效果更大。**
-> 优先级应改为：语料工程 >> 模型工程
-> 每个域/导演/机制都该问："用户会用什么具体名词描述它？"

### 产物
- ``data/raw/corpus_v3.jsonl`` 492 doc / ``queries_v3.jsonl`` 487 query
- ``models/e5-director-v3``
- ``src/build_hitchcock_pack.py`` / ``src/eval_hitchcock.py``
- ``bench/eval_hitchcock.json``

---

## 十八、ComfyUI 部署（完成）

### 架构决策：检索走 CPU
8GB 显存是全系统硬约束。SDXL/Flux 吃 6-8GB，检索模型再占 1GB 必打架。
- e5-small 在 CPU 上编码单条 query 约 50-150ms —— 够用
- 语料 embedding 预计算并缓存为 .npy，启动只加载
- **显存 100% 留给扩散模型**

### 产物
| 文件 | 作用 |
|---|---|
| `src/serve_style.py` | 风格服务，**零第三方依赖**（标准库 http.server） |
| `comfyui/comfyui_style_hint.py` | ComfyUI 节点，**零依赖**（只用 urllib） |

端点：`GET /health`、`POST /style-hint`、`POST /search`（默认 127.0.0.1:8848）

### 实测（CPU，492 doc）
| 中文 query | 命中 | facet | score |
|---|---|---|---|
| 霓虹夜色，慢门，暧昧的感觉 | 王家卫 | base | 0.4421 |
| 一个杯子就让人紧张起来 | 希区柯克 | mech_object_threat | 0.5078 |
| 黑泽明色彩鲜艳、秩序混乱 | 黑泽明 | color_1980s | 0.4838 |
| 远远的镜头，草船在江上，老渔夫在划 | 蔡明亮 | base | 0.3412 |
CPU 与 CUDA 结果**逐位一致**。

### 踩到的坑（重要，会再遇到）
**PowerShell 的 `Invoke-RestMethod -Body <字符串>` 用 ISO-8859-1 编码，中文全变 `?`。**
症状极具迷惑性：不同 query 返回同一批文档、分数只有正常值的一半。
服务端本身没问题 —— 是客户端编码。
正确写法：
```powershell
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
Invoke-RestMethod -Uri $url -Method Post -Body $bytes `
  -ContentType 'application/json; charset=utf-8'
```

### 暴露的语料缺口
「草船/雾江/山水」这类**中国传统影像**在 119 位导演语料里完全没有对应 facet。
系统只能退而求其次命中蔡明亮(slow water) / 塔可夫斯基(water, ruins)。
-> 需要补一包「东方影像」facet（山水画 / 侯孝贤雾江 / 沟口雾中景）

---

## 十九、东方影像 facet 包（完成）—— 又验证一次「语料 > 模型」

背景：草船那条 query 只命中蔡明亮(slow water)/塔可夫斯基(water, ruins)，
      因为 119 位导演语料里完全没有中国传统影像语言。

### 补了什么
10 个中国传统影像范式 + 1 个侯孝贤雾江面，每个 3 doc，共 +33 doc：
| facet | 中文 | 关键签名 |
|---|---|---|
| ink_wash | 文人水墨 | monochrome ink wash, vast empty paper |
| qinglv | 青绿山水 | mineral blue-green pigment, gold outline |
| song_academy | 宋代院体 | meticulous observation, muted silk tones |
| gongbi | 工笔重彩 | fine outline, saturated mineral pigments |
| liubai | 留白构图 | overwhelming empty space, tiny subject |
| wu_jiang | 雾江孤舟 | layered mist, low horizon, one small boat |
| handscroll | 手卷长卷 | extreme horizontal format |
| one_corner | 马一角夏半边 | subject confined to one corner |
| nianhua | 木版年画 | flat woodblock colour, bold outline |
| piying | 皮影 | translucent silhouettes, backlit screen |
| misty_river | 侯孝贤雾江 | very long static shot, misty river |

corpus_v3 (492) -> corpus_v4 (525)；加 22 条手工用户口吻中文 query。

### 结果（22 条东方 query）
| 设置 | 前3命中 |
|---|---|
| v3 模型 @ corpus_v3（无东方语料） | **1/22**（其中 20 条目标"缺席"，系统只能命中蔡明亮/塔可夫斯基/张艺谋等最接近的西方导演）|
| v4 模型 @ corpus_v4（含东方 query 训练 - 有泄漏） | 22/22 |
| **v4-noleak @ corpus_v4（东方 query 完全不参与训练）** | **20/22** ← 可信数字 |

泄漏只值 2 条，效果是真实的。

### 关键个案
「远远的镜头，一条草船在江上，有个老渔夫在划」
- v3: 目标缺席，命中 蔡明亮 / 王家卫
- v4-noleak: **第 2 名，top1=侯孝贤(misty_river) top2=雾江孤舟** ← 正确
用户随口说的一句话，现在能被自己检索出来。

### 仍然失败的两条（诚实记录）
- 「半边虚半边实那种」-> 第 5 名。因为"虚实相生"是画论术语，我的 doc 只写了
  "subject confined to one corner"，没抓住"虚"与"实"的互生关系。
- 「打着灯的影子戏」-> 第 13 名。而「皮影戏那种透光的剪影」是第 1 名。
  同一概念的两种措辞，一种命中一种失败 -> 说明覆盖面仍靠措辞运气。

### 服务已切换到 v4-noleak + corpus_v4

---

## 二十、ComfyUI 本地节点（完成）

新增 `comfyui/local_style_hint.py` —— 自包含节点，不依赖外部服务。

关键点：我们的模型是 118M 文本编码器，**不是扩散模型**，不能放 models/checkpoints/。
它只能以「权重文件 + 自定义节点」的方式安装。

两种形态：
| 文件 | 需要服务 | 说明 |
|---|---|---|
| comfyui/comfyui_style_hint.py | ✅ 要起 serve_style.py | HTTP 解耦，ComfyUI 零依赖 |
| comfyui/local_style_hint.py | ❌ 不要 | 进程内加载，装完即用 |

### 实测（CPU）
- 首次加载（编码 525 条 doc）：**20.0s**
- 后续单次查询：**13–25 ms**
- 显存占用：**0**

### 已记录的真实行为
「霓虹夜色」单独输入 -> 贾樟柯（其 doc 含 `neon night China`）
「霓虹夜色，慢门，暧昧的感觉」 -> 王家卫
-> **短 query 丢掉关键信号，会被字面词吸走。生产环境要提示用户多描述一点。**

### 装进 ComfyUI 的注意
1. 不要重装 torch（ComfyUI 自带匹配版本，我们的模型只推理）
2. 需 pip 装 transformers / tokenizers / safetensors
3. 便携版路径：ComfyUI_windows_portable\python_embeded\python.exe

---

## 二十一、ComfyUI 节点安装踩坑（已修复）

### 现象
节点放进 custom_nodes\prompt_style_local\ 后，ComfyUI 里搜不到，且界面不报错。

### 根因
**ComfyUI 的自定义节点目录必须有 __init__.py**，否则按包导入时抛
FileNotFoundError，被记为 IMPORT FAILED 后静默跳过。
日志里能看到：
    FileNotFoundError: ...\prompt_style_local\__init__.py
    [INFO] 0.1 seconds (IMPORT FAILED): ...\prompt_style_local

### 修复
新增 comfyui/__init__.py，内容是标准入口：
    import os, sys
    _dir = os.path.dirname(os.path.abspath(__file__))
    if _dir not in sys.path: sys.path.insert(0, _dir)
    from local_style_hint import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

已补到 15 个目录（Comfy-Desktop 的 14 个 install + E:\comfyui）。

### 教训
自定义节点的最小可加载单元是「目录 + __init__.py」，
只有 .py 文件不够。以后写 ComfyUI 节点第一件事就是建 __init__.py。

### 实际在用的 install
运行时从进程命令行确认：`F:\Comfy-Desktop\ComfyUI-Installs\hp\ComfyUI`
（命令行是 `python.exe -s ComfyUI\main.py`，相对路径，CWD 在 hp\ 下）

---

## 二十二、ComfyUI 里成功跑出文本（验证通过）

### 实测（通过 ComfyUI HTTP API 提交，端口 8188）
    LocalStyleHint -> ShowText|pysssss
    status: success  completed=True
    outputs["2"]["text"] = "in the style of Hou Hsiao-hsien, very long static shot,
                            misty river with one distant boat, patient framing,
                            muted grey-green air"
这是在用户自己的 ComfyUI（hp 实例）+ 自带 Python 3.13 + CPU 上真实执行的，
不是本地模拟。

### 用户环境实况
- 运行实例: F:\Comfy-Desktop\ComfyUI-Installs\hp\ComfyUI   端口 8188
- 模型目录: F:\Comfy-Desktop\ComfyUI-Shared\models  (364 GB / 59 文件)
- 模型: minimax_h3(video 31.7G) / ltx-2.3-22b(23.5G) / z_image_turbo(11.5G) / flux-2-klein-4b(7.2G)
- text encoders: qwen3vl_32b / gemma_3_12B / qwen_3_4b
- **没有任何常规 SD/SDXL 整包 checkpoint** -> 网上通用的 6 节点最小图套不上

### z_image 源码结论
comfy/text_encoders/z_image.py 确认 Z-Image 用 Qwen3-4B，tokenizer 走 <|im_start|> 模板，
但 CLIPLoader 的 type 列表里没有 z_image 选项（源码中 z_image 挂在 lumina2 分支下）。
-> 手搓 z_image 生成图有风险，未采纳。

### 产物
- comfyui/workflow_text_only.json  (UI 格式，可直接拖入，2 节点)
- comfyui/api_text_only.json       (API 格式，用于命令行验证)
- 已复制到 F:\Comfy-Desktop\ComfyUI-Shared\input\

### 踩坑记录（编码）
命令里直接写中文字面量，经 PowerShell 传输层会被有损编码（出现 ? 与乱码，甚至破坏引号）。
解法：中文值从已知正确的 JSON 文件里按顺序读出，再用 pscustomobject + ConvertTo-Json
（会自动转 \uXXXX 转义，安全）。

---

## 二十三、明天的三件事（用户定的议程）

### 1. 把模型优化得更好
- style 类现在：严格模板留出 CV +48.72pp（0.25 -> 0.74）；真实 query 5/5 进前 2
- 待做：
  - 把 HB 验证过的「雾江/草船」最终描述写进 misty_river facet 当基准 doc
  - 每个 facet 补「同一概念的多种措辞 doc」（现状：一种说法命中、换个说法就掉到 13 名）
  - 补失败案例：半边虚半边实（虚实相生，现排 5）
  - 可选：bge-reranker 蒸馏 / 更多语言

### 2. 让提示词可以互通
含义待确认，可能指：
  - (a) 图像提示词 <-> 视频提示词 互相迁移（corpus 里已有 prompt_image / prompt_video 两类）
  - (b) 跨语法互通：MJ 的 --ar/--v 与 ComfyUI/Sora 的自然语言互转
  - (c) 跨语言互通：中/英/日/德/韩 同一风格词的互相映射
  -> 明天先问清楚是哪一个，再动手

### 3. 让他拥有自己的兴趣
即最早的「主动学习」想法，此前只做了设计未实现：
  - 三信号：margin（模型犹豫）/ novelty（中等距离）/ 教师置信（bge-m3）
  - 铁律不变：数据可以自选，评测绝对不能自选
  - 待写：src/mine_interesting.py、src/active_loop.py
  - 注意 high loss != informative（高 loss 多是噪声/错标，要用 margin 不用 raw loss）

### 当前系统状态（明天从这里起）
- 服务：src/serve_style.py（CPU，0 显存，端口 8848 可改）
- ComfyUI 节点：已装 14 个 install + E:\comfyui，实测执行成功
- 模型：models/e5-director-v4-noleak（无泄漏版）
- 语料：data/raw/corpus_v4.jsonl (525 doc) + queries_v4.jsonl (509 query)
- 工作流：comfyui/workflow_text_only.json（拖进 ComfyUI 即用）
- 待办：把 HB 最终描述入库
