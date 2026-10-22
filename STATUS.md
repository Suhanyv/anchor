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

---

## 二十四、追加议程：图像提示词与视频提示词必须真分开

### 现状问题（已核查）
corpus 里 prompt_image 与 prompt_video 的差别只有两处：
    image: cinematic still, {相同签名}, --ar 2.35:1 --style raw
    video: cinematic video, {相同签名}, --ar 21:9   --duration 5s
-> 风格文本完全相同，只换了 still/video 和宽高比。
-> 且为保持语义干净，参数已从 text_semantic 剔除，导致唯一能区分二者的信号
   也进不了向量空间，检索完全分不出图/视频。

### 与「互通」的关系（关键设计判断）
先分开，才能互通。正确架构是：
    共享语义空间（同一 embedding）      -> 于是能互通（同一句风格词两边都懂）
  + 域标签（结构化过滤，参数不进向量）  -> 于是能分开（要视频还是静态图）

### 要改的四处
1. 视频词汇：镜头运动(slow push-in / tracking / handheld / crane / orbit)、时长、节奏、转场、loop
2. 图像词汇：构图、材质、光照类型、景深、分辨率、渲染质感
3. 参数转为筛选维度：--ar / --duration 不做语义，做结构化过滤
4. 检索端域过滤：query 含「视频/sora/可灵/运镜/秒」-> 只搜 video；含「图/画面/海报」-> 只搜 image；ComfyUI 节点加开关

### 评测要求
必须分域看指标：video query 是否命中 video doc，image query 是否命中 image doc。
不能只看总体平均（会像之前的 both 类一样被饱和掩盖）。

---

## 二十五、主动学习闭环第一轮（挖 -> 补 -> 重训 -> 再挖）

### 挖掘器（src/mine_interesting.py）
三信号（教师置信改为**模型分歧**，因 HF 不通无法下 bge-m3）：
  margin        导演层 第1-第3 分差，小=犹豫
  novelty       query 到最近文档的最大相似度，低=没覆盖
  disagreement  base e5 与微调模型的排名差 + 命中翻转
兴趣分 = 0.40*(1-margin) + 0.30*novelty + 0.30*disagreement，失败再 x1.5

候选池：2100 条，来自 25 套**训练没见过**的新句式（每 facet 12 条）
铁律遵守：只用于指导补语料，不用于判断模型好坏。

### v4 结果（基线）
- base e5 命中@1 17.5%，margin 0.0068（几乎无区分度）
- v4-noleak 命中@1 **82.5%**，margin 0.1505
- 最差 facet：宋代院体 100% / 手卷 83.3% / 留白 75% / 黑白新写实 58.3% / 工笔 50%
- 诊断：这些 doc 全用画论术语写；对照 misty_river 仅 25%（因为写了船雾江渔夫）

### 发现的一个真问题：微调造成回归
兴趣分前 4 名同为「对称、造作」类（Fassbinder expressionist 面）
    base 排名 1  ->  微调后排名 21~27
即微调把原本能对的情况弄坏了 = 灾难性遗忘的直接证据。

### v5 修正（src/build_corpus_v5.py）
原则：不删旧的，只加具体的。给 6 个崩掉的 facet 补 22 条**具体物件** doc。

### v5 结果（对比 v4 失败率）
| facet | v4 | v5 | 判定 |
|---|---|---|---|
| song_academy | 100% | 41.7% | 大胜 -58pp |
| handscroll | 83.3% | 跌出最差20 | 改善 |
| gongbi | 50% | 跌出最差20 | 改善 |
| luminous_bw | 41.7% | 跌出最差20 | 改善 |
| neorealist | 58.3% | 41.7% | 改善 |
| liubai | 75% | 75% | 无变化 |
| misty_river | 25% | 41.7% | 变差 |
| wu_jiang | 25% | 33.3% | 略差 |
| 总命中@1 | 82.5% | 82.9% | 几乎不动 |

### 两次失败的归因（重要）
1. **liubai 75% 不动 = 与 one_corner 语义重叠**，补 doc 无用，被邻居吸走。
   -> 应合并，或明确切分：留白=元素极少；一角=元素偏在边角。
2. **misty_river 变差 = 我加的 doc 抢了信号**。
   给留白加的第一条是 "one small fishing boat at the extreme corner..."，
   而雾江的核心正是「船」。补 A 污染了 B。
   -> 实证了早期预判「域之间会打架」。

### 教训
补语料有副作用，必须**整体看分域指标**；总体命中率被 base facet(1428/2100) 稀释，
82.9% 这个数几乎没有指示意义。

---

## 二十六、压缩实验（int8 与 PCA 降维）—— 一个预测被推翻

### 实测（400 条训练未见的新句式 query，547 doc）
| 方案 | 体积 | 编码ms | 维度 | hit@1 | 变化 |
|---|---|---|---|---|---|
| fp32 原始 | 449 MB | 18.1 | 384 | 0.8625 | - |
| int8 动态量化 | 388 MB | 15.0 | 384 | 0.7425 | **-12.00pp** |
| PCA-256 | - | 18.1 | 256 | 0.8650 | +0.25pp |
| PCA-128 | - | 18.1 | 128 | 0.8575 | -0.50pp |
| PCA-64 | - | 18.1 | 64 | 0.8325 | -3.00pp |

### 推翻的预测
此前判断「int8 可把 470MB 压到约 120MB」。实测只省 14%，且精度暴跌 12 点。
原因：**该模型 81.4% 的参数在词表 embedding**
    词表 250002 x 384 = 96.0M / 总 118M = 81.4%
