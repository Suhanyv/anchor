"""
两件事：
① 图生视频改用「只写动作」模板（不再套平台模板）
② 输出格式加「自动（识别平台）」——从描述里认出你在用哪个模型

② 为什么可做
------------
平台名是**明确的字符串事实**，不是语义推测：
    "用即梦做一段…"        -> 即梦
    "sd2.5 出图"           -> 即梦 Seedance（用户对即梦的俗称）
    "可灵四代，多镜头"       -> 可灵·多镜头
    "veo3 八秒"            -> Veo 3
认不出来就回落到通用格式，并在调试里说明——**不猜**。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ============ ① 图生视频专用：只写动作 ============
if "_fmt_motion" not in s:
    fn = '''def _fmt_motion(item, subj, craft, mat, domain, query=""):
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
    return "\\n".join([
        "【动作时间轴】",
        f"0–{half} 秒：<写：谁做什么、往哪个方向动、幅度多大>。",
        f"{half}–{dur} 秒：<写：动作怎么继续或停下；如果要变形，写清从什么变成什么>。",
        "",
        f"【镜头】{move}，只一种运动，不切镜。",
        "",
        "【保持不变】主体、构图、光线、色调与首帧一致；身份、服装、配色不要变。",
    ])


'''
    anchor = "def _fmt_seedance(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# ============ ② 平台识别 ============
if "_detect_format" not in s:
    det = '''# 平台识别表：关键词 -> 输出格式。顺序从具体到宽泛，先命中先用。
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


'''
    anchor2 = "def _fmt_motion(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor2 in s
    s = s.replace(anchor2, det + anchor2, 1)

# ============ ①② 接进 run ============
# 选项：自动 放在第一位
old_opt = '''                "输出格式": (["片段（英文）",'''
if old_opt in s:
    s = s.replace(old_opt, '''                "输出格式": (["自动（识别平台）", "片段（英文）",''', 1)
    print("  输出格式已加「自动（识别平台）」")

# 在图生视频时改走 _fmt_motion；自动时先识别
anchor3 = '''        global _CURRENT_TASK
        _CURRENT_TASK = 任务
'''
assert anchor3 in s
add3 = anchor3 + '''
        # 图生视频：只写动作，不套平台模板
        if 任务 == "图生视频":
            _m = _fmt_motion(items[0], subj, craft, mat, domain_used, 中文描述)
            dbg = "【格式】图生视频专用（只写动作，不描述外观）\\n" + dbg
            return (_post(_m), dbg)

        # 自动识别平台
        if 输出格式 == "自动（识别平台）":
            _auto, _why = _detect_format(中文描述, domain_used)
            输出格式 = _auto
            dbg = (f"【自动】识别为 {_auto}" +
                   (f"（依据『{_why}』）" if _why else "（没认出平台，用通用格式）")
                   + "\\n" + dbg)
'''
s = s.replace(anchor3, add3, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
it = N.LocalStyleHint.INPUT_TYPES()["required"]
print("  参数:", len(it), " 输出格式首项:", it["输出格式"][0][0])
print("  _fmt_motion:", hasattr(N, "_fmt_motion"), " _detect_format:", hasattr(N, "_detect_format"))
