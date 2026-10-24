"""
ComfyUI 自定义节点（本地版）—— 不依赖任何外部服务

与 comfyui_style_hint.py 的区别：
    那个走 HTTP，需要单独起 serve_style.py。
    这个直接在 ComfyUI 进程里加载模型，装完就能用。

装法见文件末尾的「安装步骤」。

显存注意
--------
设备选 "cpu" 时占用 0 显存（模型约 500MB 内存），单次查询 50-150ms。
设备选 "cuda" 时占 0.6-1GB 显存 —— 8GB 卡上跑 SDXL 时会紧张，默认用 cpu。
"""

import json
import os

# ------------------------------------------------------------------ 全局缓存
_CACHE = {}

# ------------------------------------------------------------------ 域路由
# 内联在这里，保证节点自包含（不依赖 F:\llm\src\domain_router.py）
# 原则：宁可判成 any（不过滤），也不要判错（会误杀正确答案）
_VIDEO_HINTS = [
    "视频", "运镜", "镜头运动", "动起来", "时长", "几秒", "秒钟", "秒的",
    "推镜", "拉镜", "摇镜", "移镜", "跟拍", "环绕", "升镜", "降镜", "甩镜",
    "sora", "可灵", "即梦", "runway", "veo", "kling", "pika", "海螺", "hailuo",
    "一镜到底", "转场", "慢动作", "升格", "逐帧", "镜头缓缓", "镜头推",
]
_IMAGE_HINTS = [
    "图片", "照片", "静帧", "静态", "海报", "壁纸", "插画", "原画", "立绘",
    "出图", "一张图", "一张", "封面", "截图", "构图", "分辨率",
    "4k", "8k画质", "竖版图", "横版图", "画一张", "渲染图", "图生图", "动漫",
    "midjourney", "mj", "stable diffusion", "flux", "即梦图片", "niji",
]
# 「画面」有歧义：单独出现偏静态，和运动词一起就是视频语境
_AMBIG_STILL = ["画面", "镜头", "构图感"]
# 注意：不能用单字「骑」——它会匹配到「骑士」这个名词。
_MOTION_WORDS = ["慢", "动", "推", "摇", "移", "跟", "环绕", "升", "降", "甩",
                 "转", "秒", "帧", "切", "长镜", "手持", "漂", "运镜",
                 "狂奔", "奔跑", "奔驰", "疾驰", "冲", "骑马", "飞", "追",
                 "打斗", "挥", "落", "坠", "翻滚", "穿过", "掠过", "走来", "走去"]
# 强运动词 + 「镜头/画面」= 明确是视频（真实的「骑马在麦田狂奔的镜头」就是这种）
_STRONG_MOTION = ["狂奔", "奔跑", "奔驰", "疾驰", "骑马", "跟拍", "推近", "摇镜",
                  "环绕", "翻滚", "穿过", "掠过", "打斗", "追", "冲", "飞"]


def _detect_domain(text):
    t = (text or "").lower()
    v = sum(1 for w in _VIDEO_HINTS if w.lower() in t)
    i = sum(1 for w in _IMAGE_HINTS if w.lower() in t)
    # 「镜头/画面」+ 强运动词 -> 是在说一个**运动的镜头**，判视频
    if any(w in t for w in _STRONG_MOTION) and any(w in t for w in _AMBIG_STILL):
        v += 1
    if i == 0:
        still = sum(1 for w in _AMBIG_STILL if w in t)
        motion = sum(1 for w in _MOTION_WORDS if w in t)
        if still and motion == 0:
            i = 1
    if v and not i:
        return "prompt_video"
    if i and not v:
        return "prompt_image"
    return "any"


def _allowed_idx(corpus, domain):
    if domain not in ("prompt_image", "prompt_video"):
        return list(range(len(corpus)))
    idx = [i for i, d in enumerate(corpus) if d.get("domain") == domain]
    return idx or list(range(len(corpus)))