而 quantize_dynamic(..., {nn.Linear}) 只量化 Linear，**完全没碰词表**。

### 决策
- 放弃 int8 动态量化（省 14% 掉 12 点，不划算）
- 采用 PCA-128（索引减半，精度 -0.5pp，编码速度不变）——为语料上规模做准备
  10 万条时：384 维 154MB -> 128 维 51MB，余弦快 3 倍
- 真要瘦身模型，方向是**词表**不是 Linear：剪词表 / 换小词表底座 / 蒸馏

### 附带发现
PCA 前 10 主成分只解释 5.1% 方差 -> embedding 高维各向同性，
但降维几乎无损 -> 冗余极大。

---

## 二十七、图像/视频真分开（④ 完成）

### 语料 v6（src/build_corpus_v6.py）
- 现有 181 条错标成 prompt_video 的文档改回 prompt_image
- 每组 (director,facet) 追加 2 条视频 doc，加**真正的运镜语言**：
    STATIC  locked-off camera, no cut, one extremely long take, patient stillness
    KINETIC whip pan, rapid cutting, tracking follow, restless handheld movement
    SLOW    slow push-in, gentle handheld drift, focus pulling slowly
  按风格签名自动选（含 static/long take 的给 STATIC，含 kinetic/cutting 的给 KINETIC，其余 SLOW）
- 547 -> 897 doc（image 547 / video 350），运镜分配 STATIC 45 / KINETIC 11 / SLOW 294

### 域路由（src/domain_router.py）
单向信号才判域：只有视频词->video，只有图片词->image，两者都有或都没有->any。
**宁判 any 不过滤，也不判错**——判错会把正确答案整个滤掉，比不过滤更糟。

### 评测（src/eval_domain.py，350 条 query：图 175 / 视频 175）
| 方案 | 域准确率 | 导演准确率 |
|---|---|---|
| A v5 语料 + 不过滤 | 48.29% | 80.86% |
| B v6 语料 + 不过滤 | 69.71% | 81.43% |
| C v6 语料 + 自动判域过滤 | **93.71%** | 80.00% |
- 加视频文档（纯语料）：+21.4pp
- 加自动过滤（纯逻辑）：+24.0pp
- 过滤的代价：导演准确率 -1.43pp（很小）

### 节点级实测（40 组 query）
| 模式 | 视频query->视频doc | 图片query->图片doc |
|---|---|---|
| 不限 | 45% | 88% |
| 视频（强制） | 100% | 0（预期） |
| 图片（强制） | 0（预期） | 100% |
| **自动** | **95%** | **100%** |

### 我自己写的两个 bug（都已修）
1. 节点里 `_allowed_idx` 只认 prompt_image/prompt_video，而调用方传的是 image/video
   -> 不匹配就退化成「全允许」，过滤等于没生效。**症状：三种模式输出完全一样。**
2. `_rank` 只把 "auto" 当自动识别，'自动' 落进字典查不到 -> 退化成 any。
   -> 加固为 ("auto","自动","",None) 都触发自动识别。

### 部署
- 15 个 ComfyUI 目录的节点已更新
- 新工作流 comfyui/workflow_style_hint.json（8 个参数，含「域」）
- 已复制到 ComfyUI-Shared/input，旧 workflow_text_only.json 删除

### 待改进
1. 正式评测里 107 条判成 any 的全是图片 query（模板里有「画面」「静态画面」但不在 IMAGE_HINTS 里）
   -> 补图片提示词，域准确率还能再上一层
2. 运镜分配启发式太粗：294/350 落到 SLOW，应当按 facet 知识分配而不是正则

---

## 二十八、补图片提示词 + 歧义词处理（④ 收尾）

### 关键判断：不能简单把「画面」加进图片词
「画面」在视频语境里极常见（"画面要暗一点"），加进去会把视频 query 误判成图片，
然后**把视频文档全过滤掉**——比不过滤更糟。

### 做法：歧义词单独规则
- 明确图片词扩充：静态 / 立绘 / 画一张 / 一张 / 渲染图 / 图生图 / 动漫 / niji ...
- 歧义词 AMBIG_STILL = [画面, 镜头, 构图感]：
  **仅当没有任何运动词时才计为静态**；有运动词（慢/动/推/摇/移/跟/环绕/秒/帧/切…）则判 any
- VIDEO_HINTS 与 IMAGE_HINTS 都命中 -> any（不变）

### 效果
| | 域准确率 | 导演准确率 | 判成 any 的条数 |
|---|---|---|---|
| 补词前 | 93.71% | 80.00% | 107 / 350 |
| **补词后** | **98.86%** | 80.57% | **11 / 350** |

回归测试：10 条用例（含 3 条歧义用例）全部通过。

### 又一次「测试脚手架错了」
第一次回归测试只过 3/9，原因是期望值写成 image/video，而函数返回 prompt_image/prompt_video。
函数是对的，测试是错的。本项目第三次同类错误：
  1) PowerShell Invoke-RestMethod 用 ISO-8859-1 编码中文
  2) 节点 _rank 只认 "auto"，'自动' 退化成 any
  3) 本次：测试期望值字符串不匹配
共同特征：**看起来像功能坏了，实际是验证工具本身有问题**。

---

## 二十九、中日英三语互通（② 完成第一版）

### 用户定的方向
提示词互通具体指：**中日英三种语言**（不是图像/视频，也不是 MJ 语法）。

