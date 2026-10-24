"""
提示词组装器：把四通道的检索结果拼成**结构化的完整提示词**

为什么单独做
------------
现在节点输出的是一行逗号串 + 一个通用收尾：
    in the style of Wong Kar-wai, saturated neon, ..., still frame, sharp focus, fine detail

那不是"好提示词"，那是"一段风格词"。图像和视频的提示词结构本来不一样：

    图像   主体 / 风格 / 构图 / 光与材质 / 画幅 / 负面
    视频   镜头与时长 / 起幅 / 变化 / 落幅 / 风格 / 光 / 负面

负面提示词的来源
----------------
两种，都自动生成，不手写：

1. **技术负面**：图像用 text/watermark/deformed hands，视频用 cuts/shake/flicker。
   这是输出形态决定的，不是风格决定的。

2. **对比负面**：对实体 X，找出「很多其他实体都有、但 X 从来没有」的风格标签。
   逻辑：你选了库布里克，那"手持、暖色、自然光"就是该避免的方向。
   纯从语料统计出来，不需要人写。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- 技术负面：由输出形态决定 ----
NEG_TECH = {
    "image": ["text", "watermark", "signature", "deformed hands", "extra fingers",
              "oversharpened", "hdr halo"],
    "video": ["cuts", "scene change", "camera shake", "zoom pumping", "flicker",
              "frame stutter", "morphing"],
}

# ---- 运动幅度决定的负面：这个比"从标签统计推负面"靠得住得多 ----
# 试过从语料统计"别的实体有、这个没有"的标签当负面，产出是
# "static / kinetic / natural light" 这类语义混乱的词，已放弃。
NEG_MOTION = {
    "STATIC": ["fast cutting", "whip pan", "handheld shake", "zooming"],
    "SLOW": ["fast cutting", "whip pan", "handheld shake", "jump cuts"],
    "KINETIC": ["locked-off camera", "static framing", "slow drift"],
}

# 这些标签看起来像"构图/摄影"词，可以单独填进 Composition 栏
COMPOSITION_HINTS = (
    "symmetr", "one-point", "centred", "centered", "wide-angle", "deep focus",
    "shallow depth", "close-up", "low-angle", "overhead", "fisheye",
    "frame within", "negative space", "handscroll", "horizontal",
)

# 光源/质感词，可以填进 Light / Material 栏
LIGHT_HINTS = (
    "light", "lit", "candle", "neon", "backlit", "diffus", "volumetric",
    "highlight", "shadow", "grain", "glow", "flare", "haze", "mist",
)


def load_corpus(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def contrast_negatives(director, corpus, k=4):
    """找出「很多别的实体有、这个实体没有」的标签 —— 该避免的方向。

    纯统计：对每个标签统计它出现在多少个实体里、是否出现在本实体。
    排序按「出现实体数」，取前 k 个本实体没有的。
    """
    owners = {}
    mine = set()
    for d in corpus:
        for t in d.get("style_tags") or []:
            owners.setdefault(t.strip().lower(), set()).add(d["director"])
            if d["director"] == director:
                mine.add(t.strip().lower())
    cand = [(len(v), t) for t, v in owners.items() if t not in mine and len(v) >= 3]
    cand.sort(reverse=True)
    out = []
    for _, t in cand:
        if len(out) >= k:
            break
        # 跳过与技术负面重复的
        if any(t in x for x in NEG_TECH["image"] + NEG_TECH["video"]):
            continue
        out.append(t)
    return out


def _split_tags(tags, hints):
    """从标签里挑出符合某类提示词的，返回前两个"""
    hit = [t for t in tags if any(h in t.lower() for h in hints)]
    return hit[:2]


def build_image(query, item, subj=None, craft=None, mat=None, corpus=None):
    """组装图像提示词。返回 dict（键按顺序即输出顺序）。

    只输出「真的知道」的字段：没有主体就不硬塞一行占位文字。
    """
    tags = item.get("style_tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    params = item.get("params") or {}

    out = {}
    subj_phrase = (subj or {}).get("phrase") if subj and subj.get("hit") else None
    if subj_phrase:
        out["Subject"] = subj_phrase

    # 块状输出里 label 已经写了 Style，把 "in the style of" 前缀去掉
    style = (item.get("style_string") or "").strip()
    if style.startswith("in the style of "):
        style = style[len("in the style of "):]
    out["Style"] = style

    comp = _split_tags(tags, COMPOSITION_HINTS)
    if comp:
        out["Composition"] = ", ".join(comp)

    light = []
    if mat and mat.get("hit"):
        light.append(mat["phrase"])
    style_l = style.lower()
    light += [t for t in _split_tags(tags, LIGHT_HINTS) if t.lower() not in style_l]
    if light:
        out["Light"] = ", ".join(dict.fromkeys(light))

    if craft and craft.get("hit"):
        out["Medium"] = craft["phrase"]

    out["Aspect"] = params.get("ar") or "2.35:1"
    out["Negative"] = ", ".join(dict.fromkeys(NEG_TECH["image"]))
    return out


def build_video(query, item, subj=None, craft=None, mat=None, corpus=None):
    """组装视频提示词。视频必须说清「镜头怎么动、多长、画幅」。"""
    tags = item.get("style_tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    params = item.get("params") or {}
    motion = (item.get("motion") or "SLOW").upper()
    move_en = {"STATIC": "locked-off", "SLOW": "slow push-in",
               "KINETIC": "fast handheld tracking"}.get(motion, "slow push-in")

    out = {}
    out["Shot"] = f"{move_en}, {params.get('duration') or '5s'}, {params.get('ar') or '21:9'}"

    subj_phrase = (subj or {}).get("phrase") if subj and subj.get("hit") else None
    if subj_phrase:
        out["Subject"] = subj_phrase

    # 文档描述里从 corpus_v18 起带运镜短语，用它作为「这个镜头里发生什么」
    desc = (item.get("description") or "").strip()
    body = desc.split(", in the style of")[0].strip()
    if body:
        out["Action"] = body[:200]

    camera = _split_tags(tags, ("track", "pan", "push", "crane", "orbit", "handheld",
                                "static", "dolly", "tilt", "zoom"))
    if camera:
        out["Camera"] = ", ".join(camera)

    style = (item.get("style_string") or "").strip()
    if style.startswith("in the style of "):
        style = style[len("in the style of "):]
    out["Style"] = style

    light = []
    if mat and mat.get("hit"):
        light.append(mat["phrase"])
    style_l = style.lower()
    light += [t for t in _split_tags(tags, LIGHT_HINTS) if t.lower() not in style_l]
    if light:
        out["Light"] = ", ".join(dict.fromkeys(light))

    if craft and craft.get("hit"):
        out["Medium"] = craft["phrase"]

    neg = list(NEG_TECH["video"]) + NEG_MOTION.get(motion, [])
    out["Negative"] = ", ".join(dict.fromkeys(neg))
    return out


def format_block(d):
    """把 dict 排版成可直接粘的文本"""
    w = max(len(k) for k in d)
    lines = []
    for k, v in d.items():
        if not v:
            continue
        lines.append(f"{k + ':':<{w + 1}} {v}")
    return "\n".join(lines)


def format_inline(d):
    """单行版：只取内容拼成逗号串，用于 CLIP 文本编码"""
    return ", ".join(v for v in d.values() if v)


def build(query, item, domain, subj=None, craft=None, mat=None, corpus=None, style="block"):
    """对外统一入口。domain: prompt_image / prompt_video"""
    if domain == "prompt_video":
        d = build_video(query, item, subj, craft, mat, corpus)
    else:
        d = build_image(query, item, subj, craft, mat, corpus)
    return d, (format_block(d) if style == "block" else format_inline(d))
