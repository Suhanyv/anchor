# 格式对照表

> 同一个中文描述，14 种格式各跑一遍。**内容相同，形状不同。**
> 由 `src/gen_format_samples.py` 自动生成，模型 c27 / 语料 v21。

## 一、总览

| 格式 | 什么时候用 | 出处 |
|---|---|---|
| `自动（识别平台）` | — | — |
| `片段（英文）` | 任何平台都能吃的底料，接在主体后面 | 通用 |
| `结构化（英文）` | 人看的分栏文本，排查用 | 通用 |
| `通用五面（英文，模型无关）` | 不知道选哪个时的保底 | OpenMontage / CMU 论文 |
| `即梦 Seedance 2.5（中文）` | 四段式 + 连续整数秒时间轴 | 即梦官方指南 |
| `即梦 Seedance · 关键帧（中文）` | 第一句声明帧顺序 | 即梦官方指南 |
| `MiniMax H3（中文）` | 七行模板，素材用 @1 @2 | MiniMax 官方指南 |
| `混元 HunyuanVideo（中文八段）` | 主体/运动/场景/景别/运镜/光照/风格/氛围 | 腾讯 Prompt Handbook |
| `Runway Gen-4（英文，≤60 词）` | 只写运动，不写外观 | Runway 官方指南 |
| `可灵 4.0（中文，七要素）` | 一段散文，七要素按序 | 可灵官方指南 |
| `可灵·多镜头（中文）` | 先环境再分镜，每镜不同任务 | 可灵官方指南 |
| `可灵 4.0·关键帧（中文）` | 按时间段写关键帧之间发生了什么 | 可灵官方指南 |
| `Veo 3（英文，8 秒单镜）` | 五行短句，固定 8 秒，没有时间轴 | Veo 官方指南 |
| `Sora 2（已停服 · 仅存档）` | 八模块；平台已停止服务 | CSDN 社区总结（非官方） |
| `SD 正负向（英文）` | 图像专用，正向+负向两行 | 通用做法 |

## 二、样例：视频

**输入描述**：`一个男孩和一个鲸鱼女孩在卧室里相拥`

### 自动（识别平台）

> 【格式】通用五面（Subject/Motion/Scene/Spatial/Camera）

```text
Subject:  a whale's back breaking the surface, water sheeting off it
Motion:   the subject moves through the frame; nothing else moves
Scene:    a small bedroom, the bed unmade, one window with the curtain half drawn; light: stark coastal light
Spatial:  eye-level, mid shot, subject in the near plane, background readable
Camera:   camera completely static (no movement, no zoom, no focus change), 8s, 21:9, one continuous take, no cuts
Style:    Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness
```

### 片段（英文）

```text
a whale's back breaking the surface, water sheeting off it, in the style of Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness, locked-off camera, one unbroken take
```

### 结构化（英文）

```text
Shot:     locked-off, 8s, 21:9
Subject:  a whale's back breaking the surface, water sheeting off it
Action:   a woman's face in extreme close-up in harsh light, high-contrast black and white
Style:    Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness
Negative: scene change, camera shake, zoom pumping, flicker, frame stutter, morphing, fast cutting, whip pan, handheld shake, zooming
```

### 通用五面（英文，模型无关）

> 【格式】通用五面（Subject/Motion/Scene/Spatial/Camera）

```text
Subject:  a whale's back breaking the surface, water sheeting off it
Motion:   the subject moves through the frame; nothing else moves
Scene:    a small bedroom, the bed unmade, one window with the curtain half drawn; light: stark coastal light
Spatial:  eye-level, mid shot, subject in the near plane, background readable
Camera:   camera completely static (no movement, no zoom, no focus change), 8s, 21:9, one continuous take, no cuts
Style:    Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness
```

### 即梦 Seedance 2.5（中文）

> 【格式】即梦 Seedance 2.5 四段式（素材绑定/概述/时间轴/全局约束，依据：官方提示词指南）

```text
（素材绑定：图片 1 负责<人物/场景/风格>，视频 1 只参考<动作/运镜>，音频 1 负责<音色/节奏>；没有素材就删掉这一行）

自然光。一个男孩和一个鲸鱼女孩在卧室里相拥。a small bedroom, the bed unmade, one window with the curtain half drawn。

0–4 秒：<景别>。一个男孩和一个鲸鱼女孩在卧室里相拥，自然光，固定机位，不移动。
4–8 秒：<写：上一段的动作怎么继续或停下；要变形就写清从什么变成什么>。

全程保持主体清晰、背景自然虚化；21:9；机位完全固定；只使用<环境声>，不要配乐，不要字幕。
摄影层：浅景深（背景化开）；干净的数码质感；暖金；紧绷；85mm 中焦。
备选（换一个即可）：深景深（全部清晰） / 轻微颗粒 + 低对比 / 冷青灰 / 疲惫 / 35mm 广角。
不要出现：<写 2-4 个真正会让这条废掉的错误，例如手部畸形、兵器穿模、面部漂移、血迹>。
```

### 即梦 Seedance · 关键帧（中文）