### 第一次评测（corpus_v7 + model v7，53 组，文档全英文）
| 语言 | 命中@1 |
|---|---|
| 中文 | 77.4% |
| **日文** | **49.1%**（比中文差 28.3pp）|
| 英文* | 88.7%（用 style_tags，逐字出现在文档里，有词面优势，仅上限参考）|

### 关键发现：语言-国籍混淆
日文失败样例几乎全命中日本/亚洲导演：
    不気味、夢の中      期望 David Lynch  -> Apichatpong（泰）
    長回し、群像        期望 PTA          -> 溝口健二（日）
    自然光、抑制の効いた 期望 Clint Eastwood -> 是枝裕和（日）
    鏡像、日光          期望 Jordan Peele  -> 新海誠（日）
    戦後の廃墟、素朴     期望 Fellini      -> 李安（华）
8 个失败里 6 个是亚洲导演、4 个日本导演。

根因：训练数据只有「中文 query ↔ 英文文档」一种跨语言对，
模型没见过日文→英文的映射，于是把「日文」这个**表面特征**当成了
「日本」这个**语义特征**。

### 修法：零翻译成本
把 516 条日文 query 与**同一批英文文档**配对训练（文档一条没翻）。
    src/build_ja_queries.py -> queries_v8.jsonl = queries_v4(509) + ja(516)
    覆盖 86 个组，6 套日文句式

### 结果（model v8）
| 语言 | v7 | v8 | 变化 |
|---|---|---|---|
| 中文 | 77.4% | **86.8%** | +9.4pp |
| 日文 | 49.1% | **92.5%** | **+43.4pp** |
| 英文* | 88.7% | 96.2% | +7.5pp |
日中差距：日文落后 28.3pp -> 日文反超 5.7pp（46/53 vs 49/53）

中文也跟着涨 9.4pp：日文训练对起了正则化作用，模型不能再用语言表面特征抄近路。

### 残留
4 个日文失败里仍有 1 个被拉向日本导演（正確な構図、モノクロ -> 小林正樹）。
原因：日文对照只覆盖约 150/401 个关键词、86/175 个组。扩表可继续缓解。

### 端到端（节点实测，v8 + corpus_v7）
    霧の川、孤舟、遠山        -> 雾江孤舟  0.6013
    逆光、暖かい光            -> Spielberg 0.6342
    ネオンの夜、スローシャッター -> Scorsese 0.5433
    余白、要素が極少          -> 留白构图  0.7248
4/4 正确，且日文 query 命中了中文命名的东方 facet。

### 重要提醒：v8 不能用于声称泛化
v8 用全部 query 训练（含东方手工 query）。所以：
    实际部署      -> 用 v8（性能最好）
    对外声称泛化  -> 只能用 v4-noleak / v5 / v7 的留出实验数字
v4-noleak 的意义就是证明「不是背下来的」。v8 用可验证性换了性能，
这是有意的取舍，但不能混着说。

---

## 三十、三语互通第二版：对照表补全到 401 词 / 175 组

### 补全（src/ja_lexicon.py）
中→日对照表独立成模块（原来长在 eval_3lang.py 里，导致评测脚本变成数据依赖）。
覆盖 corpus_v7 全部 **401 个关键词**，可覆盖 **175/175 组**。

### 关键验证：v8 的数字没有被覆盖率吹大
上一轮的担心：v8 的 92.5% 只在 53 个组上测，而那 53 组正好是「词被翻过」的组
-> 测试集与训练覆盖重合，数字可能虚高。

补全后在全部 175 组上重测：
| 版本 | 覆盖 | 中文 | 日文 | 英文* |
|---|---|---|---|---|
| v7 初测 | 135词/86组 | 77.4% | 49.1% | 88.7% |
| v8 加日文训练 | 135词/53组评测 | 86.8% | 92.5% | 96.2% |
| **v9 全量表** | **401词/175组全测** | 85.7% | **93.1%** | 97.1% |

-> 日文 92.5% -> 93.1%，**没掉**。覆盖率偏倚没有实质影响。

### 国籍偏置基本消失
加训练前 8 个失败里 6 个拉向亚洲导演（Apichatpong / 溝口 / 是枝 / 新海誠）；
现在 8 个失败里只剩 1~2 个涉及亚洲，且方向也变乱（有日本目标被西方抢走）。
剩余的错是「西方导演之间混」（Malick->Godard、Bresson->Bergman），属正常细粒度难题。

### 新发现：中文训练量反而不够
日文 93.1% > 中文 85.7%。原因不是中文难，是喂得少：
    中文 509 条 query，句式少（复用旧数据）
    日文 1050 条（6 套句式 x 175 组）
-> 下一步：按同样方式给中文生成多句式 query。

### 模型清单（重要区别）
| 模型 | 用途 |
|---|---|
| e5-director-v4-noleak | **对外声称泛化能力只能用这个**（东方 query 完全不参与训练）|
| e5-director-v7 | facet 重整后的留出版本 |
| e5-director-v9 | **实际部署用这个**（全量训练，性能最好，但不能用于泛化声明）|

---

## 三十一、三语互通定稿：拆掉自己的评测泄漏，得到真实数字

### 发现的问题（自己埋的）
eval_3lang 的评测句式（T_JA/T_ZH）与 build_ja_queries 的训练句式**是同一批**。
-> 93.1% 是「见过的句式」，不是「没见过的说法」。
与最早那次模板坍缩（119 条 query 两两余弦 0.9385）同一类问题。

### 修法
新增 src/lang_templates.py，把训练句式与评测句式**严格隔离**，并内置自检：
    TRAIN_ZH(6) / TRAIN_JA(6)  <- build_mlq.py 消费
    EVAL_ZH(4)  / EVAL_JA(4)   <- eval_3lang.py 消费
    _check_no_overlap() 断言两组零重合（含去标点规范化后比较）

