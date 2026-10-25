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


def _find_root():
    """找项目根：从本文件与 CWD 分别向上找含 data/raw 的目录。

    ComfyUI 节点会被复制到 <ComfyUI>/custom_nodes/ 下，此时 __file__ 的祖先里
    没有项目根，必须靠 CWD 或由用户显式设置路径。
    """
    seen = set()
    for start in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        p = start
        for _ in range(8):
            if p in seen:
                break
            seen.add(p)
            if os.path.isdir(os.path.join(p, "data", "raw")):
                return p
            nxt = os.path.dirname(p)
            if nxt == p:
                break
            p = nxt
    return os.path.dirname(os.path.abspath(__file__))


ROOT = _find_root()


# ------------------------------------------------------------------ 全局缓存
_CACHE = {}

# ------------------------------------------------------------------ 域路由
# 内联在这里，保证节点自包含（不依赖 <项目根>/...）
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
            f"本项目根推断为：{ROOT}\n"
            f"若本节点是从 custom_nodes 加载的，请把「模型目录」直接写成你 clone 的仓库里\n"
            f"models/e5-director-c27 的完整路径（例如 D:/anchor/models/e5-director-c27）。"
        )
    if not os.path.isfile(corpus_path):
        raise RuntimeError(
            f"语料文件不存在：{corpus_path}\n"
            f"本项目根推断为：{ROOT}（期望在其下找到 data/raw/）\n"
            f"若本节点是从 custom_nodes 加载的，请把「语料文件」改成 clone 仓库里的实际路径。"
        )

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
SUBJECT_FLOOR = 0.52

# ---- 赢家通吃：风格 / 主体 / 工艺 / 材质 四个渠道比大小 ----
# 实测（6 条 query 全渠道打分）：6 条里 5 条正确答案就是分最高的那个渠道。
# 相对比值（渠道分 >= 风格分 x 0.95）在风格分低时会误开，已被推翻。
# 现在只用「每渠道绝对下限 + 高于风格分」。
MAT_FLOOR = 0.52

# ---- 工艺/媒介通道的门槛（同一套相对判据）----
# 实测：蓝晒 1.27 / 金缮 1.31 / 刺绣 1.05 命中；铜版画 0.92、无工艺 0.50~0.91 正确排除
CRAFT_RATIO = 0.95
# 绝对下限比题材高（0.44 而非 0.36）：工艺的假阳性更凶。
# 实测分界：
#   真阳性 蓝晒 0.4827 / 金缮 0.4750 / 刺绣 0.5032
#   假阳性 拉弓->刺绣 0.4070 / 铜版->火柴盒 0.4215 / 骑士->糖画 0.2252
# 假阳性来自"风格分很低时任何工艺都显得相对更强"，所以必须靠绝对下限挡。
# 0.44 是 6 个样本上校准的，样本少，标注为经验值。
CRAFT_FLOOR = 0.52

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


# ================= 结构化输出（内嵌版，节点保持自包含）=================
# 逻辑与 src/prompt_builder.py 一致，但不能 import src/ —— 节点会被单独复制到
# <ComfyUI>/custom_nodes/ 下，那里没有 src/。
_COMP_HINTS = ("symmetr", "one-point", "centred", "centered", "wide-angle",
               "deep focus", "shallow depth", "close-up", "low-angle",
               "overhead", "fisheye", "frame within", "negative space",
               "handscroll", "horizontal")
_LIGHT_HINTS = ("light", "lit", "candle", "neon", "backlit", "diffus",
                "volumetric", "highlight", "shadow", "grain", "glow",
                "flare", "haze", "mist")
_NEG_IMAGE = ["text", "watermark", "signature", "deformed hands",
              "extra fingers", "oversharpened", "hdr halo"]
_NEG_VIDEO = ["scene change", "camera shake", "zoom pumping",
              "flicker", "frame stutter", "morphing"]
_NEG_MOTION = {
    "STATIC": ["fast cutting", "whip pan", "handheld shake", "zooming"],
    "SLOW": ["fast cutting", "whip pan", "handheld shake", "jump cuts"],
    "KINETIC": ["locked-off camera", "static framing", "slow drift"],
}


def _pick(tags, hints, n=2):
    return [t for t in tags if any(h in t.lower() for h in hints)][:n]


# ================= 面向平台的输出格式 =================
# 提示词不是一个字符串，是「面向某个平台的表达」。同一个镜头：
#   Seedance 2.5  要中文五段式，含【时间线】
#   MiniMax H3    要中文整段自然语言，不编号
#   图像/SD       要英文逗号串 + 独立负向，没有时间轴
# 格式错了，内容再对也是白给。
#
# ⚠️ 各平台的字段名与偏好来自公开资料与实测观察，**换平台前请自己核对一次**：
#   Seedance 2.5 的五段式（主体/风格/时间线/BGM/限制）来自 art-aesthetic-vault 的卡片
#   （MIT），该库作者实测过；MiniMax H3 接受中文自然语言整段。
#   其它平台没有核实过，宁可不支持，也不要瞎猜一个格式。

_MOVE_ZH = {"STATIC": "固定机位，不移动", "SLOW": "缓慢推近",
            "KINETIC": "快速手持跟移"}


def _beats(item, domain, dur_s=6):
    """把「镜头的起承转合」拆成三段中文。视频才有。"""
    body = (item.get("description") or "").split(", in the style of")[0].strip()
    parts = [x.strip() for x in body.split(", ") if x.strip()]
    head = parts[0] if parts else "画面主体"
    tail = parts[1] if len(parts) > 1 else ""
    mo = (item.get("motion") or "SLOW").upper()
    move = _MOVE_ZH.get(mo, "缓慢推近")
    a = max(1, int(dur_s / 3))
    b = max(a + 1, int(dur_s * 2 / 3))
    b1 = f"【0—{a}秒】起手就给画面最强的视觉信息：{head}。机位{move}，第一帧就要立住。"
    b2 = f"【{a}—{b}秒】{tail + '；' if tail else ''}动作与光在画面里推进，镜头保持同一运动，不切。"
    b3 = f"【{b}—{dur_s}秒】动作收束，画面停下来；最后一帧停在能当封面的构图上。"
    return [b1, b2, b3]


def _zh_light_style(item, mat, craft):
    """中文的光/色彩/质感描述，给中文平台用。"""
    tags = list(item.get("style_tags") or [])
    out = []
    if mat and mat.get("hit"):
        out.append(mat["phrase"])
    if craft and craft.get("hit"):
        out.append(craft["phrase"])
    light = _pick(tags, _LIGHT_HINTS)
    if light:
        out.append("、".join(light))
    return "；".join(out)


