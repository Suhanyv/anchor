# 输出格式

同一个镜头，**不同平台要不同格式**。提示词不是一个字符串，是面向某个平台的表达：
格式错了，内容再对也是白给。

节点参数 `输出格式` 决定走哪套模板。

---

## 一、格式清单

| 输出格式 | 用于 | 语言 | 有时间轴 | 备注 |
|---|---|---|---|---|
| **片段（英文）** | 任何 | 英文 | 无 | 一行逗号串，直接接在主体后面 |
| **结构化（英文）** | 任何 | 英文 | 视频有 Action 行 | 分栏文本，人在看的 |
| **Seedance 2.5（中文）** | 视频 | 中文 | **有** | 五段式：【主体】【风格】【时间线】【BGM】【限制】|
| **MiniMax H3（中文）** | 视频 | 中文 | 段落里含 | 中文自然语言一整段，不编号 |
| **SD 正负向（英文）** | 图像 | 英文 | 无 | `Positive:` / `Negative:` 两行 |

域与格式不匹配时会**自动回落**并在调试里说明，例如：

```
【格式】Seedance 是视频格式，当前是图片域 -> 回落到结构化
```

---

## 二、视频 vs 图像：结构本来就不同

### 视频必须有时间

```
【时间线】
【0—2秒】起手就给最强的视觉信息：<你的主体>。机位固定，第一帧就立住。
【2—5秒】<光与质感>；动作推进，镜头保持同一运动，不切。
【5—8秒】动作收束，画面停下来，最后一帧停在能当封面的构图上。
```

三段的分界按该实体的建议时长自动算（1/3、2/3 处）。

### 图像没有时间，但要有构图与画幅

```
Subject:      a knight in plate armour on a horse
Style:        Robert Eggers, candle-lit darkness, historical authenticity
Composition:  one-point perspective symmetry
Light:        one hard rim of light
Aspect:       2.35:1
Negative:     text, watermark, signature, deformed hands
```

---

## 三、中文格式的主体用**你的原话**

这是最容易做错的一点。中文平台的主体必须是你写的中文描述，
**不能**用检索到的英文风格样例——那是"某种风格长什么样"，不是"你要的画面"。

英文只出现在一处：`风格锚定：` 那一行。这是 Seedance 这类平台的通行做法
（中文说意图，英文钉住风格）。

正确：

```
【主体】一个男孩和一个鲸鱼女孩在卧室里相拥。<补一句：谁、在做什么、和什么互动>

【风格】8秒，21:9，高清。黑白特写、冷峻、静默。
风格锚定：Ingmar Bergman, high-contrast black and white, extreme close-ups of faces
```

错误（旧版，已修）：

```
【主体】a woman's face in extreme close-up in harsh light，出现在<场景>
```

---

## 四、平台格式的可信度

**我们只对自己核实过的格式负责：**

| 格式 | 依据 |
|---|---|
| Seedance 2.5 五段式 | [art-aesthetic-vault](https://github.com/YanKaFei/art-aesthetic-vault)（MIT）的卡片，该库作者实测过 |
| MiniMax H3 中文整段 | 同上 |
| SD 正负向 | 通用做法，长期稳定 |
| 其它平台 | **没有核实过，所以不提供** |

> 加新平台时：先自己实测一遍那个平台的输入框到底吃什么，
> 再往 `local_style_hint.py` 里加一个 `_fmt_xxx` 函数。
> **宁可不支持，也不要瞎猜一个格式。**

---

## 五、改哪里

`comfyui/local_style_hint.py`：

```
_MOVE_ZH          运镜的中文说法
_beats_zh()       时间轴三段
_core()           抽公共字段（主体为什么用 query、中文风格怎么拼）
_fmt_seedance()   Seedance 五段式
_fmt_minimax()    MiniMax 整段
_fmt_sd()         SD 正负向
```

`run()` 末尾按 `输出格式` 分发；域不匹配时回落。