### 同时补齐中文训练量
v9 时中文只有 509 条、日文 1050 条 -> 中文被反超不是能力问题而是喂饭不均。
src/build_mlq.py：中日各 6 套训练句式 x 175 组 = 各 1050 条。
queries_v9.jsonl = 旧中文 509 + 新中文 1050 + 日文 1050 = 2609 条。

### v10 结果（评测句式全部留出，175 组全测）
| 语言 | v9（句式见过）| v10（句式留出）|
|---|---|---|
| 中文 | 85.7% | **89.7%** |
| 日文 | 93.1% | **89.7%** |
| 英文* | 97.1% | 97.1% |
中日完全持平。中文真涨 +4.0pp；日文 93.1%->89.7% 是**假数字被修正**，不是退步。

### 错误性质的变化
加训练前：8 个失败里 6 个拉向亚洲导演（语言->国籍混淆）
现在：8 个失败里只剩 1 个国籍相关，主流错误变成「风格相近的西方导演之间混」
（Malick<->Godard、Wes Anderson<->George Miller、Ari Aster<->Lars von Trier）
-> 已从语言问题降级为内容层面的细粒度问题。

### 部署默认已切到 v10（serve_style.py + ComfyUI 节点）
注意：v10 全量训练，**不能用于对外声称泛化能力**。
泛化数字只能用 e5-director-v4-noleak / v5 / v7 的留出实验。

---

## 三十二、澄清：王家卫查询没有退步（是我输入打错字）

### 现象
用 v10 端到端测试「霓虹夜色，慢门，暧昧的感觉」时命中了 Apichatpong，
看起来像招牌 query 退步了。

### 查证
实际测试时把「暧昧」(\u66a7\u6627) 打成了「暈昧」(\u6688\u6627)。
用正确输入重测四个模型：

| 模型 | 王家卫排名 | 分数 | 第 2 名分数 |
|---|---|---|---|
| v4-noleak | 1 | 0.4430 | 0.3358 |
| v7 | 1 | 0.4369 | 0.3906 |
| v9 | 1 | 0.4218 | 0.3931 |
| v10 | 1 | **0.5540** | 0.4645 |

四版全部第 1 名，v10 领先幅度最大 -> **没有退步**，v10 反而最干净。

### 记一笔：本项目脚手架错误清单（5 次）
| # | 错在哪 | 表现 |
|---|---|---|
| 1 | PowerShell Invoke-RestMethod 用 ISO-8859-1 发中文 | query 变 ?，分数腰斩 |
| 2 | 节点传 '自动'，_rank 只认 "auto" | 过滤静默失效 |
| 3 | 测试期望值写成 image 而非 prompt_image | 9 条过 3 条 |
| 4 | kw_zh 混入域词（运镜/视频） | 命中率 82.9% -> 26.2% |
| 5 | 测试输入打错一个字（暈昧/暧昧） | 招牌 query 疑似退步 |

共同特征：**验证工具本身错了，却看起来像系统坏了**。
每次要判断「模型好没好」，就引入一层新判断代码，而那层代码没被验证过。
-> 现在的习惯：任何异常结果，**先验证输入，再怀疑模型**。
这五次全靠「拿真实输出对账」抓出来，而不是相信报告里的数字。

---

## 三十三、实体边界修复（v8c，总命中 83.0% 新高）

### 先做消融，推翻自己的归因
上一轮把 song_academy 41.7%->100% 归因于「视频文档重复稀释」。**没测过就归因，是错的。**
消融：corpus_v7(906,350视频) 81.2%  vs  corpus_v7_img(556,无视频) 82.7%
-> 视频文档代价只有 1.5pp，远不能解释 58pp 的跳变。归因错误。

### 真正的诊断（src/diag_confusion.py）
liubai 失败 9/12，**全部 9 次都流向 one_corner**（100% 单向碾压），one_corner 失败 0/12。
原因：one_corner 签名含 "almost blank pale field"，字面就是「空旷」；
     liubai 只靠 "centred" 一个词区分，太弱。
wu_jiang 失败 7/12 -> handscroll:3（远山撞长卷）、base/Herzog:3（雾撞丛林雾）、misty_river:1
     （原以为和侯孝贤互抢，实际是「远山」「雾」被别的实体抢走）
song_academy 失败 11/12 -> gongbi:4（同为中国传统绘画，边界不清）

### 修法：签名改成正交（src/build_corpus_v8.py）
| facet | 新签名（只占一个概念） |
|---|---|
| liubai | emptiness on all four sides, one small subject at dead centre |
| one_corner | subject entering from one corner only, everything else left bare |
| wu_jiang | distant mountains half dissolved in mist, one lone boat on a wide still river |
| song_academy | imperial academy scroll, precise study of a bird or plant on silk |
| gongbi | hairline outline filled with flat mineral colour, decorative symmetry |
另：视频文档 350 -> 175（每组 1 条），拿回 1.5pp。
9 个重建 facet 两两签名共享词检查：仅 liubai/one_corner 共享 "subject"（可接受）。

### 附带修的坑
corpus_v8 删了 32 条旧文档并换新 doc_id，queries_v4 里 10 条手工东方 query
的 relevant 指向已删 id -> train_embed 报 KeyError: 'd0514'
-> 新增 src/repair_queries.py，逐级回退（原 id -> 同 director+facet -> 同 director -> 丢弃）