SCENE_FLOOR = 0.39
SUBJECT_TIE_MARGIN = 0.015   # 题材与工艺/材质近似平局时让题材赢


def _core(item, subj, craft, mat, domain, query=""):
    """抽取公共字段，供各平台模板复用。

    query 是用户的中文原话 —— 中文平台的主体必须用它，
    不能用检索到的英文描述（那是风格样例，不是你要的画面）。
    """
    tags = list(item.get("style_tags") or [])
    kw = list(item.get("kw_zh") or [])
    params = item.get("params") or {}
    style = (item.get("style_string") or "").strip()
    if style.startswith("in the style of "):
        style = style[len("in the style of "):]
    body = (item.get("description") or "").split(", in the style of")[0].strip()
    parts = [x.strip() for x in body.split(", ") if x.strip()]
    mo = (item.get("motion") or "SLOW").upper()

    # 低置信度护栏：风格分低于阈值时，库里的"最高分"其实是噪声，
    # 中文模板不能把它当风格打印出来（实测出现过给"竹简"匹配恐怖片）。
    score = float(item.get("score") or 0)
    weak = score < 0.30

    # 图生视频：外观已在首帧里。清空 kw（影响 zh_style）——
    # 注意 zh_light 要等下面构造完再清，否则会被覆盖（这个坑踩过一次）。
    if _CURRENT_TASK == "图生视频":
        kw = []

    who_zh = item.get("director_zh") or item.get("director") or ""
    if _CURRENT_TASK == "图生视频":
        zh_style = ""          # 外观交给首帧
    elif weak:
        zh_style = "<风格：库中没有可靠匹配，请自行指定>"
    else:
        zh_style = who_zh + ("：" + "、".join(kw[:4]) if kw else "")

    # 光/质感优先用材质与工艺通道；两者都没命中时才回落到风格关键词，
    # 否则中文模板里会把同一组词说两遍（「整体走 X」和「光线与质感是 X」）。
    zh_light = []
    if mat and mat.get("hit"):
        zh_light.append(mat.get("zh") or "")
    if craft and craft.get("hit"):
        zh_light.append(craft.get("zh") or "")
    if not zh_light and kw and not weak:
        zh_light.append("、".join(kw[:3]))
    zh_light = "；".join([x for x in zh_light if x])

    # 图生视频：外观已在首帧里，这里给显式占位符（不是留空——
    # 留空会被各模板的 "or 自然光" 默认值填上，等于又给了一个外观来源）
    if _CURRENT_TASK == "图生视频":
        zh_light = "<外观以首帧为准，不用写>"

    # 场景槽位：type=scene 且过门槛就填，**不要求它赢**
    # 场景：优先用 scene_best（场景子集的最优），退而用 top1（若它本身就是场景）
    scene_phrase = ""
    subj_is_scene = False
    if subj:
        sb = subj.get("scene_best")
        if sb and float(sb.get("score") or 0) >= SCENE_FLOOR:
            scene_phrase = sb["phrase"]
        elif (subj.get("type") == "scene"
              and float(subj.get("score") or 0) >= SCENE_FLOOR):
            scene_phrase = subj["phrase"]
            subj_is_scene = True
    subject_phrase = (subj["phrase"]
                      if (subj and subj.get("hit") and not subj_is_scene) else "")

    return {
        "style": style, "zh_style": zh_style, "zh_light": zh_light,
        "scene": scene_phrase,
        "tags": tags, "kw": kw, "params": params, "motion": mo,
        "head": parts[0] if parts else "",
        "tail": parts[1] if len(parts) > 1 else "",
        "subject_zh": (query or "").strip(),
        "subject": subject_phrase,
        "weak": weak, "score": score,
        "ar": params.get("ar") or ("21:9" if domain == "prompt_video" else "2.35:1"),
        "dur": params.get("duration") or "6s",
    }


def _beats_zh(c, dur):
    """时间轴三段：主体用用户原话，运动用中文运镜词。"""
    who = c["subject_zh"] or c["head"]
    move = _MOVE_ZH.get(c["motion"], "缓慢推近")
    light = c["zh_light"] or "按参考描述的光"
    a = max(1, int(dur / 3))
    b = max(a + 1, int(dur * 2 / 3))
    return [
        f"【0—{a}秒】起手就给最强的视觉信息：{who}。机位{move}，第一帧就立住。",
        f"【{a}—{b}秒】{light}；动作在画面里推进，镜头保持同一运动，不切。",
        f"【{b}—{dur}秒】动作收束，画面停下来，最后一帧停在能当封面的构图上。",
    ]


# 平台识别表：关键词 -> 输出格式。顺序从具体到宽泛，先命中先用。
# 认不出来就回落，不猜。
_PLATFORM_HINTS = [
    (("关键帧", "首尾帧", "首帧"), "即梦", "即梦 Seedance · 关键帧（中文）"),
    (("多镜头", "分镜", "多机位"), "可灵", "可灵·多镜头（中文）"),
    (("关键帧", "首尾帧"), "可灵", "可灵 4.0·关键帧（中文）"),
    (("即梦", "seedance", "sd2.5", "sd 2.5", "seedance2.5"), "", "即梦 Seedance 2.5（中文）"),
    (("可灵", "kling"), "", "可灵 4.0（中文，七要素）"),
    (("minimax", "海螺", "hailuo"), "", "MiniMax H3（中文）"),
    (("veo", "gemini", "google"), "", "Veo 3（英文，8 秒单镜）"),
    (("runway", "gen-4", "gen4"), "", "Runway Gen-4（英文，≤60 词）"),
    (("混元", "hunyuan"), "", "混元 HunyuanVideo（中文八段）"),
    (("sora",), "", "Sora 2（已停服 · 仅存档）"),
    (("sd", "stable diffusion", "sdxl", "flux", "midjourney", "mj"), "", "SD 正负向（英文）"),
]


def _detect_format(query, domain):
    """从描述里认出目标平台。返回 (格式名, 依据)；认不出返回 (默认格式, "")。"""
    q = (query or "").lower()
    for words, also, fmt in _PLATFORM_HINTS:
        hit = next((w for w in words if w in q), None)
        if hit and (not also or also in q):
            return fmt, hit
    # 认不出来：视频给通用五面（模型无关），图片给 SD 正负向
    return ("通用五面（英文，模型无关）" if domain == "prompt_video"
            else "SD 正负向（英文）"), ""


def _i2v_cam(c):
    return {"STATIC": "镜头不动（三脚架）",
            "SLOW": "镜头极缓推近",
            "KINETIC": "镜头手持跟随"}.get(c["motion"], "镜头不动")


