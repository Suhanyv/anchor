"""低置信度护栏：风格分太低时，中文格式不要假装有风格"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# 1) _core 里判定弱匹配
old = """    who_zh = item.get("director_zh") or item.get("director") or ""
    zh_style = who_zh + ("：" + "、".join(kw[:4]) if kw else "")"""
new = """    # 低置信度护栏：风格分低于阈值时，库里的"最高分"其实是噪声，
    # 中文模板不能把它当风格打印出来（实测出现过给"竹简"匹配恐怖片）。
    score = float(item.get("score") or 0)
    weak = score < 0.30

    who_zh = item.get("director_zh") or item.get("director") or ""
    if weak:
        zh_style = "<风格：库中没有可靠匹配，请自行指定>"
    else:
        zh_style = who_zh + ("：" + "、".join(kw[:4]) if kw else "")"""
assert old in s, "找不到 zh_style 构造处"
s = s.replace(old, new, 1)

# 2) kw 在弱匹配时也不要用作光/质感
old2 = """    if not zh_light and kw:
        zh_light.append("、".join(kw[:3]))"""
new2 = """    if not zh_light and kw and not weak:
        zh_light.append("、".join(kw[:3]))"""
assert old2 in s
s = s.replace(old2, new2, 1)

# 3) _core 返回值带上 weak
old3 = """        "ar": params.get("ar") or ("21:9" if domain == "prompt_video" else "2.35:1"),"""
new3 = """        "weak": weak, "score": score,
        "ar": params.get("ar") or ("21:9" if domain == "prompt_video" else "2.35:1"),"""
assert old3 in s
s = s.replace(old3, new3, 1)

# 4) run() 的 dbg 里加一行警告
old4 = """        dbg = fmt + dbg

        # ---- 按目标格式分发 ----"""
new4 = """        dbg = fmt + dbg
        if float(items[0].get("score") or 0) < 0.30:
            dbg = ("⚠️ 风格置信度低（{} : {:.4f}）：库里没有可靠匹配，"
                   "输出里的风格一栏是占位符，不是推荐。\\n".format(
                       items[0].get("director_zh") or items[0].get("director", "?"),
                       float(items[0].get("score") or 0))) + dbg

        # ---- 按目标格式分发 ----"""
assert old4 in s, "找不到分发锚点"
s = s.replace(old4, new4, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加低置信度护栏")
print("  参数", len(N.LocalStyleHint.INPUT_TYPES()["required"]))
