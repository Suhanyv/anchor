# 外部提示词库的使用说明

本目录记录我们从**开源提示词库**中提取的词汇统计，以及使用条款。

## 用到了什么

| 来源 | 用途 | 许可 |
|---|---|---|
| [水仙的AI提示词](https://github.com/BaYue-SYJ/shuixian-prompts) | 只提取**工艺/材质词表**做覆盖度对照 | 署名使用协议：可学习 / fork / 非商业转载，**须保留出处并链接回仓库**；提示词原文版权归各自原作者 |

## 没有用到的

- **没有复制任何提示词的原文进我们的语料。**
- 原始抓取内容（*.txt）**不入 git**，见 .gitignore；仅本地保留供复核。
- 我们加入 corpus_v16 的描述文本，全部由本项目自行撰写。
  其中「藏在植被里的观察者」这一机制来自于一条网络上流传的提示词，
  但**措辞已完全重写**（作者不明，无法署名，故只能改写而非引用）。

## 如何复核

    # 重新抓取（需能访问 raw.githubusercontent.com）
    curl -L -o data/raw/external/shuixian_part1.txt \
      https://raw.githubusercontent.com/BaYue-SYJ/shuixian-prompts/main/shuixian-unified/data/prompts.part1.json

    # 重新生成词表统计
    python src/extract_craft_vocab.py

## 派生结果（已入库）

- ench/external_vocab_v2.json —— 69 个概念的外部频次 vs 我们语料覆盖
- ench/external_craft_vocab.json —— 26 个工艺词，缺 20 个的对照
