# 交接单（HANDOFF）

**这份文件是为了"换一个新会话也能接着干"而写的。**
如果你是我，正在读这份文件：先照「怎么验一遍」跑三条命令，再看「下一步」。

最后更新：2026-10-31 · 提交 182 · 全部已推到 GitHub

---

## 一、现在部署的是什么

```
模型    models/e5-director-c27
语料    data/raw/corpus_v26.jsonl        （1049 条 / 176 实体）
题材    data/raw/subjects_v20.jsonl      （329 条 / 约 150 实体）
工艺    data/raw/crafts_v9.jsonl         （132 条 / 约 53 实体）
材质    data/raw/materials_v12.jsonl     （309 条 / 约 93 实体）
节点    comfyui/local_style_hint.py      （16 个参数 / 16 种输出格式）
```

**部署位置**：15 个 ComfyUI 安装的 `custom_nodes/prompt_style_local/` + `E:\comfyui`。

---

## 二、怎么验一遍（三条命令）

```powershell
cd F:\llm
$env:HF_HOME='F:\llm\cache\hf'; $env:HF_HUB_OFFLINE='1'; $env:PYTHONIOENCODING='utf-8'

# ① 冒烟：数据一致性 + 三条基本检索
& .venv\Scripts\python.exe src\smoke_test.py
#    期望：一致 ['corpus_v26.jsonl','crafts_v9.jsonl','materials_v12.jsonl','subjects_v20.jsonl']
#    期望：=== 3/3 通过 ===

# ② 端到端一句（应当一个占位符都没有，除了 negative 那种极端情况）
& .venv\Scripts\python.exe -c "import sys;sys.path.insert(0,r'F:\llm\comfyui');import local_style_hint as N;d=N.LocalStyleHint.INPUT_TYPES()['required'];o,_=N.LocalStyleHint().run('雨里，一个女孩抱着纸箱跑',d['模型目录'][1]['default'],d['语料文件'][1]['default'],d['题材文件'][1]['default'],d['工艺文件'][1]['default'],d['材质文件'][1]['default'],True,'文生视频',False,'即梦 Seedance 2.5 · 整段（中文）','cpu','视频','导演/风格聚合',1,'',False);print(o)"

# ③ 门槛 A/B（应当 20/20，且结论是"不改"）
& .venv\Scripts\python.exe src\_ab_floors.py
```

**三条都过，说明环境和数据都是好的。**

---

## 三、这个系统的形状（读代码前先读这个）

**一次调用 = 十维查表 + 模板拼装。它不写内容。**

| 维 | 来源表 | 条数 |
|---|---|---|
| 风格 | corpus（向量检索）| 176 实体 |
| 主体 ×2 | subjects | 约 150 |
| 场景 ×2 | subjects（type=scene）| 44 |
| 工艺 | crafts | 53 |
| 材质 | materials | 93 |
| 光 | `light_ref.json` + `scene_light.json` | 32 + 18 类规则 |
| 运镜 | `motion_ref.json` | 21 |
| 声音 | `sound_ref.json` | 17 |
| 数量 | `quantity_ref.json` | 20 |
| 时长 | `duration_ref.json` + 查询里的"N 秒" | — |
| 动作节拍 | `beat_ref.json` | 13 |
| 风险 | `risk_ref.json` | 14 |
| 镜头类型 | `shot_ref.json` | 5 |
| 画面材质 | `medium_ref.json` | 10 |
| **构图** | `composition_ref.json` | **24** |
| **脸部光型** | `face_light_ref.json` | **14** |
| **类型片视觉** | `genre_look_ref.json` | **20** |
| **景别** | `shot_size_ref.json` | **20** |
| **机位角度** | `camera_angle_ref.json` | **17** |
| **调色** | `color_ref.json` | **15** |
| **剪辑转场** | `edit_ref.json` | **16**（仅多镜）|
| **光学效果** | `optical_ref.json` | **16** |

**每张表里都有 `_about` / `_why`，用来说明"为什么要这张表"。改数据前先读它。**

### 层与层的关系（2026-10-31 补的三层）

联网从一个公开影视技法库里补了三层**语法**——以前只有"词汇"（雨天光、荧光灯），
没有"怎么摆、怎么打、整包长什么样"：

```
类型片（整包，最高）     一遍给出光+镜头+色彩+布景
  构图 / 脸部光型 / 镜头类型
    光 / 声音 / 动作节拍 / 风险
      风格 / 主体 / 场景
```

**规则：整包压过零件。** 实测「黑色电影 + 办公室」同时输出
"荧光灯，偏绿的冷白"和"黑白，硬光低调"——两种光互相拆台。
现在只要类型片命中，场景光整条不输出，调色也交给类型片定（黑白的就得是黑白）。

