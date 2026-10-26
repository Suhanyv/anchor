"""
整段式输出：一气写下来，不分栏、不带【】标签

为什么
------
用户指出："不是一段词出多个，而是出一整段。"

现在的即梦格式虽然按官方四段排，但写成了带标签的表格：

    【共用】…
    一句话概述：…
    0–1 秒：…
    摄影层：…
    不要出现：…

而**官方示例是一气写下来的散文**：

    写实自然纪录片质感，温暖午后的森林草坡。一只圆润的熊猫幼崽笨拙地顺坡滚下。
    主体与场景：幼崽毛发蓬松…；草坡上有苔藓、三叶草…
    0–3 秒：低机位中远景。熊猫趴在斜坡上，开始缓慢侧滚…
    3–8 秒：镜头轻微向右下方跟随…
    全程保持熊猫清晰、背景自然虚化；轻微手持呼吸感。

差别不在内容，在**形状**：散文能被模型当段落读，分栏表格会被当成指令清单。

所以加一个 `整段` 变体：风格、时间轴、摄影、声音、禁忌全部缝进一段话。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_fmt_seedance_prose" not in s:
    fn = '''def _fmt_seedance_prose(item, subj, craft, mat, domain, query=""):
    """即梦整段式：一整段散文，不分栏不带标签。"""
    c = _core(item, subj, craft, mat, domain, query)
    dur = int(str(c["dur"]).rstrip("s") or 6)
    half = max(2, dur // 2)
    who = c["subject_zh"] or "<主体>"
    light = c["zh_light"] or "自然光"
    style = c["zh_style"] or ""
    move = {"STATIC": "固定机位", "SLOW": "镜头极缓推近",
            "KINETIC": "手持跟随"}.get(c["motion"], "镜头极缓推近")
    # 摄影层揉成短句，不加"摄影层"三字
    cine = _cine_line(c).split("\\n")[0].replace("摄影层：", "")

    seg = [f"{light}。"]
    if style:
        seg.append(f"{style}。")
    seg.append(f"{who}。")
    seg.append(f"0 到 {half} 秒，{who}，{move}。")
    seg.append(f"{half} 到 {dur} 秒，<写：动作怎么继续或停下；"
               f"要变形就写清从什么变成什么>。")
    seg.append(f"{cine}")
    seg.append(f"{c['ar']}，全程保持主体清晰、背景自然虚化。")
    seg.append("只使用<环境声>，不要配乐，不要字幕。")
    seg.append("不要出现<2-4 个会让这条废掉的错误，例如多余的人、"
               "手部畸形、兵器穿模>。")
    return "".join(seg)


'''
    anchor = "def _fmt_seedance_kf("
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

    # 登记格式
    old_opt = '                    "即梦 Seedance 2.5（中文）",'
    new_opt = (old_opt + '\n'
               '                    "即梦 Seedance 2.5 · 整段（中文）",')
    assert old_opt in s
    s = s.replace(old_opt, new_opt, 1)

    # 分派
    old_disp = '''            if "关键帧" in want:'''
    new_disp = '''            if "整段" in want:
                return (_fmt_seedance_prose(items[0], subj, craft, mat,
                                            domain_used, 中文描述),
                        "【格式】即梦整段式（不分栏，一气写下来）\\n" + dbg)
            if "关键帧" in want:'''
    assert old_disp in s
    s = s.replace(old_disp, new_disp, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
f = N.LocalStyleHint.INPUT_TYPES()["required"]["输出格式"][0]
print("  格式", len(f), "种；含整段:", any("整段" in x for x in f))
