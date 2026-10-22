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
_MOTION_WORDS = ["慢", "动", "推", "摇", "移", "跟", "环绕", "升", "降", "甩",
                 "转", "秒", "帧", "切", "长镜", "手持", "漂", "运镜"]


def _detect_domain(text):
    t = (text or "").lower()
    v = sum(1 for w in _VIDEO_HINTS if w.lower() in t)
    i = sum(1 for w in _IMAGE_HINTS if w.lower() in t)
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


def _load(model_dir, corpus_path, device):
    key = (model_dir, corpus_path, device)
    if key in _CACHE:
        return _CACHE[key]

    import torch
    from transformers import AutoModel, AutoTokenizer

    if not os.path.isdir(model_dir):
        raise RuntimeError(
            f"模型目录不存在：{model_dir}\n"
            f"请把 F:\\llm\\models\\e5-director-v4-noleak 整个文件夹复制到这个路径，"
            f"或把本节点的「模型目录」改成实际位置。"
        )
    if not os.path.isfile(corpus_path):
        raise RuntimeError(f"语料文件不存在：{corpus_path}")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]

    tok = AutoTokenizer.from_pretrained(model_dir)
    enc = AutoModel.from_pretrained(model_dir).to(device).eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    # 预编码全部文档（只做一次）
    import torch.nn.functional as F
    texts = [d["text_semantic"] for d in corpus]
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok(["passage: " + t for t in texts[i:i + 32]], padding=True,
                    truncation=True, max_length=128, return_tensors="pt")
            b = {k: v.to(device) for k, v in b.items()}
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
    doc_emb = torch.cat(out).cpu()

    _CACHE[key] = {"corpus": corpus, "doc_emb": doc_emb, "tok": tok, "enc": enc, "device": device}
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


def _rank(q, model_dir, corpus_path, device, topk, by, domain="auto"):
    st = _load(model_dir, corpus_path, device)
    qe = _encode_query(st, q)
    sims = (st["doc_emb"] @ qe).numpy()
    corpus = st["corpus"]

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
        return sorted(best.values(), key=lambda x: -x["score"])[:topk], "director"

    out = []
    for i in sorted(allowed, key=lambda j: -sims[j])[:topk]:
        d = corpus[int(i)]
        out.append({"score": float(sims[int(i)]), "director": d["director"],
                    "director_zh": d.get("director_zh", ""),
                    "facet": d.get("facet", "base"),
                    "style_string": d.get("prompt", ""),
                    "prompt": d.get("prompt", "")})
    return out, "prompt"


# ------------------------------------------------------------------ 节点
class LocalStyleHint:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "中文描述": ("STRING", {"multiline": True,
                                       "default": "远远的镜头，一条草船在江上，有个老渔夫在划"}),
                "模型目录": ("STRING", {"default": r"F:\llm\models\e5-director-v4-noleak"}),
                "语料文件": ("STRING", {"default": r"F:\llm\data\raw\corpus_v6.jsonl"}),
                "设备": (["cpu", "cuda"], {"default": "cpu"}),
                "域": (["自动", "图片", "视频", "不限"], {"default": "自动"}),
                "匹配方式": (["导演/风格聚合", "逐条提示词"], {"default": "导演/风格聚合"}),
                "候选数": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "追加到": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("风格串", "调试信息")
    FUNCTION = "run"
    CATEGORY = "中文 风格"

    @classmethod
    def IS_CHANGED(cls, **kw):
        return float("NaN")   # 每次都重算，避免缓存旧的 query 结果

    def run(self, 中文描述, 模型目录, 语料文件, 设备, 域, 匹配方式, 候选数, 追加到):
        items, mode = _rank(中文描述, 模型目录, 语料文件, 设备, 候选数, 匹配方式,
                            {"自动": "auto", "图片": "image", "视频": "video", "不限": "any"}.get(域, "auto"))
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
