# 数据许可：CC-BY-4.0

本项目的**语料、索引与标注数据**以
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/legalcode)
（CC-BY-4.0）发布。

涵盖范围：

```
data/raw/corpus_v16.jsonl        风格语料（796 条）
data/raw/subjects_v4.jsonl       题材索引（40 条）
data/raw/crafts_v3.jsonl         工艺索引（32 条）
data/raw/materials_v4.jsonl      材质/光索引（109 条）
data/raw/queries_*.jsonl         训练与评测 query
bench/*.json                     评测结果与统计
```

您被允许：

- **共享** —— 以任何媒介或格式复制、分发本数据
- **演绎** —— 修改、转换、以本数据为基础创作

但须遵守：

- **署名** —— 注明来源（见下文）并附许可链接，并**说明是否作出修改**
- **不得增加额外限制** —— 不得以法律条款或技术手段限制他人做许可允许的事
- **无担保** —— 本数据按「现状」提供，不含任何明示或默示担保

## 建议的署名格式

    Anchor (锚) dataset — vertical cross-lingual retrieval for cinematic style prompts
    by <原作者>, licensed CC-BY-4.0
    https://github.com/<repo>  ·  https://creativecommons.org/licenses/by/4.0/

若作出修改，请补充一句：

    Modified from the original: <简述修改内容>

## 需要特别注意的两点

1. **语料描述的是导演/影片的视觉风格**，是对公开作品的风格描述，
   不含任何影像素材本身。转载时请同样不要附加截图或帧。
2. **基座模型不是数据**。`models/` 下的权重以 MIT 发布，见 `LICENSE` 与 `NOTICE`。
   MIT 与 CC-BY-4.0 对模型权重的适用存在争议，本项目采取「权重用 MIT、
   数据用 CC-BY」的分立口径，并在 `NOTICE` 中说明来源。