### 结果
| facet | v4 | v5 | v7 | **v8c** |
|---|---|---|---|---|
| song_academy | 100% | 41.7% | 100% | 41.7% |
| liubai | 75% | 75% | 75% | **33.3%** |
| wu_jiang | 25% | 33.3% | 58.3% | **0%** |
| neorealist | 58.3% | 41.7% | 58.3% | 16.7% |
| handscroll | 83.3% | 16.7% | 16.7% | 8.3% |
| 总命中@1 | 82.5% | 82.9% | 81.2% | **83.0%** |
混淆确认消失：liubai->one_corner 9/9 -> 0/4；wu_jiang 7/12 失败 -> 0/12。
liubai 剩余失败流向 ink_wash（文人水墨）——不是 bug，留白本就是文人画核心理念。

### 新发现的问题
1. **rural_realism 12/12 全错**，实测流向 Satyajit Ray(0.5277) / Clint Eastwood / Rossellini，
   张艺谋只排 2~4 名。
   -> 不是模型错，是**我给的 facet 错了**：「乡土写实+朴素+尘土地光」全球最贴切的是
      雷伊（阿普三部曲）。张艺谋的辨识度在饱和红金，不在朴素。
   -> 修法待定：给该 facet 加红金特征（红轿子+高粱地+尘土金光），或直接删掉这个面。

2. **diag_confusion.py 系统性漏报**（只报 6 个 facet，mining 报十几个），
   与 mine_interesting 结论矛盾，已实测确认 mining 正确。
   -> 第 6 个脚手架 bug，暂停使用该脚本，勿据其结论改语料。

---

## 三十四、张艺谋的乡村面重定义为「红高粱」（v9 / c9）

### 归属核查结果
    乡土写实 / 尘土地光  -> 只有张艺谋用（无冲突）
    朴素                -> 费里尼 / 陈凯歌 / 张艺谋 共用
    雷伊的关键词         -> 人文 / 乡村 / 自然光

结论：不是词归属错，是**词太泛**。
「乡土写实/朴素」译成英文就是 earthy rural naturalism / plain，
而雷伊文档里写着 village / natural light -> 语义上确实更像他。
张艺谋真正的标识是**大红**（base 面 kw = 大红/对称/群像），而我偏偏在乡村面里把红丢了。

### 做法（src/build_corpus_v9.py）
facet: rural_realism -> **red_sorghum**
    kw   : 乡土写实/尘土地光/朴素 -> 红高粱/乡野/尘土金光   （红高粱为张艺谋独有）
    签名 : dusty golden light, bold red cloth and sorghum across an open field
    场景 : 红轿子过土路 / 高粱地与红布条 / 农夫与牛与红布 / 砖院挂红辣椒
删除旧 rural_realism 4 条（含 1 条视频），新增 5 条（含 1 条视频）。
同时补日文对照：红高粱->高粱、乡野->田園、尘土金光->埃の金光。

### 结果
| | v8c | c9 |
|---|---|---|
| 总命中@1 | 83.0% | **83.7%** |
| red_sorghum 失败率 | 100%（原 rural_realism）| 跌出最差列表 |
| liubai | 33.3% | 41.7%（略退）|
| song_academy | 41.7% | 33.3%（略进）|

### 必须说清的一点：这 +0.7pp 主要是基准修正，不是模型进步
改了 facet 定义 -> 该组的 12 条 query 全部换了（朴素/尘土地光 -> 红高粱/乡野）。
12/2100 = 0.57%，与涨幅 0.7pp 相当。
真实结论：**那 12 条失败从来不是模型失败，是我的测试问错了问题。**
「朴素、尘土地光」全球范围内正确答案是雷伊，算作张艺谋的失败属于规格错误。
这是修我写错的规格，不是改测试迁就模型——但必须如实标注，不能混进模型收益里。

---

## 三十五、第一条真实 query 暴露的两个产品级问题

### 用户 query
「我想要一个中世纪骑士，骑马在麦田狂奔的镜头」

### 问题 1（产品级）：输出里没有主体
节点只输出风格：
    in the style of Ridley Scott, sun-baked historical epic, dust and gold, vast desert scale, warm amber haze
knight / horse / wheat / medieval 全部不在里面。
-> 直接粘进 CLIPTextEncode 会画出一片沙漠，**没有骑士、没有马、没有麦田**。
这是接线设计上的错误：节点直连 CLIPTextEncode，但只给风格不给主体。
修法：新增参数「包含原文」（默认 是），输出变为
    {用户原文}, in the style of ...
用户原文保持中文不翻译（无离线翻译器，且现代视频模型能吃中英混排）。

### 问题 2：域路由把「狂奔的镜头」判成静态图
「镜头」在歧义词表里，而「狂奔」不在运动词表。
修法两层：
  a. 运动词表补 狂奔/奔跑/奔驰/疾驰/骑马/翻滚/穿过/掠过 等
  b. 新增规则：强运动词 + 「镜头/画面」-> 判视频
      （因为「镜头」单独是歧义，但「狂奔的镜头」明确是运动的镜头）

### 踩到的坑：单字「骑」会匹配「骑士」这个名词
先加了 "骑"，导致「骑士的盔甲细节」也被当成运动词。
-> 改用 "骑马"（双字），回归测试确认「骑士的盔甲细节」判 any 正确。

### 一处我改测试而非改代码
「骑马追赶」-> 我期望 prompt_video，实际 any。
想清楚后确认 any 才对：一句话没说清要静态图还是视频，
判成视频会排除图片文档，反而可能错。按「宁 any 不判错」原则保留 any。
**这是改测试迁就代码吗？不是**——是原先的期望值本身就违背了既定原则。

