# 平台对照表

> **原则：只对自己核实过的格式负责。**
> 没核实的平台，矩阵里告诉你，但节点**不提供**那个格式——格式猜错比不支持更糟，
> 用户会以为是模型不行。

---

## 一、闭源平台

| 平台 | 形态 | 语言 | 词数甜点 | 独立负向 | 时间轴 | 节点支持 | 依据 |
|---|---|---|---|---|---|---|---|
| **Seedance 2.0 / 2.5** | 视频 | 中英 | **200–400**（hero）/ 80–150（插入）| 无 | 五段式含时间线 | ✅ Seedance 2.5 | [art-aesthetic-vault](https://github.com/YanKaFei/art-aesthetic-vault)（MIT）+ OpenMontage |
| **MiniMax / 海螺 H3** | 视频 | 中 | 段落 | 无 | 段内含 | ✅ MiniMax H3 | 同上 |
| **Runway Gen-4** | 视频 | 英 | **≤60** | 无 | 单镜 | ✅ Runway Gen-4 | [Runway 官方指南](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide) |
| Sora 2 / 2 Pro | 视频 | 英 | 100–250 | 无 | 结构化模板（镜头/滤镜/调色/同期声）| ❌ 未支持 | [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide) |
| Veo 3.1 / 3 | 视频 | 英 | 100–250 | 无 | 14 组件 | ❌ 未支持 | [Vertex AI 指南](https://cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide) |
| Kling 2.6 | 视频 | 中英 | — | 无 | 4 段 + `++强调++` | ❌ 未支持 | [fal.ai 指南](https://fal.ai/learn/devs/kling-2-6-pro-prompt-guide) |
| 可灵 / 即梦 / Vidu | 视频 | 中 | — | — | — | ❌ 未核实 | — |
| Pika / Luma Dream Machine | 视频 | 英 | — | 有（部分） | — | ❌ 未核实 | — |
| Grok Imagine Video | 视频 | 英 | — | — | 引用图占位 `<IMAGE_1>` | ❌ 未支持 | OpenMontage |
| Midjourney | 图像 | 英 | — | `--no` 参数 | 无 | ❌ 未支持 | 参数式，与文本模板不同 |
| **SD 1.5 / SDXL / Flux** | 图像 | 英 | — | **有，独立** | 无 | ✅ SD 正负向 | 通用做法 |

---

## 二、开源模型

| 模型 | 形态 | 语言 | 词数甜点 | 时间轴 | 节点支持 | 依据 |
|---|---|---|---|---|---|---|
| **HunyuanVideo 1.5** | 视频 | 中英 | — | 八段公式 | ✅ 混元八段 | [腾讯 Prompt Handbook](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md) |
| Wan 2.1 / 2.2 | 视频 | 英 | 200–400 | — | ⚠️ 用「通用五面」 | 无官方指南，长描述训练 |
| LTX-2 | 视频 | 英 | **≤80** | 6 元素 | ⚠️ 用「通用五面」 | [LTX 指南](https://docs.ltx.video/api-documentation/prompting-guide) |
| CogVideoX | 视频 | 英 | — | — | ⚠️ 用「通用五面」 | 无官方指南 |
| Open-Sora / Mochi | 视频 | 英 | — | — | ❌ 未核实 | — |
| SD / SDXL / Flux | 图像 | 英 | — | 无 | ✅ SD 正负向 | 通用做法 |

**⚠️ 标记的含义**：该模型没有专属格式，但用「通用五面」比什么都不给要好——
那是模型无关的骨架，实证有效。

---

## 三、通用五面为什么存在

出处：OpenMontage 的 [video-gen-prompting](https://github.com/calesthio/OpenMontage/blob/main/skills/creative/video-gen-prompting.md)，
其引用论文（CMU/Harvard *Building a Precise Video Language*）的结论是：

> VLM 能可靠描述主体与场景，但**系统性失败于运动、空间、运镜**。
> 强制填满以下五个槽是提升最大的一步。

```
Subject        主体 + 关键视觉属性 + 多主体时怎么区分
Motion         动作按时间顺序；主体与物件/主体的互动
Scene          叠加层（单独写！）+ 视角 + 环境 + 时间 + 场景动态
Spatial        景别 + 画面位置 + 深度（前/中/后景）+ 相对机位高度，以及它们在镜头里怎么变
Camera         播放速度 → 镜头畸变 → 高度 → 角度 → 对焦/景深 → 稳定度 → 运动
```

**没核实过格式的平台，一律用它。** 它是所有平台的下界，不是最优解。

---

## 四、三条容易踩的线（来自同一份指南）

1. **dolly ≠ zoom，pan ≠ truck**
   dolly 是机位平移，zoom 是焦距变化；pan 是旋转，truck 是横向平移。
   模型会跟着权重更高的那个词走，写混就出错误运动。

2. **"static" 是严格条件**
   零位移、零变焦、零焦点变化才算 static。只要有任意一项，就不要写 static。

3. **叠加层不属于景深**
   字幕、水印、HUD、画框图形要**单独写**内容和位置，绝不能说"overlay in the foreground"。

---

## 五、怎么加一个新平台

1. **先自己实测**那个平台的输入框到底吃什么（分段？长度？要不要负面？）
2. 在 `comfyui/local_style_hint.py` 加一个 `_fmt_xxx()`，并在 `输出格式` 选项里登记
3. 在本文件补一行，**把依据链接写上**
4. 没实测过就别加——写进"未核实"那几行

**判断标准很简单：如果我没法说出这个格式的出处，就不该写进代码。**
