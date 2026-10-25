"""
把「场景」接进节点：type=scene 的题材条目填 scene 槽位

设计要点
--------
1. 场景**不参与赢家通吃**——只填「场景」那一格，不改变现有四个通道的竞争
2. 判定条件是 `score >= SCENE_FLOOR`，不要求它赢
   （这样"汝窑在桌上"里，汝窑赢工艺，场景仍然能填上"桌上"）
3. 若赢家就是场景条目，则它不再当 subject 用（避免把"卧室"写进主体栏）
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ---- 1) 常量 ----
if "SCENE_FLOOR" not in s:
    anchor = "def _core(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, "SCENE_FLOOR = 0.42\n\n\n" + anchor, 1)

# ---- 2) _core 里拆出 scene 与 subject ----
old = '''    return {
        "style": style, "zh_style": zh_style, "zh_light": zh_light,'''
new = '''    # 场景槽位：type=scene 且过门槛就填，**不要求它赢**
    subj_is_scene = bool(subj and subj.get("type") == "scene"
                         and float(subj.get("score") or 0) >= SCENE_FLOOR)
    scene_phrase = subj["phrase"] if subj_is_scene else ""
    subject_phrase = (subj["phrase"]
                      if (subj and subj.get("hit") and not subj_is_scene) else "")

    return {
        "style": style, "zh_style": zh_style, "zh_light": zh_light,
        "scene": scene_phrase,'''
assert old in s, "_core 返回字典锚点变了"
s = s.replace(old, new, 1)

# subject 改为按上面的判定（原来是 subj.hit 就算 subject）
old2 = '''        "subject": subj["phrase"] if (subj and subj.get("hit")) else "",'''
new2 = '''        "subject": subject_phrase,'''
assert old2 in s, "subject 那一行变了"
s = s.replace(old2, new2, 1)

# ---- 3) 各格式的「场景」槽位改成用 c["scene"] ----
REPL = [
    ('    scene = "<your scene>"\n',
     '    scene = c["scene"] or "<your scene>"\n', "_fmt_veo"),
    ('    scene = c["tail"] or "<your scene>"\n',
     '    scene = c["scene"] or c["tail"] or "<your scene>"\n', "_fmt_5aspect"),
    ('    scene = "<写清地点与关键物件>"\n',
     '    scene = c["scene"] or "<写清地点与关键物件>"\n', "_fmt_kling"),
    ('        f"场景：<写清在哪里、什么时候>",\n',
     '        f"场景：{c[\'scene\'] or \'<写清在哪里、什么时候>\'}",\n', "_fmt_hunyuan"),
    ('        "[场景] <写清：时间、天气、地面材质、前景/中景/远景各有什么>",\n',
     '        f"[场景] {(c[\'scene\'] or \'\') or \'<写清：时间、天气、地面材质、前景/中景/远景各有什么>\'}",\n',
     "_fmt_sora"),
    ('        f"场景顺序：{who}，{light} → {act} → 停在{end_shot}。",\n',
     '        f"场景顺序：{who}，{c[\'scene\'] or light} → {act} → 停在{end_shot}。",\n',
     "_fmt_minimax"),
    ('    lines.append(f"{light}。{who}。<地点与事件补一句：在哪里、发生什么>。")\n',
     '    lines.append(f"{light}。{who}。" + (c["scene"] + "。" if c["scene"]\n'
     '                                         else "<地点与事件补一句：在哪里、发生什么>。"))\n',
     "_fmt_seedance"),
]
for old_s, new_s, tag in REPL:
    if old_s in s:
        s = s.replace(old_s, new_s, 1)
        print(f"  已接场景槽位: {tag}")
    else:
        print(f"  ⚠️ 没找到: {tag}")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  语法 OK，参数", len(N.LocalStyleHint.INPUT_TYPES()["required"]))
print("  SCENE_FLOOR =", N.SCENE_FLOOR)