### 顺带证实：检索方向是对的，只是分数诚实
    1. Ridley Scott [sunbaked_epic] 0.3083  -> 天国王朝/角斗士，历史史诗
    2. Terrence Malick 0.2608                -> 天堂之日，全片麦田
    3. George Miller [KINETIC] 0.2403        -> 狂奔的速度感
三个都在点上。正常 query 分数是 0.55~0.60，这里只有 0.31，
这个低分是**诚实的**：语料里没有中世纪/骑士/马，它在说「我知道方向，但我没有素材」。

### 部署
节点参数 8 -> 9，工作流已重生成并同步，15 个 ComfyUI 目录全部更新。

---

## 三十六、加入「内容题材」维度（第二条通道）

### 用户需求
「我想要一个中世纪骑士，骑马在麦田狂奔的镜头」
—— 这是**内容题材**，而现有语料全是**导演风格**。
用户明确要求：加入内容题材。

### 架构决定：题材独立索引，不混进风格索引
依据：之前把 350 条视频文档塞进风格索引，消融实测风格精度掉 1.5pp。
题材词（骑士/唐代/赛博）与风格词（对称/深焦）混在同一空间会互相抢。
    query ─┬─> 风格索引(175 个导演面) -> "in the style of Ridley Scott, ..."
           └─> 题材索引(20 题材/40 文档) -> "a knight in plate armour on a horse"
    输出 = 题材短语 + ", " + 风格串

### 题材库（src/build_subjects.py -> subjects_v1.jsonl）
20 个题材 x 2 条英文变体 = 40 文档：
中世纪骑士 / 中世纪战场 / 唐代宫廷 / 民国上海 / 武侠竹林 / 赛博朋克都市 /
太空船内 / 水下 / 雪原 / 沙漠商队 / 废墟城市 / 麦田 / 旅馆走廊 / 雨夜街道 /
老式厨房 / 空教室 / 教堂内部 / 集市人群 / 老人特写 / 奔马

### 关键设计：题材是否拼入用**相对判据**
先试绝对阈值 0.42 -> 把正确答案挡掉（中世纪骑士只有 0.3620）。
原因：题材文档是短句，与 e5 的相似度天然低于长描述的风格文档。
改为比较两条通道谁更贴合：subject_score >= top_style_score * 0.95
六条实测：
| query | 题材 | 题材/风格 | 拼入 | 判定 |
|---|---|---|---|---|
| 中世纪骑士+麦田+狂奔 | 中世纪骑士 | 1.47 | ✅ | 对 |
| 两个剑客在竹林里对峙 | 武侠竹林 | 1.51 | ✅ | 对 |
| 唐代宫殿里的宫女 | 唐代宫廷 | 1.26 | ✅ | 对 |
| 老人坐在客厅窗外下雨 | 雨夜街道 | 1.15 | ✅ | 合理 |
| 霓虹夜色，慢门，暧昧 | 雨夜街道 | 0.63 | ⛔ | 对（不该拼）|
| 磁悬车+赛博朋克大楼 | 太空船内 | 0.60 | ⛔ | 排除对了但没认出 |

### 用户那条 query 的最终输出
    a knight in plate armour on a horse, castle walls behind,
    in the style of Ridley Scott, sun-baked historical epic,
    dust and gold, vast desert scale, warm amber haze

### 节点变化
参数 9 -> 10：新增「题材文件」；「包含原文」默认改为 否
（题材通道已给英文主体，不必再塞中文原文；想保留原话时再打开）。
工作流已重生成并同步，15 个 ComfyUI 目录全部更新。

### 待改进
1. 赛博朋克那条没认出来（题材分 0.2469，题材库里的 Cyberpunk Street 没赢）
   -> 题材库需要更多同义表达，或补中文关键词参与匹配
2. 题材库的 ja 对照未补（三语评测暂不涉及题材通道）

---

## 三十七、图像 / 视频输出形态分开

### 之前只做了「检索哪一批」，没做「输出长什么样」
域路由只决定搜 image doc 还是 video doc，两种输出文字结构完全一样：
    subject + in the style of <director>, <tags>
视频没有运镜和时长，图像没有静帧和清晰度。

### 现在按域分开收尾语言
| 域 | 追加的收尾 | 调试信息里报出 |
|---|---|---|
| 视频 | MOTION_EN[motion]：STATIC=locked-off camera, one unbroken take / KINETIC=fast handheld tracking, quick cuts / SLOW=slow push-in, steady drift | 运镜类型 / 建议时长 / 建议宽高比 21:9 |
| 图像 | still frame, sharp focus, fine detail | 建议宽高比 2.35:1 |
| 判不准(any) | 按图像形态输出，并提示「想生成视频请在『域』里选视频」 | 明确说明 |

### 实测对比（同一条描述）
域=视频：
    ..., warm amber haze, slow push-in, steady drift
    【视频形态】运镜=SLOW  建议时长=5s  建议宽高比=21:9
域=图片：
    ..., warm amber haze, still frame, sharp focus, fine detail
    【图像形态】建议宽高比=2.35:1
自动：「狂奔+镜头」-> 视频；「画面+海报」-> 图像；「年画那种大红大绿」-> 图像+未判定提示

### 设计决定：宽高比/时长不塞进提示词
用户实际用豆包/可灵这类，尺寸和时长是**独立参数**，不是 prompt 里的 --ar。
所以只在调试信息里给出建议值，保持提示词干净可复制。

### 部署
15 个 ComfyUI 目录已更新，参数数仍为 10（未新增开关）。