**这三张表的 `_source` 指向同一个站**：`screenweaver.ai/zh/film-techniques`
（授权未核实，**只取结构、用我们自己的话写**，源地址记在文件里）。
那个站还有这些页没捞：景别 / 机位角度 / 色彩 / 光学效果 / 剪辑转场 / 氛围天气 / 镜头与光学。

**2026-10-31 续：上面七页已经捞完六页**，共新增 **142 条**：
构图 24 · 光型 14 · 类型片 20 · 景别 20 · 角度 17 · 调色 15 · 剪辑 16 · 光学 16。
**只剩「氛围与天气」和「镜头与光学」两页没捞。**

捞的过程中撞到三个真 bug，都值得记住：

1. **调色从三档写死变 15 档**：以前 `_cine_line` 只有暖金/青橙/自然色三个候选。
2. **`_match_ref` 会拿风格标签去匹配表**：黑泽明的关键词里有「群像」，
   于是「一个女孩在雨里跑」被判成群像镜头。**导演的标签能拽进一整个景别。**
   新四张表改成只认查询原话。
3. **一张有语法错的表会静静失败**：`color_ref.json` 少了个逗号，
   `_load_ref` 捕获异常返回空表，界面上什么都没发生。**表坏了不会报错，只会没效果。**
   改表后必须跑 `python -c "import json;json.load(open(...))"`。



---

## 四、几条必须守的规矩

1. **不许替工具美化输出**（`CORRECTIONS.md` 长期规矩）。
   我只贴它吐出来的原文，不补时间轴、不改措辞、不手改秒数。
   发现问题**改代码**，改完重跑，让人看到新版本的原样输出。

2. **任何"某某做不到 / 某某不允许"，必须写清依据和日期**（C6）。
   写不出依据的进"待验证"，不进规则。

3. **验收要两组数**：新条目命中 + 老条目不变。改动前后都跑。

4. **不许拿训练样本当测试**（`docs/CORRECTION_QUERY_AUG.md`）。
   用写进库的句子去测命中率，那是背诵。

5. **中文代码一律写成 .py 文件再跑**，不要用 shell 内联——引号会被吃，至少踩过十次。

---

## 五、下一步（按优先级）

### ① 那部片子还没拍完

四镜（雨天女孩水墨风）已经出全，**镜1 还差半段**：

```
镜1 正面推进 12s   6–12 秒 仍是 <写…> 占位符（"正面推进"这条节拍只给了一段）
镜2 背面跟拍 15s   已填满
镜3 脚下特写 8s    已填满
镜4 空镜收尾 12s   已填满
```

**要么把镜1 压到 8 秒（一段就够），要么人工填那半段。**
四镜合计 47 秒，即梦一次只能出 30 秒以内，**必须分开生成再剪**。

### ② 品味数据 11/20

```powershell
python src\taste.py batch "请求A" "请求B"      # 一次问多条，每条三版
python src\taste.py pick 1C --also 1A --note "为什么"
python src\taste.py report
```

**目标 20 条。** 已有的结论：光要跟场景走（深夜便利店→荧光灯，雨→柔散光），
维度分不等于好（用户挑过维 3 的、弃过维 4 的）。

### ③ 声音表还能扩

现在 17 类，按"白天/夜里、室内/室外"还能再分一层。

### ④ 用户的插件 `@local/model-craft`

`dev` 里的 `llm-craft` 技能。可以把它 §9「血泪坑」转成库里的 `risk_ref` 条目，
让"踩过的坑"变成可查的表，而不是一份要人读的清单。

### ⑤ 缺口记录 18 条还躺在 gaps.jsonl

里面有"我不会"的查询。**没有"把 gaps 变成学习清单"的流程**——这是个断点。

---

## 六、最近这段的关键教训

```
① 一条真实视频，比我写过的所有单元测试都有效
   它抓出三个缺陷：风格名对视频模型无效 / 机位没锁住 / 节拍表有歧义

② 风格名 → 画面材质
   「文人水墨」写进去出的是写实电影感；
   改成「画面：整幅是水墨，宣纸纤维可见…」才真的出水墨。

③ 锁定要跟镜头类型走
   「一镜到底，机位不换位置」把跟拍也禁了，模型只好自己切镜。

④ 库里有 ≠ 用得上
   雕漆/蜡染在 crafts_v9，节点却指着 v8；门槛标定脚本的常数早改名。
   这一类"东西在但没接上"出现了至少五次。
```

---

## 七、环境

```
Python   F:\llm\.venv\Scripts\python.exe  (3.12.10, torch cpu)
模型     39 个 e5-* 版本；权重↔语料对应见 data/raw/model_manifest.json（推断，24 个 low）
盘       F: 是移动硬盘，掉过一次；仓库也可从 GitHub 重克隆
远端     git@github.com:Suhanyv/anchor.git（SSH 走 443，见 PUBLISH.zh-CN.md）
```
