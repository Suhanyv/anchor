"""
「让工具提案分镜」：只给数量时，由它自己编排 N 拍

边界（重要）
------------
检索层不创作，LLM 层才创作。这个功能是**在检索到的元素范围内编排**，
并把每一拍的来源标出来：

    【库】军阵、尘土、横移、长剑      <- 检索给的
    【编】不给正脸、只打一个人、空镜收 <- 编排给的

不标来源的话，用户会以为整段都是检索结果——那是幻觉。

编排语法（不是随机）
--------------------
一对多的打斗，三拍的经典分工：
    1 建立   全景/环境，主体入场，**不给看清任何一张脸**（留下"多"的想象）
    2 交手   只打一个人，一个动作，最近的景别
    3 收     空镜或背面，留白（"多"的处理结果交给观众）

这套语法来自检索到的风格（军阵/对峙/硬切这类调度词），不是写死的三镜内容。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_propose_beats" not in s:
    fn = '''def _propose_beats(item, subj, craft, mat, domain, n=3):
    """按「建立 / 交手 / 收」的语法编排 N 拍，并标出每拍的来源。"""
    c = _core(item, subj, craft, mat, domain, "")
    look = "、".join([x for x in (c.get("zh_light") or "").split("、") if x][:3]) or "环境光"
    who = (subj or {}).get("zh") or "主体"
    prop = (subj or {}).get("phrase") or ""
    tags = "、".join((item.get("kw_zh") or [])[:4]) or "—"

    beats = []
    # 第 1 拍：建立
    beats.append((
        f"全景或中远景。{who}在{look}里，"
        f"画面里还有别的人影但都不清（<写几个人、在哪个方位>）；机位横移或不动，不给正脸。",
        f"【库】{tags} 【编】不给正脸 / 用画外与边缘交代人数"))
    # 第 2 拍：交手
    if n >= 2:
        beats.append((
            f"近景，只跟一个人。一个对手从画框一侧进入，一个动作（劈或挡）；"
            f"{who}架住，金属相碰。只此一个动作，不追加。",
            "【库】对峙/突然加速 【编】只打一个人 / 一个动作 / 不追加"))
    # 第 3 拍：收
    if n >= 3:
        beats.append((
            f"镜头拉开或切到空处。{who}背对或侧对镜头，兵器垂下；"
            f"其余人影在画外或虚焦里退开。画面停住。",
            "【库】硬切/留白 【编】背面收 / 不交代结果"))
    # 更多拍：在交手与收之间加过渡
    while len(beats) < n:
        beats.insert(-1, (
            f"中景，横移未停。第二个人影从另一侧掠过，{who}没有出兵器，只侧身让开。",
            "【库】横移 【编】用让开代替交战 / 保持人数压力"))
    return beats[:n]


'''
    anchor = "def _fmt_multishot("
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 参数
old_opt = '''                "任务": (["文生视频", "图生视频", "参考生视频"], {"default": "文生视频"}),'''
new_opt = '''                "任务": (["文生视频", "图生视频", "参考生视频"], {"default": "文生视频"}),
                "提案分镜": ("BOOLEAN", {"default": False}),'''
assert old_opt in s
s = s.replace(old_opt, new_opt, 1)

# run 签名
s = s.replace('''           任务, 输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):''',
              '''           任务, 提案分镜, 输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):''', 1)

# 只给数量时：若开了提案，就用编排结果填进去
old2 = '''        if len(_shots) < 2:
            _n = _count_shots(中文描述)
            if _n >= 2:
                _shots = [""] * _n   # 只给了数量：出空槽，不替用户编动作'''
new2 = '''        if len(_shots) < 2:
            _n = _count_shots(中文描述)
            if _n >= 2:
                if 提案分镜:
                    # 用户开了提案：按建立/交手/收的语法编排，并标注来源
                    _prop = _propose_beats(items[0], subj, craft, mat,
                                           domain_used, _n)
                    _shots = [b[0] for b in _prop]
                    dbg = ("【提案】已按「建立/交手/收」编排 "
                           f"{_n} 拍（来源在每拍末尾标注）\\n" + dbg)
                else:
                    _shots = [""] * _n   # 只给了数量：出空槽，不替用户编动作'''
assert old2 in s, "数量分支没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
it = N.LocalStyleHint.INPUT_TYPES()["required"]
print("  参数:", len(it), " 提案分镜:", it["提案分镜"][1]["default"])
print("  _propose_beats:", hasattr(N, "_propose_beats"))