---

## 三十八、第一条真实视频提示词：结构与缺口分析

### 用户给的样本（253 词，已存 data/raw/prompt_real_01.txt）
主题：女骑士骑战马穿过野草原走向镜头，镜头藏在草丛树枝后偷看，她突然发现并直视镜头。

### 体量对比（实测）
    用户这条        253 词
    我们语料一条 doc  平均 27 词（中位 25，最长 48）
    -> 9.3 倍

### 结构对比：用户有 8 个功能槽，我们只有 1~2 个
| 槽位 | 用户 | 我们 |
|---|---|---|
| 开场主体 | ✅ | ✅ |
| 引用参考图 x2（护甲/发型/脸部表情）| ✅ | ❌ |
| 姿态/道具细节（剑挂腰不拿手里）| ✅ | ❌ |
| 排除约束（not held / hold reins naturally）| ✅ | ❌ |
| 镜头视角+叙事逻辑（躲在草丛，像有人偷看）| ✅ | ❌ |
| 叙事动作（突然发现，直视镜头）| ✅ | ❌ |
| 画幅 16:9 | ✅ | 建议值 |
| 光线（金色阳光透树、深影）| ✅ | 风格标签里 |
| 质量尾串（ultra realistic, 8K, DOF）| ✅ | ❌ |

### 重要认知：我们的系统不该假装能生成这种提示词
用户那条是**自己导演好的一场戏**。叙事、调度、参考图、约束都是创作，不该由检索去猜。
我们的真实价值是**其中一个槽**：氛围/影调/风格的准确命名。

### 但确实扒出了语料缺口（这是最大收获）
用该提示词的机制核心做中文 query 测试：
    「偷看+被发现」-> Hitchcock 第 1 名 0.3695  ✅
    「从树枝后面看过去，前景有草叶遮挡」-> 手卷长卷 0.3423  ❌ 完全跑偏
查语料原因：我们所有窥视文档都是**隔窗偷看**
    a grid of apartment windows at dusk with one lit window, telephoto compression
而用户的机制是**躲在植被里偷看**
    hidden behind wild grass and tree branches / leaves and blades of grass partially block the frame
-> 两种不同机制，后者完全缺失。不是模型笨，是没这个知识。

### 修复
新增 facet mech_hidden_observer（藏在植被里的观察者）归 Hitchcock，
用**用户自己的措辞**写 4 条图 + 1 条视频：
    voyeuristic perspective, foreground foliage partially blocking the frame, caught watching
    a figure watched from behind tall grass and leaves that blur the foreground
    the subject suddenly notices and looks straight into the camera, caught watching

### 结果（corpus_v10 / model c10）
| query | 修前 | 修后 |
|---|---|---|
| 从树枝后面看过去，前景有草叶遮挡 | 手卷长卷 0.3423 | **Hitchcock [mech_hidden_observer] 0.3802** |
| 偷看+被发现 | Hitchcock base 0.3695 | **Hitchcock [mech_hidden_observer] 0.4471** |

### 同时修掉题材误报
只靠「题材/风格 >= 0.95」会误报：该 query 拼进了「沙漠商队」（比值0.99）。
新增绝对下限 SUBJECT_FLOOR=0.36（实测校准，样本少，标为经验值）：
    中世纪骑士 0.4945 ✓ / 唐代宫廷 0.5070 ✓ / 武侠竹林 0.4813 ✓ / 老人 0.4168 ✓
    沙漠商队误报 0.3378 ✗ / 跑偏那条 0.2042 ✗

### 泄漏声明
本条提示词的措辞已用于建语料，**不再是留出样本**，文件标注已改。
以后不能用它测效果。下一条真实提示词才可当留出样本。

### 从这条提示词学到的语言规律
用户写提示词时用的是**机制词**而不是影评词：
    voyeuristic perspective / caught watching / hidden observer / battle-worn weathered metal
这与本项目反复验证的结论一致：**用具体机制描述，不用评论术语**。

---

## 三十九、场景锚定评测：83.7% 是虚的，真实 60%

### 为什么要建新基准
用户给了两条真实提示词（各 253/255 词）。用中文描述其场景去查，发现严重问题：
    用户明确写了 "Denis Villeneuve style"，但用中文描述该场景时 Villeneuve 前 5 都进不去，
    第 1 名是「雾江孤舟」（一条中世纪骑士 query 被东方实体抢走）。

### 根因：我的基准测的不是这件事
现有 2100 条 query 全部用 facet 自己的 kw_zh 造（「留白、空旷」「雾江、孤舟」），
所以它们**天然会命中对的实体**。
-> 83.7% 测的是「关键词能不能路由到实体」，不是「能不能听懂一个场景」。

### 新基准：src/eval_scene.py
规则：query 用中文口语描述场景，**不含 facet 关键词**；标注一个或多个可接受答案；
指标 = 可接受答案中最好那个的排名。
15 题来源：prompt_real_01/02 拆解 7 题 + 东方应命中 4 题 + 通用 4 题。

### 结果（corpus_v10 / model c10）
    top1  9/15 = 60%
    top3 10/15 = 67%
    top5 10/15 = 67%
对比关键词锚定基准的 83.7% —— **差 24pp**。

### 失败明细（真实缺口）
| 场景 | 实际 top1 | 期望 | 期望排名 |
|---|---|---|---|
| 女骑士全速疾驰，远景全身 | 手卷长卷 | Villeneuve | 15 |
| 广阔荒原孤独骑士，人很小 | 雾江孤舟 | Villeneuve | 8 |
| 钢铁盔甲反光，侧光深影冷硬 | 塔可夫斯基 | Villeneuve | 26 |
| 两人面对面，房间完全对称 | 希区柯克 | 库布里克 | 8 |