def _encode_texts(tok, enc, device, texts, prefix):
    """把一批文本编码成归一化向量（内部工具）"""
    import torch
    import torch.nn.functional as F
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok([prefix + t for t in texts[i:i + 32]], padding=True,
                    truncation=True, max_length=128, return_tensors="pt")
            b = {k: v.to(device) for k, v in b.items()}
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
    return torch.cat(out).cpu()


def _load(model_dir, corpus_path, device, subject_path=None, craft_path=None, material_path=None):
    key = (model_dir, corpus_path, device, subject_path, craft_path, material_path)
    if key in _CACHE:
        return _CACHE[key]

    import torch
    from transformers import AutoModel, AutoTokenizer

    if not os.path.isdir(model_dir):
        raise RuntimeError(
            f"模型目录不存在：{model_dir}\n"
            f"请把 F:\\llm\\models\\e5-director-c9 整个文件夹复制到这个路径，"
            f"或把本节点的「模型目录」改成实际位置。"
        )
    if not os.path.isfile(corpus_path):
        raise RuntimeError(f"语料文件不存在：{corpus_path}")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]

    # 题材库：独立通道，不混进风格索引（混在一起会互相抢）
    subjects = []
    if subject_path and os.path.isfile(subject_path):
        with open(subject_path, encoding="utf-8") as f:
            subjects = [json.loads(l) for l in f if l.strip()]

    # 工艺/媒介库：第三条通道。实测把它混进风格索引会让场景 -5pp、材质 -7pp，
    # 所以必须独立（见 STATUS 第五十节）。
    crafts = []
    if craft_path and os.path.isfile(craft_path):
        with open(craft_path, encoding="utf-8") as f:
            crafts = [json.loads(l) for l in f if l.strip()]

    materials = []
    if material_path and os.path.isfile(material_path):
        with open(material_path, encoding="utf-8") as f:
            materials = [json.loads(l) for l in f if l.strip()]

    tok = AutoTokenizer.from_pretrained(model_dir)
    enc = AutoModel.from_pretrained(model_dir).to(device).eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    doc_emb = _encode_texts(tok, enc, device, [d["text_semantic"] for d in corpus], "passage: ")
    subj_emb = (_encode_texts(tok, enc, device, [s["text_semantic"] for s in subjects], "passage: ")
                if subjects else None)
    craft_emb = (_encode_texts(tok, enc, device, [c["text_semantic"] for c in crafts], "passage: ")
                 if crafts else None)
    mat_emb = (_encode_texts(tok, enc, device, [m["text_semantic"] for m in materials], "passage: ")
               if materials else None)

    _CACHE[key] = {"corpus": corpus, "doc_emb": doc_emb,
                   "subjects": subjects, "subj_emb": subj_emb,
                   "crafts": crafts, "craft_emb": craft_emb,
                   "materials": materials, "mat_emb": mat_emb,
                   "tok": tok, "enc": enc, "device": device}
    return _CACHE[key]