def _i2v_acts(c, dur):
    a = max(2, dur // 3)
    b = max(a + 1, dur * 2 // 3)
    return a, b


def _fmt_i2v_minimax(item, subj, craft, mat, domain, query=""):
    """MiniMax H3 图生视频：七行结构，外观全部交给 @1。"""
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    a, b = _i2v_acts(c, dur)
    cam = _i2v_cam(c)
    return "\n".join([
        "参考素材：@1 作为首帧，负责画面外观、构图与光线；**不要在提示词里重新描述它**。",
        f"场景顺序：<首帧状态> → <{a}–{b} 秒发生什么> → <最后一帧停在哪>。",
        "主体动作：<谁><具体做什么>，动作速度与幅度是 <说明>。",
        f"相机：{cam}，只一种运动，最后停在 <结束构图>。",
        "声音：<对白>；<环境声>；<同步音效>；<背景音乐>。",
        "保持不变：主体身份、构图、光线、色调与 @1 一致。",
        "不要出现：错字、元素变形、重复主体、水印、字幕。",
    ])


def _fmt_i2v_seedance(item, subj, craft, mat, domain, query=""):
    """即梦 Seedance 图生视频：四段结构，连续整数秒，外观交给图片 1。"""
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    a, b = _i2v_acts(c, dur)
    cam = _i2v_cam(c)
    return "\n".join([
        "（素材绑定：图片 1 作为首帧，只继承外观、构图与光线；不要重新描述它）",
        "",
        "一句话概述：<这一段里发生什么，一句话>。",
        "",
        f"0–{a} 秒：<动作开始，写清方向与幅度>，{cam}。",
        f"{a}–{b} 秒：<动作推进或转折>。",
        f"{b}–{dur} 秒：<收束，停在什么画面上>。",
        "",
        f"全局约束：保持首帧的主体、构图、光线与色调；{c['ar']}；"
        "不要配乐，不要字幕，不要出现文字。",
    ])


def _fmt_i2v_kling(item, subj, craft, mat, domain, query=""):
    """可灵 4.0 图生视频：七要素散文，但只写动作与镜头。"""
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    cam = _i2v_cam(c)
    return (
        "主体与首帧保持一致，面部特征、服装与配色不变。"
        "<写一个看得见的动作，写清方向与幅度>。"
        f"镜头{cam}，一段只写一种运动。"
        "节奏舒缓，单一连续镜头。"
        "环境音：<写环境音或留空>"
    )


def _fmt_motion(item, subj, craft, mat, domain, query=""):
    """图生视频专用：只写动作。

    首帧已经给出了外观、构图、光线，这里再描述一遍等于给模型第二个来源，
    会把首帧重画掉。所以这个模板**刻意不写**外观，只写三件事：
        动作时间轴 / 镜头怎么动 / 什么必须保持不变
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    half = max(2, dur // 2)
    move = {"STATIC": "镜头不动（三脚架）",
            "SLOW": "镜头极缓推近",
            "KINETIC": "镜头手持跟随"}.get(c["motion"], "镜头极缓推近")
    return "\n".join([
        "【动作时间轴】",
        f"0–{half} 秒：<写：谁做什么、往哪个方向动、幅度多大>。",
        f"{half}–{dur} 秒：<写：动作怎么继续或停下；如果要变形，写清从什么变成什么>。",
        "",
        f"【镜头】{move}，只一种运动，不切镜。",
        "",
        "【保持不变】主体、构图、光线、色调与首帧一致；身份、服装、配色不要变。",
    ])


def _fmt_seedance(item, subj, craft, mat, domain, query=""):
    """即梦 Seedance 2.5：官方四段式（中文）。

    依据：即梦 Seedance 2.5 官方提示词指南（用户提供，上下两篇）。官方结构是
        素材绑定 + 一句话概述 + 时间轴或镜头顺序 + 全局约束
    并且是**连续整数秒时间段**（0–3 秒 / 3–8 秒），不留空档；
    官方示例不是分栏而是流水句，所以这里也按流水写。
    官方还强调：动作概括主线、只把少数记忆点写细；
    表情用可观察的面部变化，不要抽象情绪词。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    half = max(2, dur // 2)
    who = c["subject_zh"] or "<主体：外观、服装、位置>"
    light = c["zh_light"] or "自然光"
    move = _MOVE_ZH.get(c["motion"], "缓慢推近")
    act = _KL_ACT.get(c["motion"], _KL_ACT["SLOW"])
    lines = []

    # 素材绑定：只有真的用了素材才写（我们不产出素材，所以作为可选首行）
    lines.append("（素材绑定：图片 1 负责<人物/场景/风格>，视频 1 只参考<动作/运镜>，"
                 "音频 1 负责<音色/节奏>；没有素材就删掉这一行）")
    lines.append("")

    # 一句话概述：主体 + 地点 + 事件 + 题材或风格
    lines.append(f"{light}。{who}。" + (c["scene"] + "。" if c["scene"]
                                         else "<地点与事件补一句：在哪里、发生什么>。"))
    lines.append("")

    # 时间轴：连续整数秒，两段（时长短时够用；要更细就自己往下拆）
    lines.append(f"0–{half} 秒：<景别>。{who}，{light}，{move}。")
    lines.append(f"{half}–{dur} 秒：镜头{ ('轻微跟随' if c['motion'] != 'STATIC' else '保持不动') }；"
                 f"{act}；画面在这里发生一次变化，其余保持不变。")
    lines.append("")

    # 全局约束（官方：机位、光线、色彩、环境声、画幅，以及"无字幕、无配乐"）
    lines.append(f"全程保持主体清晰、背景自然虚化；{c['ar']}；"
                 f"{'轻微手持呼吸感' if c['motion'] != 'STATIC' else '机位完全固定'}；"
                 f"只使用<环境声>，不要配乐，不要字幕。")
    return "\n".join(lines)


def _fmt_seedance_kf(item, subj, craft, mat, domain, query=""):
    """即梦 Seedance 2.5 · 关键帧：第一句必须声明帧顺序。

    官方要求：把每张关键画面作为独立图片按顺序上传，
    并在提示词第一句写「以图片 1 至图片 N 的顺序作为关键帧」；
    然后用连续时间段把每个关键帧挂上去，事件顺序与帧顺序一致。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    who = c["subject_zh"] or "<主体>"
    light = c["zh_light"] or "自然光"
    return "\n".join([
        f"以图片 1 至图片 N 的顺序作为关键帧，制作 {dur} 秒 {c['ar']} 的短片。",
        "",
        f"全片保持{light}；主体外观、服装与身份一致，不换人、不变形。",
        "",
        f"0–{max(2, dur // 3)} 秒对应图片 1；"
        f"{max(2, dur // 3)}–{max(4, dur * 2 // 3)} 秒对应图片 2；"
        f"{max(4, dur * 2 // 3)}–{dur} 秒对应图片 3。",
        "严格保持关键帧的画面顺序与构图，不新增镜头，角色外观随对应关键帧保持一致。",
        "",
        "无文字、无字幕、无闪烁、无元素变形。",
    ])


# ---- Veo3 / Gemini Omni ----
# 依据：Veo3 / Gemini Omni 官方提示词指南（用户提供）。
# 关键约束：**固定 8 秒一段**，一个提示词只写一个镜头；
# 结构是五行英文：8-second video. / [Subject] in [scene]. / [action]. /
# [Lighting, mood, style]. / [Camera].
# 官方明确：塞多个场景、多个人物、多次剪辑会更容易失败或前后不一致。

# 会触发安全审核的方向（官方列的 13 类，这里取能靠关键词判断的几类）
_RISK = [
    (("血", "血腥", "尸体", "残肢", "blood", "gore", "corpse"), "暴力/血腥"),
    (("刀", "枪", "武器", "爆炸", "attack", "knife", "gun", "weapon", "explosion"), "武器/暴力行为"),
    (("裸", "性暗示", "色情", "nude", "naked", "sexual"), "成人内容"),
    (("儿童", "未成年", "小孩", "child", "minor", "kid"), "涉及未成年人（需格外谨慎）"),
    (("名人", "明星", "网红", "celebrity", "famous person"), "真实人物/名人肖像"),
    (("钢铁侠", "蜘蛛侠", "哈利波特", "动漫角色", "游戏角色",
      "iron man", "spider-man", "harry potter", "anime character"), "受版权保护的角色/IP"),
]


def _safety_note(text):
    """粗筛可能触发 Veo 审核的内容。只做提示，不做拦截。"""
    t = (text or "").lower()
    hits = [why for words, why in _RISK
            if any(w.lower() in t for w in words)]
    if not hits:
        return ""
    return ("⚠️ 这条可能触发 Veo 审核：" + "、".join(dict.fromkeys(hits)) +
            "。官方建议改写为中性描述（例如把「持刀攻击」改成「在暗巷里激烈争吵，"
            "戏剧性光线，无肢体暴力」）。")


def _fmt_sora(item, subj, craft, mat, domain, query=""):
    """Sora 2：八模块结构（中文）。

    出处要说明白：**这份不是 OpenAI 官方指南**，是一篇 CSDN 博客的社区总结
    （作者「好好学习，天天向上～」，CC BY-SA 4.0，原文链接见 PLATFORM_MATRIX）。
    官方 cookbook 我们访问不到（403），所以**没有经过官方核对**。

    博主的八个模块：主体 / 场景 / 动作 / 镜头 / 光线 / 风格 / 技术参数 / 限制项。
    几条实用约束（同样来自该文）：
        · 8 秒内只做 1~2 个主动作，动作链清晰
        · 镜头只写一种运动，不要"推进+旋转+拉远"同时出现
        · 风格词控制 3~5 个，多了会互相冲突
        · 限制项长期固定成"防翻车清单"
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    if dur > 8:
        dur = 8   # 该文实测：新手先做 5~8 秒更稳
    who = c["subject_zh"] or "<主体：年龄/外观/服装/道具>"
    light = c["zh_light"] or "自然光，色温与方向写清"
    move = _MOVE_ZH.get(c["motion"], "缓慢推近")
    act = _KL_ACT.get(c["motion"], _KL_ACT["SLOW"])
    return "\n".join([
        f"[主体] {who}。<补：年龄段、外观、服装、道具，具体到可识别>",
        "",
        f"[场景] {(c['scene'] or '') or '<写清：时间、天气、地面材质、前景/中景/远景各有什么>'}",
        "",
        f"[动作] {act}。8 秒内只做 1~2 个主动作，动作链清晰，不要瞬移。",
        "",
        f"[镜头] 中景、平视机位开场，{move}，镜头运动平滑，不做突兀跳切；"
        "只写一种运动。",
        "",
        f"[光线] {light}。写清冷暖、强弱、方向。",
        "",
        f"[风格] {c['zh_style']}。风格词控制在 3~5 个，不要堆冲突风格。",
        "",
        f"[技术参数] 时长 {dur} 秒，24fps，{c['ar']}，4K，画面稳定。",
        "",
        "[限制项] 避免手部畸形、面部扭曲、物体穿模、文字乱码、画面闪烁与跳帧；"
        "禁止字幕、水印、logo。",
    ])


def _fmt_veo(item, subj, craft, mat, domain, query=""):
    """Veo3 / Gemini Omni：官方五行结构（英文），固定 8 秒。

    官方结构：
        8-second video.
        [Subject] in [scene].
        [What the subject is doing].
        [Lighting, mood, and visual style].
        [Camera movement or shot type].

    要点：**一个主体、一个动作、一个场景、一条镜头指令、一种风格**。
    官方说塞多了会失败或前后不一致，所以这里刻意不做时间轴。
    """
    c = _core(item, subj, craft, mat, domain, query)
    who = c["subject"] or "<your subject>"
    scene = c["scene"] or "<your scene>"
    act = {"STATIC": "the subject stays almost still, only breathing and a slight shift",
           "SLOW": "the subject turns slowly toward the camera",
           "KINETIC": "the subject moves quickly across the frame"}.get(
        c["motion"], "the subject turns slowly toward the camera")
    cam = {"STATIC": "Static camera, no movement.",
           "SLOW": "Slow push-in, close-up.",
           "KINETIC": "Handheld tracking shot, medium shot."}.get(
        c["motion"], "Slow push-in, close-up.")
    light = "; ".join(_pick(c["tags"], _LIGHT_HINTS)) or "soft natural light"
    return "\n".join([
        "8-second video.",
        "",
        f"{who} in {scene}.",
        "",
        f"{act}.",
        "",
        f"{light}. {c['style']}.",
        "",
        f"{cam}",
    ])


def _fmt_minimax(item, subj, craft, mat, domain, query=""):
    """MiniMax H3：官方七行模板（中文）。

    依据：MiniMax H3 官方提示词指南（用户提供）。官方模板是结构化的七行：

        参考素材：[@N 负责什么]
        场景顺序：[开场状态] → [主要动作与变化] → [结束状态]
        主体动作：[谁][具体做什么]，动作速度与反应是 [说明]
        相机：[初始景别和角度]，[主要相机运动]，最后停在 [结束构图]
        声音：[对白]；[环境声]；[音效]；[背景音乐]
        保持不变：[人物身份、服装、场景结构等]
        不要出现：[真正影响交付的错误]

    ⚠️ 注意这与「一整段自然语言」不同——我原先按第三方卡片写成一整段，是错的。
    官方示例里素材用 @1/@2 引用，时间戳用小数秒（0.0–1.2s）。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    who = c["subject_zh"] or "<主体：谁>"
    light = c["zh_light"] or "自然光"
    move = _KL_MOVE.get(c["motion"], _KL_MOVE["SLOW"])
    act = _KL_ACT.get(c["motion"], _KL_ACT["SLOW"])
    end_shot = "主体特写" if c["motion"] != "STATIC" else "原构图"
    return "\n".join([
        "参考素材：@1 负责<人物/商品外观>；@2 负责<相机路径/节奏/声音>。"
        "（没有素材就删掉这一行）",
        f"场景顺序：{who}，{c['scene'] or light} → {act} → 停在{end_shot}。",
        f"主体动作：{who}，动作速度与反应是{act}。",
        f"相机：中景、平视机位开场，{move}，最后停在{end_shot}。",
        "声音：<对白>；<环境声>；<同步音效>；<背景音乐>。",
        f"保持不变：主体身份、服装、场景结构与「{light}」不变。",
        "不要出现：错字、元素变形、重复主体、水印、字幕。",
    ])


def _fmt_5aspect(item, subj, craft, mat, domain, query=""):
    """通用五面骨架（英文）：Subject / Motion / Scene / Spatial / Camera。

    出处：OpenMontage 的 video-gen-prompting 指南，引用的论文
    （CMU/Harvard "Building a Precise Video Language"）验证过：
    模型能描述主体与场景，但**系统性漏掉运动、空间、运镜**，
    所以强制填满这五个槽是提升最大的一步。模型无关，谁都能用。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    move = {"STATIC": "camera completely static (no movement, no zoom, no focus change)",
            "SLOW": "slow dolly forward", "KINETIC": "handheld tracking"}.get(
        c["motion"], "slow dolly forward")
    who = c["subject"] or "<your subject>"
    scene = c["scene"] or c["tail"] or "<your scene>"
    # 英文块里不能混中文：光也用英文标签，不用 zh_light
    light = "; ".join(_pick(c["tags"], _LIGHT_HINTS))
    w = 9
    return "\n".join([
        f"{'Subject:':<{w}} {who}",
        f"{'Motion:':<{w}} the subject moves through the frame; nothing else moves",
        f"{'Scene:':<{w}} {scene}" + (f"; light: {light}" if light else ""),
        f"{'Spatial:':<{w}} eye-level, mid shot, subject in the near plane, background readable",
        f"{'Camera:':<{w}} {move}, {dur}s, {c['ar']}, one continuous take, no cuts",
        f"{'Style:':<{w}} {c['style']}",
    ])


def _fmt_runway(item, subj, craft, mat, domain, query=""):
    """Runway Gen-4：只写运动，不写外观，≤60 词。

    出处：Runway 官方 Gen-4 提示词指南的要点是「focus on motion, not appearance;
    one scene per clip; simplicity wins」，词数甜点 ≤60。
    所以这里刻意**不写风格标签**——写多了反而降质。
    """
    c = _core(item, subj, craft, mat, domain, query)
    move = {"STATIC": "Static camera, no movement at all.",
            "SLOW": "Camera dollies in slowly.",
            "KINETIC": "Handheld camera follows close."}.get(c["motion"], "Camera dollies in slowly.")
    who = c["subject"] or "<your subject>"
    return (f"{who}. {move} One continuous scene, no cuts. "
            f"Subject motion is the focus; keep the frame simple.")


def _fmt_hunyuan(item, subj, craft, mat, domain, query=""):
    """腾讯混元 1.5 八段公式（中文）：
    主体 + 运动 + 场景 + 景别 + 运镜 + 光照 + 风格 + 氛围。

    出处：Tencent-Hunyuan/HunyuanVideo-1.5 的 Prompt Handbook。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    who = c["subject_zh"] or c["head"]
    move = _MOVE_ZH.get(c["motion"], "缓慢推近")
    return "\n".join([
        f"主体：{who}",
        f"运动：主体在画面中自然地动作，全程一个镜头不切换",
        f"场景：{c['scene'] or '<写清在哪里、什么时候>'}",
        f"景别：中景",
        f"运镜：{move}，{dur} 秒",
        f"光照：{c['zh_light'] or '按参考描述'}",
        f"风格：{c['zh_style']}",
        f"氛围：安静、克制，情绪落在最后一帧",
        f"（英文锚定：{c['style']}）",
        f"（画幅 {c['ar']}）",
    ])


# ---- 可灵 4.0 ----
# 依据：可灵官方提示词指南（用户提供）。官方顺序是
#   主体 + 动作 + 场景 + 镜头 + 光线 + 节奏 + 声音
# 并强调「用直白的语言说清楚，少用魔幻/震撼这类抽象词」，
# 以及「一段只写一种运镜」「写明面部与服装保持不变」。
_KL_MOVE = {"STATIC": "固定机位，镜头不动",
            "SLOW": "固定机位，镜头轻微推近",
            "KINETIC": "手持跟拍，镜头随主体移动"}
_KL_PACE = {"STATIC": "节奏舒缓，单一连续镜头",
            "SLOW": "节奏舒缓，单一连续镜头",
            "KINETIC": "节奏偏快，单一连续镜头"}
_KL_ACT = {"STATIC": "几乎不动，只有呼吸和发丝有极小的变化",
           "SLOW": "缓慢地转头或移动，动作幅度很小",
           "KINETIC": "快速穿过画面，动作幅度大"}


def _fmt_kling(item, subj, craft, mat, domain, query=""):
    """可灵 4.0 单镜：七要素写成一段散文（官方示例就是这个形态）。"""
    c = _core(item, subj, craft, mat, domain, query)
    who = c["subject_zh"] or "<写清主体：外观、服装、位置>"
    move = _KL_MOVE.get(c["motion"], _KL_MOVE["SLOW"])
    act = _KL_ACT.get(c["motion"], _KL_ACT["SLOW"])
    pace = _KL_PACE.get(c["motion"], _KL_PACE["SLOW"])
    # 场景我们确实不知道（检索只给风格与光），老实留占位符，
    # 否则「场景」和「光线」两栏会重复同一句风格词。
    scene = c["scene"] or "<写清地点与关键物件>"
    light = c["zh_light"] or "自然光"
    return (
        f"{who}，面部特征与服装保持不变。"
        f"{act}。"
        f"{scene}。"
        f"{move}，{light}，{pace}。"
        f"环境音：<写环境音或留空>"
    )


def _fmt_kling_multi(item, subj, craft, mat, domain, query=""):
    """可灵多镜头：先交代场景/人物/风格，再按顺序列镜头，每个镜头不同作用。

    官方要点：3–15 秒内最多 6 个镜头；每个镜头要承担不同任务
    （建立环境 / 交代动作 / 给出反应），不要换角度重复同一信息。
    """
    c = _core(item, subj, craft, mat, domain, query)
    who = c["subject_zh"] or "<主体>"
    style = c["zh_style"]
    move = _KL_MOVE.get(c["motion"], _KL_MOVE["SLOW"])
    return "\n".join([
        f"{who}，{style}。",
        f"镜头 1：中景，{who}的动作与环境，{move}。",
        f"镜头 2：<换一种信息：给反应或给细节，不要重复镜头 1>",
        f"镜头 3：<收尾镜头，停在能当封面的构图上>",
        f"环境音：<写环境音或留空>",
    ])


def _fmt_kling_keyframe(item, subj, craft, mat, domain, query=""):
    """可灵 4.0 关键帧：提示词写的是关键帧之间「发生了什么」。

    官方要点：3–30 秒、最多 10 个关键帧；按时间段写，事件顺序与关键帧顺序一致；
    只在画面状态必须变化的地方加关键帧。
    """
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    half = max(2, dur // 2)
    who = c["subject_zh"] or "<主体>"
    act = _KL_ACT.get(c["motion"], _KL_ACT["SLOW"])
    move = _KL_MOVE.get(c["motion"], _KL_MOVE["SLOW"])
    return "\n".join([
        f"0–{half} 秒：{who}，{c['zh_light'] or '按参考描述的光'}，{move}。",
        f"{half}–{dur} 秒：{act}；画面状态在这里发生一次变化，其余保持不变。",
        f"（总长 {dur} 秒，画幅 {c['ar']}；每加一个关键帧只改一件事，"
        f"不要同时改人物、环境、商品、镜头、光线和风格）",
    ])


def _fmt_sd(item, subj, craft, mat, domain):
    """图像用：英文正向逗号串 + 独立负向，无时间轴。"""
    c = _core(item, subj, craft, mat, domain)
    pos = []
    if c["subject"]:
        pos.append(c["subject"])
    pos.append(c["head"])
    pos.append(c["style"])
    comp = _pick(c["tags"], _COMP_HINTS)
    pos += comp
    if mat and mat.get("hit"):
        pos.append(mat["phrase"])
    if craft and craft.get("hit"):
        pos.append(craft["phrase"])
    sl = " ".join(pos).lower()
    pos += [t for t in _pick(c["tags"], _LIGHT_HINTS) if t.lower() not in sl]
    pos.append(f"{c['ar']}")
    neg = _NEG_IMAGE[:]
    w = 9
    return "\n".join([
        f"{'Positive:':<{w}} {', '.join(dict.fromkeys(pos))}",
        f"{'Negative:':<{w}} {', '.join(dict.fromkeys(neg))}",
    ])


def _structured(item, subj, craft, mat, domain):
    """把检索结果拼成 结构化完整提示词。只输出真的知道的字段。"""
    tags = list(item.get("style_tags") or [])
    params = item.get("params") or {}
    style = (item.get("style_string") or "").strip()
    if style.startswith("in the style of "):
        style = style[len("in the style of "):]

    d = {}
    if domain == "prompt_video":
        mo = (item.get("motion") or "SLOW").upper()
        mv = {"STATIC": "locked-off", "SLOW": "slow push-in",
              "KINETIC": "fast handheld tracking"}.get(mo, "slow push-in")
        d["Shot"] = (f"{mv}, {params.get('duration') or '5s'}, "
                      f"{params.get('ar') or '21:9'}")

    if subj and subj.get("hit"):
        d["Subject"] = subj["phrase"]

    body = (item.get("description") or "").split(", in the style of")[0].strip()
    if domain == "prompt_video" and body:
        # 取前两个从句即可：v18 在部分文档上追加过运镜短语，原描述里本来就有一个，
        # 全留会得到「camera tracking with them, a slow vertical descent」这种重复
        parts = [x.strip() for x in body.split(", ") if x.strip()]
        d["Action"] = ", ".join(parts[:2])

    d["Style"] = style

    if domain != "prompt_video":
        comp = _pick(tags, _COMP_HINTS)
        if comp:
            d["Composition"] = ", ".join(comp)

    light = []
    if mat and mat.get("hit"):
        light.append(mat["phrase"])
    sl = style.lower()
    light += [t for t in _pick(tags, _LIGHT_HINTS) if t.lower() not in sl]
    if light:
        d["Light"] = ", ".join(dict.fromkeys(light))

    if craft and craft.get("hit"):
        d["Medium"] = craft["phrase"]

    if domain == "prompt_video":
        mo = (item.get("motion") or "SLOW").upper()
        d["Negative"] = ", ".join(dict.fromkeys(
            _NEG_VIDEO + _NEG_MOTION.get(mo, [])))
    else:
        d["Aspect"] = params.get("ar") or "2.35:1"
        d["Negative"] = ", ".join(_NEG_IMAGE)

    w = max(len(k) for k in d)
    return "\n".join(f"{k + ':':<{w + 1}} {v}" for k, v in d.items() if v)


_CURRENT_TASK = "文生视频"

_TASK_NOTE = {
    "图生视频": (
        "\n\n【首帧约定】首帧图已提供，画面的外观、构图、光线以首帧为准。"
        "上面**没有填外观相关的槽位是有意的**——再描述一遍会让模型重画首帧。"
        "你只需要补：动什么、往哪个方向动、幅度多大、镜头怎么动、节奏。"
    ),
    "参考生视频": (
        "\n\n【参考约定】逐条写明每个素材负责什么（人物外观 / 动作路径 / 运镜节奏 / 音色），"
        "**并写明不要复制什么**。参考素材只承担明确职责，不要让模型自行推断。"
        "只描述要变化的部分；除变化项外，身份、服装、配色保持不变。"
    ),
}


def _post(text):
    return text + _TASK_NOTE.get(_CURRENT_TASK, "")


def _exact_hits(query, rows, min_len=3):
    """查询里逐字包含条目名、或包含长度 >= min_len 的关键词时，返回这些条目的下标。

    为什么不所有关键词都认：
    部分条目的 kw_zh 里放了泛用风格词（"柔光""颗粒""霓虹"），
    它们是形容词或泛指，会把纯风格查询误判成"命中了某材质"。

    所以只认两类：
        1. 条目名本身（*_zh 字段），任意长度
        2. kw_zh 且长度 >= min_len（默认 3）

    命中的条目按匹配词长度排序，长的优先。
    """
    if not query:
        return []
    hits = []
    for i, r in enumerate(rows):
        name = str(r.get("subject_zh") or r.get("craft_zh") or r.get("mat_zh") or "").strip()
        best = 0
        if name and name in query:
            best = len(name)
        for kw in (r.get("kw_zh") or []):
            kw = str(kw).strip()
            if len(kw) >= min_len and kw in query and len(kw) > best:
                best = len(kw)
        if best:
            hits.append((best, i))
    hits.sort(key=lambda x: -x[0])
    return [i for _, i in hits]


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
        _ex = _exact_hits(q, st["crafts"])
        k = int(csims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(csims[j]))
        c = st["crafts"][k]
        craft = {"exact": bool(_ex), "score": float(csims[k]), "en": c["craft_en"],
                 "zh": c["craft_zh"], "phrase": c["phrase"], "hit": False}

    # ---- 材质/光通道（第四条，仅在「启用材质」打开时计算）----
    mat = None
    if use_material and st.get("mat_emb") is not None and len(st["materials"]):
        msims = (st["mat_emb"] @ qe).numpy()
        _ex = _exact_hits(q, st["materials"])
        k = int(msims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(msims[j]))
        m = st["materials"][k]
        mat = {"exact": bool(_ex), "score": float(msims[k]), "en": m["mat_en"],
               "zh": m["mat_zh"], "phrase": m["phrase"], "hit": False}

    # ---- 题材通道（独立索引，与风格并行）----
    subj = None
    subj_idx = None
    if st.get("subj_emb") is not None and len(st["subjects"]):
        ssims = (st["subj_emb"] @ qe).numpy()
        _ex = _exact_hits(q, st["subjects"])
        k = int(ssims.argmax())
        if _ex:
            k = max(_ex, key=lambda j: float(ssims[j]))
        s = st["subjects"][k]
        subj_idx = k
        subj = {"exact": bool(_ex), "score": float(ssims[k]), "en": s["subject_en"],
                "zh": s["subject_zh"], "phrase": s["phrase"],
                "type": s.get("type", ""), "hit": False}

    # ---- 场景子集单独取最优（不限于 top1，也不改返回元组）----
    if (subj is not None and st.get("subj_emb") is not None
            and len(st.get("subjects") or [])):
        try:
            _sidx = [(i, r) for i, r in enumerate(st["subjects"])
                     if r.get("type") == "scene"]
            if _sidx:
                _ii = [i for i, _ in _sidx]
                _sub = ssims[_ii]
                _kk = int(_sub.argmax())
                _exs = _exact_hits(q, [st["subjects"][i] for i in _ii])
                if _exs:
                    _kk = max(_exs, key=lambda j: float(_sub[j]))
                _row = st["subjects"][_ii[_kk]]
                subj["scene_best"] = {
                    "score": float(_sub[_kk]),
                    "phrase": _row["phrase"],
                    "zh": _row.get("subject_zh", ""),
                }
        except Exception:
            pass

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
                    "style_tags": list(d.get("style_tags") or []),
                    "kw_zh": list(d.get("kw_zh") or []),
                    "description": d.get("description", ""),
                    "params": dict(d.get("params") or {}),
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
                "模型目录": ("STRING", {"default": os.path.join(ROOT, "models/e5-director-c27")}),
                "语料文件": ("STRING", {"default": os.path.join(ROOT, "data/raw/corpus_v21.jsonl")}),
                "题材文件": ("STRING", {"default": os.path.join(ROOT, "data/raw/subjects_v7.jsonl")}),
                "工艺文件": ("STRING", {"default": os.path.join(ROOT, "data/raw/crafts_v6.jsonl")}),
                "材质文件": ("STRING", {"default": os.path.join(ROOT, "data/raw/materials_v8.jsonl")}),
                # 改为默认开启：赢家通吃规则上线后，材质通道不再污染其它渠道
                # （钢甲问出太空船内、丝绸问出湿壁画两个案例已修好）。
                # 仍存在的已知错误是「材质通道内部认错材质名」（暗角/混凝土），
                # 那是材质库内容不足（方案 A），不是通道机制问题。
                "启用材质": ("BOOLEAN", {"default": True}),
                "任务": (["文生视频", "图生视频", "参考生视频"], {"default": "文生视频"}),
                "输出格式": ([
                    "自动（识别平台）",
                    "片段（英文）",
                    "结构化（英文）",
                    "通用五面（英文，模型无关）",
                    "即梦 Seedance 2.5（中文）",
                    "即梦 Seedance · 关键帧（中文）",
                    "MiniMax H3（中文）",
                    "混元 HunyuanVideo（中文八段）",
                    "Runway Gen-4（英文，≤60 词）",
                    "可灵 4.0（中文，七要素）",
                    "可灵·多镜头（中文）",
                    "可灵 4.0·关键帧（中文）",
                    "Veo 3（英文，8 秒单镜）",
                    "Sora 2（已停服 · 仅存档）",
                    "SD 正负向（英文）"],
                    {"default": "片段（英文）"}),
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

    def run(self, *args, **kwargs):
        """对外入口：统一给输出追加「任务约定」"""
        text, dbg = self._run_inner(*args, **kwargs)
        return _post(text), dbg

    def _run_inner(self, 中文描述, 模型目录, 语料文件, 题材文件, 工艺文件, 材质文件, 启用材质,
                   任务, 输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):
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
            _t = "场景" if subj.get("type") == "scene" else "物件"
        dbg = (f"主体[{_t}]: {subj['zh']} {subj['score']:.4f} (下限{SUBJECT_FLOOR}) "
                   f"{'过' if subj['score'] >= SUBJECT_FLOOR else '未过'}\n" + dbg)
        if craft:
            dbg = (f"工艺: {craft['zh']} {craft['score']:.4f} (下限{CRAFT_FLOOR}) "
                   f"{'过' if craft['score'] >= CRAFT_FLOOR else '未过'}\n" + dbg)
        if mat:
            dbg = (f"材质: {mat['zh']} {mat['score']:.4f} (下限{MAT_FLOOR}) "
                   f"{'过' if mat['score'] >= MAT_FLOOR else '未过'}\n" + dbg)

        eligible = []
        for name, obj in (("主体", subj), ("工艺", craft), ("材质", mat)):
            if (obj and obj["score"] > top_style
                    and (obj.get("exact") or obj["score"] >= floors[name])):
                eligible.append((name, obj["score"], obj))

        winner = max(eligible, key=lambda x: x[1]) if eligible else None

        # 近似平局：题材与工艺/材质差在 margin 内时，改判题材
        if winner is not None:
            _by_name = {x[0]: x for x in eligible}
            if (winner[0] in ("工艺", "材质") and "主体" in _by_name
                    and _by_name["主体"][1] >= winner[1] - SUBJECT_TIE_MARGIN):
                dbg = (f"平局修正: 题材 {_by_name['主体'][1]:.4f} 与 {winner[0]} "
                       f"{winner[1]:.4f} 差在 {SUBJECT_TIE_MARGIN} 内 -> 判题材赢\n" + dbg)
                winner = _by_name["主体"]
        if winner is None:
            dbg = (f"最终: 风格最高或无人过门槛 -> 不拼内容 (风格 {top_style:.4f})\n" + dbg)
        else:
            name, sc, obj = winner
            dbg = (f"最终: {name}分最高{'（精确词命中）' if obj.get('exact') else ''}"
                   f" -> 只拼{name} ({sc:.4f} > 风格 {top_style:.4f})\n" + dbg)
            obj["hit"] = True   # 供结构化输出判断（之前漏了，导致 Subject 永远为空）
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
        if float(items[0].get("score") or 0) < 0.30:
            dbg = ("⚠️ 风格置信度低（{} : {:.4f}）：库里没有可靠匹配，"
                   "输出里的风格一栏是占位符，不是推荐。\n".format(
                       items[0].get("director_zh") or items[0].get("director", "?"),
                       float(items[0].get("score") or 0))) + dbg

        global _CURRENT_TASK
        _CURRENT_TASK = 任务

        # 图生视频：只写动作，不套平台模板
        if 任务 == "图生视频":
            # 先确定平台：显式选的优先，否则从描述里认
            _pf = 输出格式
            if _pf == "自动（识别平台）":
                _pf, _why = _detect_format(中文描述, domain_used)
            else:
                _why = "手动指定"
            if "MiniMax" in _pf:
                _m = _fmt_i2v_minimax(items[0], subj, craft, mat, domain_used, 中文描述)
            elif "即梦" in _pf:
                _m = _fmt_i2v_seedance(items[0], subj, craft, mat, domain_used, 中文描述)
            elif "可灵" in _pf:
                _m = _fmt_i2v_kling(items[0], subj, craft, mat, domain_used, 中文描述)
            else:
                _m = _fmt_motion(items[0], subj, craft, mat, domain_used, 中文描述)
            dbg = (f"【格式】图生视频 · 按 {_pf} 的结构（依据『{_why}』），"
                   "外观交给首帧，只写运动\n" + dbg)
            return (_m, dbg)   # 约定块由 run 包装器统一追加

        # 自动识别平台
        if 输出格式 == "自动（识别平台）":
            _auto, _why = _detect_format(中文描述, domain_used)
            输出格式 = _auto
            dbg = (f"【自动】识别为 {_auto}" +
                   (f"（依据『{_why}』）" if _why else "（没认出平台，用通用格式）")
                   + "\n" + dbg)

        # ---- 按目标格式分发 ----
        # 视频专用格式遇到图片域、图片格式遇到视频域，都要回落到通用格式并说明，
        # 不要硬套（时间轴套在静态图上毫无意义）。
        is_video = (domain_used == "prompt_video")
        want = 输出格式
        if want.startswith("Sora"):
            if not is_video:
                return (_structured(items[0], subj, craft, mat, domain_used),
                        "【格式】Sora 是视频格式，当前是图片域 -> 回落到结构化\n" + dbg)
            return (_fmt_sora(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】Sora 2 八模块 · 该平台已停止服务，本格式仅作存档。"
                    "结构来自 CSDN 博客的社区总结（CC BY-SA 4.0），非官方；"
                    "官方 cookbook 亦不可达（403）。\n" + dbg)
        if want.startswith("Veo"):
            if not is_video:
                return (_structured(items[0], subj, craft, mat, domain_used),
                        "【格式】Veo 是视频格式，当前是图片域 -> 回落到结构化\n" + dbg)
            warn = _safety_note(中文描述 + " " + (items[0].get("description") or ""))
            head = "【格式】Veo3 五行结构（英文，固定 8 秒单镜；依据：官方指南）\n"
            if warn:
                head += warn + "\n"
            return (_fmt_veo(items[0], subj, craft, mat, domain_used, 中文描述),
                    head + dbg)
        if want.startswith("即梦"):
            if not is_video:
                return (_structured(items[0], subj, craft, mat, domain_used),
                        "【格式】即梦 Seedance 是视频格式，当前是图片域 -> 回落到结构化\n" + dbg)
            if "关键帧" in want:
                return (_fmt_seedance_kf(items[0], subj, craft, mat, domain_used, 中文描述),
                        "【格式】即梦 Seedance 2.5 · 关键帧（依据：官方提示词指南）\n" + dbg)
            return (_fmt_seedance(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】即梦 Seedance 2.5 四段式（素材绑定/概述/时间轴/全局约束，"
                    "依据：官方提示词指南）\n" + dbg)
        if want == "MiniMax H3（中文）":
            if is_video:
                return (_fmt_minimax(items[0], subj, craft, mat, domain_used, 中文描述),
                        "【格式】MiniMax H3 中文整段（无编号）\n" + dbg)
            return (_structured(items[0], subj, craft, mat, domain_used),
                    "【格式】MiniMax H3 是视频格式，当前是图片域 -> 回落到结构化\n" + dbg)
        if want == "通用五面（英文，模型无关）":
            return (_fmt_5aspect(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】通用五面（Subject/Motion/Scene/Spatial/Camera）\n" + dbg)
        if want == "混元 HunyuanVideo（中文八段）":
            return (_fmt_hunyuan(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】混元 1.5 八段公式（中文）\n" + dbg)
        if want == "Runway Gen-4（英文，≤60 词）":
            return (_fmt_runway(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】Runway Gen-4（只写运动，≤60 词）\n" + dbg)
        if want.startswith("可灵"):
            if not is_video:
                return (_structured(items[0], subj, craft, mat, domain_used),
                        "【格式】可灵是视频格式，当前是图片域 -> 回落到结构化\n" + dbg)
            fn = {"可灵 4.0（中文，七要素）": _fmt_kling,
                  "可灵·多镜头（中文）": _fmt_kling_multi,
                  "可灵 4.0·关键帧（中文）": _fmt_kling_keyframe}.get(want, _fmt_kling)
            return (fn(items[0], subj, craft, mat, domain_used, 中文描述),
                    "【格式】" + want + "（依据：可灵官方提示词指南）\n" + dbg)
        if want == "SD 正负向（英文）":
            return (_fmt_sd(items[0], subj, craft, mat, domain_used),
                    "【格式】SD 正向/负向逗号串（无时间轴）\n" + dbg)
        if want == "结构化（英文）":
            return (_structured(items[0], subj, craft, mat, domain_used), dbg)

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
        <项目根>/...
        <项目根>/...
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