### 成功明细（可信的部分）
    偷看+被发现 -> Hitchcock #1
    树枝遮挡视线 -> Hitchcock #1
    突然转头直视镜头 -> Hitchcock #1
    雨夜霓虹积水 -> 王家卫 #1
    一个杯子光从下打上来 -> Hitchcock #1
    绢本花鸟笔很细 -> 宋代院体 #1
    大片空白中间一个小东西 -> 留白构图 #1
    云雾江面小船远山 -> 雾江孤舟 #1
-> 机制类与东方类很准，西方导演的画面感很差。

### 根因：三个「通用磁铁」
    手卷长卷  "continuous unfolding landscape"  <- 一切"横向展开的景"被吸走
    雾江孤舟  "lone + distant + misty"          <- 一切"孤独遥远"被吸走
    留白构图  "emptiness all around"            <- 一切"空/小主体"被吸走
这些签名太通用，必须**锚定到自身媒介与内容**（纸、墨、卷轴、船、江、绢），
不能只描述"空旷孤独"。这是我上一轮"改成正交签名"时用力过猛造成的副作用：
为了和 one_corner 区分，把 liubai 写成了纯"空旷"，反而变成通用磁铁。

### 评测自身的 bug（要修）
第 12 题「红柱子、宫灯、讲究的唐代宫廷」期望 Tang Court，但 Tang Court 属于**题材库**
（subjects_v1.jsonl），不在风格语料里 -> 风格检索必然找不到。此题为评测设计错误，不算模型失败。

### 下一步
1. 东方三实体签名锚定到媒介（纸/墨/绢/船/江），去掉通用"空旷孤独"表述
2. 给 Villeneuve 的 dust_epic / base 补钢铁、盔甲、巨型地景的具体语言
3. 场景评测分两段：风格段查风格语料，题材段查题材库（修 bug）
4. 以后**同时报两个数**：关键词锚定（内部回归）+ 场景锚定（对外真实）

---

## 四十、真实提示词 04：中文分镜脚本（第三种体裁）

### 体裁分裂
| 样本 | 体裁 | 语言 | 体量 |
|---|---|---|---|
| 01 / 03 | 英文场景描述（含 OCR 噪声）| 英 | 253 / 251 词 |
| 02 | 英文场景描述（标注为图像）| 英 | 255 词 |
| **04** | **中文分镜脚本（章节+时间轴+音效+负面约束）** | 中 | **1516 中文字** |

### 04 的结构（实测）
    5 段时间轴：0.0-0.1 / 0.1-1.2 / 1.2-2.6 / 2.6-3.8 / 3.8-5.0 秒
    9 条负面约束
    11 个功能块：参考图角色 / 视频目标 / 核心主体与质感 / 音效建议 /
                空间环境与光影 / 镜头语言与运镜 / 逐秒动态流程 / 负面约束 /
                No BGM / 首帧规则(不能从静止开始) / 面部清晰度约束

### 关键量化：这 1516 字里我们最多能贡献 4.9%
| 功能块 | 字数 | 占比 |
|---|---|---|
| 输入图片说明(参考图锁定) | 288 | 19.0% |
| 视频目标 | 145 | 9.6% |
| 核心主体与质感 | 193 | 12.7% |
| 感官与音效建议 | 120 | 7.9% |
| **空间环境与光影（★风格）** | **75** | **4.9%** |
| 镜头语言与运镜 | 154 | 10.2% |
| 动态流程(时间轴) | 358 | 23.6% |
| 负面约束 | 174 | 11.5% |
-> **我们的系统是「风格命名器」，不是「提示词生成器」**，最多负责其中 5%。

### 检索实测（从脚本蒸馏 3 条中文 query）
| query | top1 | 判定 |
|---|---|---|
| 武侠电影，雪林里一个女子拉弓搭箭，冷白风雪，高速动态 | 奉俊昊 cold_industrial 0.4071（徐克第2 0.3627）| 不准，但徐克第2算接近 |
| 冷白的雪光，雪粒横飞，远山在雪雾里若隐若现，泛光漫射柔焦 | 赫尔佐格 0.3303（韦斯·安德森 winter_monochrome 第2）| 不准 |
| 近距离广角，跟拍推进，前推追踪扫拍，转身时雪幕遮挡 | **Hitchcock [mech_hidden_observer] 0.4429** | 误报 |

### 由此暴露的三个缺口
1. **缺胡金铨（King Hu）** —— 武侠片最该有的导演，语料里完全没有。
   现有武侠类只有：徐克 base(武侠/飘/山雾)、李安 wuxia_color(武侠青绿/飘逸/竹林)
2. **winter_monochrome（韦斯·安德森雪景）是雪景磁铁** —— 一切"雪光/冷白"都被吸走
3. **我 1 小时前刚加的 mech_hidden_observer 变成了"遮挡"磁铁** ——
   "雪幕遮挡"是转场手段，"树叶遮挡"是偷窥视点，机制不同却被匹配。
   又一个"补一个坑造一个磁铁"的案例，而且发生得极快。

### 结论与取向
用户不需要我们生成他的分镜脚本——他自己写得很完整。我们需要做的是：
1. 补胡金铨这类**缺失的东方导演**
2. 给磁铁类实体加**媒介/机制锚定**，别再当通用词吸盘
3. 明确对外表述：这是**风格命名器**，不是提示词生成器
