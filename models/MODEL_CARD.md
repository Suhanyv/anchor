# 模型卡 · e5-director-c18

> **这个目录里没有权重文件，这是故意的。**
> 权重不进 git（465 MB × 多版本 = 十几 GB），但**可以从数据 + 脚本两分钟重建**。

---

## 一分钟重建

在干净克隆里实测（Windows / CPU / 1.5 分钟）：

```powershell
python src/train_embed.py --epochs 6 --batch-size 32 --lr 2e-5 `
    --dev-ratio 0.01 --select-mode final `
    --corpus  data/raw/corpus_v16.jsonl `
    --queries data/raw/queries_v4_fixed16.jsonl `
    --out-dir models/e5-director-c18
```

```bash
# 或 bash
python src/train_embed.py --epochs 6 --batch-size 32 --lr 2e-5 \
    --dev-ratio 0.01 --select-mode final \
    --corpus  data/raw/corpus_v16.jsonl \
    --queries data/raw/queries_v4_fixed16.jsonl \
    --out-dir models/e5-director-c18
```

重建后直接可用，无需其它步骤：

```
霓虹夜色，慢门，暧昧的感觉  ->  in the style of Wong Kar-wai, saturated neon, ...
从树枝后面看过去，前景有草叶遮挡 ->  in the style of Alfred Hitchcock, a viewer concealed in vegetation, ...
```

---

## 它是什么

| 项 | 值 |
|---|---|
| 基座 | `intfloat/multilingual-e5-small`（118M，MIT）|
| 参数 | 1.18 亿，其中 **81% 是词表 embedding**（250002 × 384）|
| 体积 | 465 MB（fp32）|
| 训练 | 对比学习（InfoNCE + 难负例再挖掘），6 epoch |
| 数据 | `corpus_v16.jsonl` 796 条 + `queries_v4_fixed16.jsonl` 509 条 |
| 生成时间 | 约 1.5 分钟（CPU）/ 40 秒（RTX 4060）|
| 语言 | 中文 query 为主；英文文档侧 |
| 用途 | 风格检索，**不生成内容** |

## 指标

| 基准 | 分数 | 备注 |
|---|---|---|
| 场景锚定 top1 | 55% | ✅ 最接近真实使用 |
| 场景锚定 top3 | 70% | |
| 材质/光（文档级）| 47% | 词面判分，是下界 |
| 关键词锚定 | 83.7% | ⚠️ 与训练分布同源，仅内部回归用 |

**详细缺陷见 `LIMITATIONS.md`，比这张卡重要。**

## 为什么不发权重

1. **可重建**：数据与脚本都在仓库里，两分钟就能复现，发 465 MB 是浪费。
2. **可审计**：别人自己训练一遍，比下载我们的权重更能验证结果。
3. 如果将来确实需要预训练权重，计划放到 Hugging Face Hub
   （本机网络当前无法访问 HF，故暂缓），并在本卡补充链接与 sha256。

## 其它实验版本（不随仓库分发）

| 名称 | 特点 | 场景基准 |
|---|---|---|
| `c14` | 上一版默认（语料含第三方措辞）| 55% |
| **`c18`** | **当前默认，合规改写后** | **55%** |
| `c16b` / `c17zh2` / `c17zh3` | 四语训练（中/日/韩/德）| **45%**（中文退步）|

四语版本的中文场景能力低于默认版本，**不建议直接用**。见 `LIMITATIONS.md` 第五节。

## 许可

MIT（继承基座）。见仓库根部 `NOTICE` 与 `LICENSE`。