> 【格式】即梦 Seedance 2.5 · 关键帧（依据：官方提示词指南）

```text
以图片 1 至图片 N 的顺序作为关键帧，制作 8 秒 21:9 的短片。

全片保持自然光；主体外观、服装与身份一致，不换人、不变形。

0–2 秒对应图片 1；2–5 秒对应图片 2；5–8 秒对应图片 3。
严格保持关键帧的画面顺序与构图，不新增镜头，角色外观随对应关键帧保持一致。

无文字、无字幕、无闪烁、无元素变形。
```

### MiniMax H3（中文）

> 【格式】MiniMax H3 中文整段（无编号）

```text
参考素材：@1 负责<人物/商品外观>；@2 负责<相机路径/节奏/声音>。（没有素材就删掉这一行）
场景顺序：一个男孩和一个鲸鱼女孩在卧室里相拥，a small bedroom, the bed unmade, one window with the curtain half drawn → 几乎不动，只有极细微的变化 → 停在原构图。
主体动作：一个男孩和一个鲸鱼女孩在卧室里相拥，动作速度与反应是几乎不动，只有极细微的变化。
相机：中景、平视机位开场，镜头不动，最后停在原构图。
声音：<对白>；<环境声>；<同步音效>；<背景音乐>。
保持不变：主体身份、服装、场景结构与「自然光」不变。
不要出现：错字、元素变形、重复主体、水印、字幕。
```

### 混元 HunyuanVideo（中文八段）

> 【格式】混元 1.5 八段公式（中文）

```text
主体：一个男孩和一个鲸鱼女孩在卧室里相拥
运动：主体在画面中自然地动作，全程一个镜头不切换
场景：a small bedroom, the bed unmade, one window with the curtain half drawn
景别：中景
运镜：固定机位，不移动，8 秒
光照：按参考描述
风格：<风格：库中没有可靠匹配，请自行指定>
氛围：安静、克制，情绪落在最后一帧
（英文锚定：Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness）
（画幅 21:9）
```

### Runway Gen-4（英文，≤60 词）

> 【格式】Runway Gen-4（只写运动，≤60 词）

```text
a whale's back breaking the surface, water sheeting off it. Static camera, no movement at all. One continuous scene, no cuts. Subject motion is the focus; keep the frame simple.
```

### 可灵 4.0（中文，七要素）

> 【格式】可灵 4.0（中文，七要素）（依据：可灵官方提示词指南）

```text
一个男孩和一个鲸鱼女孩在卧室里相拥，面部特征与服装保持不变。几乎不动，只有极细微的变化。a small bedroom, the bed unmade, one window with the curtain half drawn。镜头不动，自然光，节奏舒缓，单一连续镜头。环境音：<写环境音或留空>
```

### 可灵·多镜头（中文）

> 【格式】可灵·多镜头（中文）（依据：可灵官方提示词指南）

```text
一个男孩和一个鲸鱼女孩在卧室里相拥，<风格：库中没有可靠匹配，请自行指定>。
镜头 1：中景，一个男孩和一个鲸鱼女孩在卧室里相拥的动作与环境，镜头不动。
镜头 2：<换一种信息：给反应或给细节，不要重复镜头 1>
镜头 3：<收尾镜头，停在能当封面的构图上>
环境音：<写环境音或留空>
```

### 可灵 4.0·关键帧（中文）

> 【格式】可灵 4.0·关键帧（中文）（依据：可灵官方提示词指南）

```text
0–4 秒：一个男孩和一个鲸鱼女孩在卧室里相拥，按参考描述的光，镜头不动。
4–8 秒：几乎不动，只有极细微的变化；画面状态在这里发生一次变化，其余保持不变。
（总长 8 秒，画幅 21:9；每加一个关键帧只改一件事，不要同时改人物、环境、商品、镜头、光线和风格）
```

### Veo 3（英文，8 秒单镜）

> 【格式】Veo3 五行结构（英文，固定 8 秒单镜；依据：官方指南）

```text
8-second video.

a whale's back breaking the surface, water sheeting off it in a small bedroom, the bed unmade, one window with the curtain half drawn.

the subject stays almost still, only breathing and a slight shift.

stark coastal light. Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness.

Static camera, no movement.
```

### Sora 2（已停服 · 仅存档）

> 【格式】Sora 2 八模块 · 该平台已停止服务，本格式仅作存档。结构来自 CSDN 博客的社区总结（CC BY-SA 4.0），非官方；官方 cookbook 亦不可达（403）。

```text
[主体] 一个男孩和一个鲸鱼女孩在卧室里相拥。<补：年龄段、外观、服装、道具，具体到可识别>

[场景] a small bedroom, the bed unmade, one window with the curtain half drawn

[动作] 几乎不动，只有极细微的变化。8 秒内只做 1~2 个主动作，动作链清晰，不要瞬移。

[镜头] 中景、平视机位开场，固定机位，不移动，镜头运动平滑，不做突兀跳切；只写一种运动。

[光线] 自然光，色温与方向写清。写清冷暖、强弱、方向。

[风格] <风格：库中没有可靠匹配，请自行指定>。风格词控制在 3~5 个，不要堆冲突风格。

[技术参数] 时长 8 秒，24fps，21:9，4K，画面稳定。

[限制项] 避免手部畸形、面部扭曲、物体穿模、文字乱码、画面闪烁与跳帧；禁止字幕、水印、logo。
```