def _encode_query(st, q):
    import torch
    import torch.nn.functional as F
    tok, enc, device = st["tok"], st["enc"], st["device"]
    with torch.no_grad():
        b = tok(["query: " + q], padding=True, truncation=True,
                max_length=128, return_tensors="pt")
        b = {k: v.to(device) for k, v in b.items()}
        h = enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        v = ((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float()
        return F.normalize(v, dim=-1).cpu()[0]


# 题材是否拼入输出：用**相对判据**而不是绝对阈值。
# 绝对阈值试过 0.42，会把正确答案（中世纪骑士 0.3620）挡掉——
# 题材文档是短句，与 e5 的相似度天然低于长描述的风格文档。
# 实测四条 query 证明：比"题材分 vs 风格分"能全对：
#     中世纪骑士  0.3620 > 0.3238  拼
#     老人客厅    0.4168 > 0.3615  拼
#     无明确题材  0.3172 < 0.5057  不拼
#     跑偏那条    0.2042 < 0.3077  不拼
SUBJECT_RATIO = 0.95
# 相对比值会误报：实测「从树枝后面看过去，前景有草叶遮挡」拼进了「沙漠商队」（比值 0.99）。
# 所以再加一道**绝对下限**。0.36 是实测校准值（样本少，标注为经验值）：
#   中世纪骑士 0.4945 ✓ / 唐代宫廷 0.5070 ✓ / 武侠竹林 0.4813 ✓ / 老人 0.4168 ✓
#   沙漠商队误报 0.3378 ✗ / 跑偏那条 0.2042 ✗
SUBJECT_FLOOR = 0.36

# ---- 赢家通吃：风格 / 主体 / 工艺 / 材质 四个渠道比大小 ----
# 实测（6 条 query 全渠道打分）：6 条里 5 条正确答案就是分最高的那个渠道。
# 相对比值（渠道分 >= 风格分 x 0.95）在风格分低时会误开，已被推翻。
# 现在只用「每渠道绝对下限 + 高于风格分」。
MAT_FLOOR = 0.40

# ---- 工艺/媒介通道的门槛（同一套相对判据）----
# 实测：蓝晒 1.27 / 金缮 1.31 / 刺绣 1.05 命中；铜版画 0.92、无工艺 0.50~0.91 正确排除
CRAFT_RATIO = 0.95
# 绝对下限比题材高（0.44 而非 0.36）：工艺的假阳性更凶。
# 实测分界：
#   真阳性 蓝晒 0.4827 / 金缮 0.4750 / 刺绣 0.5032
#   假阳性 拉弓->刺绣 0.4070 / 铜版->火柴盒 0.4215 / 骑士->糖画 0.2252
# 假阳性来自"风格分很低时任何工艺都显得相对更强"，所以必须靠绝对下限挡。
# 0.44 是 6 个样本上校准的，样本少，标注为经验值。
CRAFT_FLOOR = 0.44

# ---- 分级去偏：把「画什么」从 query 向量里减掉，只留「怎么拍」----
# 实测（场景基准 20 题）：全局去偏净亏 10pp，因为它把地貌类的风格信号也减掉了。
# 只对 character_object（人物/物件）去偏后：
#   top1 55%->60%  top3 70%->75%  top5 70%->85%
# 判据：地貌/街道与"辽阔/空旷/自然光"共享语义，物件的语义与风格分离。
DEBIAS_ALPHA = 1.0
DEBIAS_TYPES = {"character_object"}

# ---- 输出形态：图像和视频要用不同的收尾语言 ----
# 图像要"停在那一格"，视频要"怎么动、动多久"
MOTION_EN = {
    "STATIC": "locked-off camera, one unbroken take",
    "KINETIC": "fast handheld tracking, quick cuts",
    "SLOW": "slow push-in, steady drift",
}
IMG_TAIL = "still frame, sharp focus, fine detail"


def _rank(q, model_dir, corpus_path, device, topk, by, domain="auto",
          subject_path=None, craft_path=None, material_path=None, use_material=False):
    st = _load(model_dir, corpus_path, device, subject_path, craft_path, material_path)
    qe = _encode_query(st, q)
    sims = (st["doc_emb"] @ qe).numpy()
    corpus = st["corpus"]

    # ---- 工艺/媒介通道（第三条，独立索引）----
    craft = None
    if st.get("craft_emb") is not None and len(st["crafts"]):
        csims = (st["craft_emb"] @ qe).numpy()
        k = int(csims.argmax())
        c = st["crafts"][k]
        craft = {"score": float(csims[k]), "en": c["craft_en"],
                 "zh": c["craft_zh"], "phrase": c["phrase"], "hit": False}

    # ---- 材质/光通道（第四条，仅在「启用材质」打开时计算）----
    mat = None
    if use_material and st.get("mat_emb") is not None and len(st["materials"]):
        msims = (st["mat_emb"] @ qe).numpy()
        k = int(msims.argmax())
        m = st["materials"][k]
        mat = {"score": float(msims[k]), "en": m["mat_en"],
               "zh": m["mat_zh"], "phrase": m["phrase"], "hit": False}

    # ---- 题材通道（独立索引，与风格并行）----
    subj = None
    subj_idx = None
    if st.get("subj_emb") is not None and len(st["subjects"]):
        ssims = (st["subj_emb"] @ qe).numpy()
        k = int(ssims.argmax())
        s = st["subjects"][k]
        subj_idx = k
        subj = {"score": float(ssims[k]), "en": s["subject_en"],
                "zh": s["subject_zh"], "phrase": s["phrase"],
                "type": s.get("type", ""), "hit": False}

    # ---- 分级去偏（必须在算风格分之前：需要先知道风格 top1 才能判题材是否命中）----
    # 先用原向量算一遍拿到 style_top，再决定减不减，最后重算风格分。
    _sims_raw = sims
    _top_style_raw = float(sims[:].max()) if len(sims) else 0.0
    if (subj is not None and DEBIAS_ALPHA > 0
            and subj["type"] in DEBIAS_TYPES
            and subj["score"] >= _top_style_raw * SUBJECT_RATIO
            and subj["score"] >= SUBJECT_FLOOR):
        import numpy as _np
        sv = st["subj_emb"][subj_idx].numpy()
        v = qe.numpy() - DEBIAS_ALPHA * sv
        n = float(_np.linalg.norm(v))
        if n > 1e-9:
            import torch as _torch
            sims = (st["doc_emb"] @ _torch.from_numpy(v / n)).numpy()
            subj["debiased"] = True
    if subj is not None and "debiased" not in subj:
        subj["debiased"] = False

    # 域解析：auto/自动 都按 query 自动判断；判不准就 any（不过滤）
    if domain in ("auto", "自动", "", None):
        domain = _detect_domain(q)
    # 统一成 corpus 里的 domain 值（image/video/图片/视频 都映射过来）
    domain = {
        "image": "prompt_image", "video": "prompt_video",
        "图片": "prompt_image", "视频": "prompt_video",
        "prompt_image": "prompt_image", "prompt_video": "prompt_video",
    }.get(domain, "any")
    allowed = _allowed_idx(corpus, domain)

    if by == "导演/风格聚合":
        best = {}
        for i in allowed:
            d = corpus[i]
            s = float(sims[i])
            cur = best.get(d["director"])
            if cur is None or s > cur["score"]:
                tags = ", ".join(d.get("style_tags", [])[:4])
                best[d["director"]] = {
                    "score": s, "director": d["director"],
                    "director_zh": d.get("director_zh", ""),
                    "facet": d.get("facet", "base"),
                    "doc_id": d.get("doc_id", ""),
                    "domain": d.get("domain", ""),
                    "motion": d.get("motion", ""),
                    "style_string": f"in the style of {d['director']}" + (f", {tags}" if tags else ""),
                    "prompt": d.get("prompt", ""),
                }
        return sorted(best.values(), key=lambda x: -x["score"])[:topk], "director", subj, domain, craft, mat

    out = []
    for i in sorted(allowed, key=lambda j: -sims[j])[:topk]:
        d = corpus[int(i)]
        out.append({"score": float(sims[int(i)]), "director": d["director"],
                    "director_zh": d.get("director_zh", ""),
                    "facet": d.get("facet", "base"),
                    "style_string": d.get("prompt", ""),
                    "prompt": d.get("prompt", "")})
    return out, "prompt", subj, domain, craft, mat


# ------------------------------------------------------------------ 节点
class LocalStyleHint:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "中文描述": ("STRING", {"multiline": True,
                                       "default": "远远的镜头，一条草船在江上，有个老渔夫在划"}),
                "模型目录": ("STRING", {"default": r"F:\llm\models\e5-director-c18"}),
                "语料文件": ("STRING", {"default": r"F:\llm\data\raw\corpus_v16.jsonl"}),
                "题材文件": ("STRING", {"default": r"F:\llm\data\raw\subjects_v4.jsonl"}),
                "工艺文件": ("STRING", {"default": r"F:\llm\data\raw\crafts_v3.jsonl"}),
                "材质文件": ("STRING", {"default": r"F:\llm\data\raw\materials_v4.jsonl"}),
                # 改为默认开启：赢家通吃规则上线后，材质通道不再污染其它渠道
                # （钢甲问出太空船内、丝绸问出湿壁画两个案例已修好）。
                # 仍存在的已知错误是「材质通道内部认错材质名」（暗角/混凝土），
                # 那是材质库内容不足（方案 A），不是通道机制问题。
                "启用材质": ("BOOLEAN", {"default": True}),
                "设备": (["cpu", "cuda"], {"default": "cpu"}),
                "域": (["自动", "图片", "视频", "不限"], {"default": "自动"}),
                "匹配方式": (["导演/风格聚合", "逐条提示词"], {"default": "导演/风格聚合"}),
                "候选数": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "追加到": ("STRING", {"multiline": True, "default": ""}),
                # 默认「否」：题材通道已经给出英文主体，不必再塞中文原文。
                # 想保留你自己的原话（中文）时再打开。
                "包含原文": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("风格串", "调试信息")
    FUNCTION = "run"
    CATEGORY = "中文 风格"

    @classmethod
    def IS_CHANGED(cls, **kw):
        return float("NaN")   # 每次都重算，避免缓存旧的 query 结果

    def run(self, 中文描述, 模型目录, 语料文件, 题材文件, 工艺文件, 材质文件, 启用材质,
            设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):
        items, mode, subj, domain_used, craft, mat = _rank(
            中文描述, 模型目录, 语料文件, 设备, 候选数, 匹配方式,
            {"自动": "auto", "图片": "image", "视频": "video",
             "不限": "any"}.get(域, "auto"), 题材文件, 工艺文件, 材质文件, 启用材质)
        if not items:
            return ("", "无结果")

        if mode == "director":
            text = ", ".join(it["style_string"] for it in items) if 候选数 > 1 else items[0]["style_string"]
            dbg = "\n".join(f"{i+1}. {it['director']} / {it['director_zh']} "
                            f"[{it['facet']}] {it.get('domain','')} "
                            f"{it.get('motion','')} {it['score']:.4f}"
                            for i, it in enumerate(items))
        else:
            text = items[0]["prompt"] if 候选数 == 1 else \
                "\n\n".join(f"[{i+1}] {it['prompt']}" for i, it in enumerate(items))
            dbg = "\n".join(f"{i+1}. {it['director']} [{it['facet']}] {it['score']:.4f}"
                            for i, it in enumerate(items))

        if 追加到 and 追加到.strip():
            text = text + ", " + 追加到.strip()

        # ================= 赢家通吃：四渠道比大小 =================
        # 实测（6 条 query 全渠道打分）：6 条里 5 条正确答案就是分最高的那个渠道。
        # 相对比值（渠道分 >= 风格分 x 0.95）在风格分低时会误开，已被推翻。
        # 现在只用「每渠道绝对下限 + 必须高于风格分」。
        top_style = items[0]["score"]
        floors = {"主体": SUBJECT_FLOOR, "工艺": CRAFT_FLOOR, "材质": MAT_FLOOR}

        if subj:
            dbg = (f"主体: {subj['zh']} {subj['score']:.4f} (下限{SUBJECT_FLOOR}) "
                   f"{'过' if subj['score'] >= SUBJECT_FLOOR else '未过'}\n" + dbg)
        if craft:
            dbg = (f"工艺: {craft['zh']} {craft['score']:.4f} (下限{CRAFT_FLOOR}) "
                   f"{'过' if craft['score'] >= CRAFT_FLOOR else '未过'}\n" + dbg)
        if mat:
            dbg = (f"材质: {mat['zh']} {mat['score']:.4f} (下限{MAT_FLOOR}) "
                   f"{'过' if mat['score'] >= MAT_FLOOR else '未过'}\n" + dbg)

        eligible = []
        for name, obj in (("主体", subj), ("工艺", craft), ("材质", mat)):
            if obj and obj["score"] > top_style and obj["score"] >= floors[name]:
                eligible.append((name, obj["score"], obj))

        winner = max(eligible, key=lambda x: x[1]) if eligible else None
        if winner is None:
            dbg = (f"最终: 风格最高或无人过门槛 -> 不拼内容 (风格 {top_style:.4f})\n" + dbg)
        else:
            name, sc, obj = winner
            dbg = (f"最终: {name}分最高且过门槛 -> 只拼{name} "
                   f"({sc:.4f} > 风格 {top_style:.4f})\n" + dbg)
            if name == "主体":
                text = obj["phrase"] + ", " + text
            elif name == "工艺":
                text = text + ", rendered as " + obj["phrase"]
            else:
                text = text + ", " + obj["phrase"]

        # 保留用户原话（中文）
        if 包含原文 and 中文描述 and 中文描述.strip():
            text = 中文描述.strip() + ", " + text

        # ---- 输出形态：图像 / 视频 收尾语言不同 ----
        params = items[0].get("params") or {}
        if domain_used == "prompt_video":
            mo = items[0].get("motion") or "SLOW"
            arr = params.get("ar") or "21:9"
            dur = params.get("duration") or "5s"
            text = text + ", " + MOTION_EN.get(mo, MOTION_EN["SLOW"])
            fmt = (f"【视频形态】运镜={mo}  建议时长={dur}  建议宽高比={arr}\n")
        else:
            text = text + ", " + IMG_TAIL
            if domain_used == "prompt_image":
                arr = params.get("ar") or "2.35:1"
                fmt = f"【图像形态】建议宽高比={arr}\n"
            else:
                fmt = ("【图像形态】域未能判定，按静态图处理；"
                       "想生成视频请在「域」里选「视频」\n")
        dbg = fmt + dbg
        return (text, dbg)


NODE_CLASS_MAPPINGS = {"LocalStyleHint": LocalStyleHint}
NODE_DISPLAY_NAME_MAPPINGS = {"LocalStyleHint": "中文风格提示-本地 (Local Style Hint)"}


# ------------------------------------------------------------------ 安装步骤
"""
安装步骤
========

1) 复制节点文件
   把本文件放到：
       ComfyUI\\custom_nodes\\prompt_style_local\\local_style_hint.py
   （注意是自定义节点的子目录里，随便起名）

2) 模型和语料
   两种做法，任选：
   a. 直接引用（不占额外空间）—— 保持默认路径不动：
        F:\\llm\\models\\e5-director-v4-noleak
        F:\\llm\\data\\raw\\corpus_v4.jsonl
   b. 搬进 ComfyUI（约 470MB）：
        ComfyUI\\models\\prompt_retrieval\\e5-director-v4-noleak\\
        ComfyUI\\models\\prompt_retrieval\\corpus_v4.jsonl
      然后把节点的「模型目录」「语料文件」两个输入改成对应绝对路径。

3) 装依赖（只有这一步会碰 ComfyUI 的环境）
   便携版（ComfyUI_windows_portable）：
       python_embeded\\python.exe -m pip install -U transformers tokenizers safetensors

   独立安装版（用 venv 跑 ComfyUI 的）：
       用你启动 ComfyUI 的那个 python： -m pip install -U transformers tokenizers safetensors

   ⚠️ 不要重装 torch！
      ComfyUI 自带配套的 torch（cu12x），我们的模型只做推理，任何 torch 都能跑。
      重装 torch 极可能把 ComfyUI 弄坏。

4) 重启 ComfyUI
   节点菜单搜索「中文风格提示-本地」

显存建议
========
默认「设备=cpu」：占 0 显存，单次 50-150ms。8GB 卡强烈建议保持。
只有在你不同时跑大模型时，才切到 cuda。
"""
