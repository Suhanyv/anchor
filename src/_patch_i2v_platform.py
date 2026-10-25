"""
图生视频按平台出结构：MiniMax H3 / 即梦 / 可灵 各一套

问题
----
上一版图生视频统一用"只写动作"的通用模板，**把用户指定的平台丢了**。
用户说"用 MiniMax H3"时，他要的是 MiniMax 的七行结构，
只是外观那几行换成 @1 引用、内容只写运动。

各平台 i2v 该长什么样（依据各自的官方指南）
--------------------------------------------
MiniMax H3   七行：参考素材 / 场景顺序 / 主体动作 / 相机 / 声音 / 保持不变 / 不要出现
即梦 Seedance 四段：素材绑定 / 一句话概述 / 连续整数秒时间轴 / 全局约束
可灵 4.0     七要素散文：主体 / 动作 / 场景 / 镜头 / 光线 / 节奏 / 声音
其他         通用：动作时间轴 / 镜头 / 保持不变
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_fmt_i2v_minimax" not in s:
    fns = '''def _i2v_cam(c):
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
    return "\\n".join([
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
    return "\\n".join([
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


'''
    anchor = "def _fmt_motion(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fns + anchor, 1)

# 路由：i2v 分支按平台分派
old = '''        if 任务 == "图生视频":
            _m = _fmt_motion(items[0], subj, craft, mat, domain_used, 中文描述)
            dbg = "【格式】图生视频专用（只写动作，不描述外观）\\n" + dbg
            return (_m, dbg)   # 约定块由 run 包装器统一追加，这里不再加'''
new = '''        if 任务 == "图生视频":
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
                   "外观交给首帧，只写运动\\n" + dbg)
            return (_m, dbg)   # 约定块由 run 包装器统一追加'''
assert old in s, "i2v 分支变了"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加三套平台化 i2v")
for fn in ("_fmt_i2v_minimax", "_fmt_i2v_seedance", "_fmt_i2v_kling"):
    print(f"    {fn}: {hasattr(N, fn)}")