### SD 正负向（英文）

> 【格式】SD 正向/负向逗号串（无时间轴）

```text
Positive: a whale's back breaking the surface, water sheeting off it, a woman's face in extreme close-up in harsh light, Ingmar Bergman, high-contrast black and white, extreme close-ups of faces, stark coastal light, intimate stillness, extreme close-ups of faces, 21:9
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

## 三、样例：图片

**输入描述**：`雨夜的街道，霓虹倒映在积水里，一个人走过`

### 自动（识别平台）

> 【格式】SD 正向/负向逗号串（无时间轴）

```text
Positive: a wet street at night, signs reflecting in puddles, a holographic advertisement flickering over a wet crowd, Cyberpunk, neon signage, wet street, dense cabling, holographic ad, 2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 片段（英文）

```text
a wet street at night, signs reflecting in puddles, in the style of Cyberpunk, neon signage, wet street, dense cabling, holographic ad, still frame, sharp focus, fine detail
```

### 结构化（英文）

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 通用五面（英文，模型无关）

> 【格式】通用五面（Subject/Motion/Scene/Spatial/Camera）

```text
Subject:  a wet street at night, signs reflecting in puddles
Motion:   the subject moves through the frame; nothing else moves
Scene:    a tiled bathroom, water still running, the mirror fogged; light: neon signage
Spatial:  eye-level, mid shot, subject in the near plane, background readable
Camera:   slow dolly forward, 6s, 2.35:1, one continuous take, no cuts
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
```

### 即梦 Seedance 2.5（中文）

> 【格式】即梦 Seedance 是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 即梦 Seedance · 关键帧（中文）

> 【格式】即梦 Seedance 是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### MiniMax H3（中文）

> 【格式】MiniMax H3 是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 混元 HunyuanVideo（中文八段）

> 【格式】混元 1.5 八段公式（中文）

```text
主体：雨夜的街道，霓虹倒映在积水里，一个人走过
运动：主体在画面中自然地动作，全程一个镜头不切换
场景：a tiled bathroom, water still running, the mirror fogged
景别：中景
运镜：缓慢推近，6 秒
光照：全息广告、人群、湿地
风格：赛博朋克：全息广告、人群、湿地
氛围：安静、克制，情绪落在最后一帧
（英文锚定：Cyberpunk, neon signage, wet street, dense cabling, holographic ad）
（画幅 2.35:1）
```

### Runway Gen-4（英文，≤60 词）

> 【格式】Runway Gen-4（只写运动，≤60 词）

```text
a wet street at night, signs reflecting in puddles. Camera dollies in slowly. One continuous scene, no cuts. Subject motion is the focus; keep the frame simple.
```

### 可灵 4.0（中文，七要素）

> 【格式】可灵是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 可灵·多镜头（中文）

> 【格式】可灵是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### 可灵 4.0·关键帧（中文）

> 【格式】可灵是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### Veo 3（英文，8 秒单镜）

> 【格式】Veo 是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### Sora 2（已停服 · 仅存档）

> 【格式】Sora 是视频格式，当前是图片域 -> 回落到结构化

```text
Subject:  a wet street at night, signs reflecting in puddles
Style:    Cyberpunk, neon signage, wet street, dense cabling, holographic ad
Aspect:   2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

### SD 正负向（英文）

> 【格式】SD 正向/负向逗号串（无时间轴）

```text
Positive: a wet street at night, signs reflecting in puddles, a holographic advertisement flickering over a wet crowd, Cyberpunk, neon signage, wet street, dense cabling, holographic ad, 2.35:1
Negative: text, watermark, signature, deformed hands, extra fingers, oversharpened, hdr halo
```

## 四、怎么选

```
要时间轴、要分段变化      -> 即梦 Seedance / 可灵 4.0 / MiniMax H3
只要一个 8 秒的瞬间       -> Veo 3（五行，没有分段）
要最短、只写运动          -> Runway Gen-4（≤60 词）
出图像而不是视频          -> SD 正负向
平台没在列表里            -> 通用五面（保底，任何模型都能吃）

中文平台优先用中文格式；英文模型（Veo/Runway/SD）用英文格式。
混用会让模型解析变差，这不是风格问题，是语言问题。
```

---

## 五、三条通用于所有平台的规律

今天读的六份材料（含四份官方指南）里，三家独立提到了同一件事：

1. **一个镜头只写一种运动** —— 不要「推进+旋转+拉远」同时出现
   （可灵：运镜太多画面乱；OpenMontage：dolly ≠ zoom，pan ≠ truck）
2. **必须写清「镜头最后停在哪」** —— 可灵、即梦、MiniMax 都单列了这条
3. **必须写清「哪些东西不变」** —— 人物身份、服装、Logo、场景结构

**这不是某个平台的偏好，是这几个模型的共同失败模式。**
