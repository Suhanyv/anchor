"""
近似平局规则：题材与工艺/材质差距很小时，让题材赢

起因
----
「一个人拿起桌上的竹简」实测：

    题材 简牍 0.6143   ← 正确
    工艺 竹编 0.6202   ← 高 0.006，赢了，输出里出现了"竹编"

这不是场景改动造成的，是第二批补进「竹编」之后出现的**近邻翻转**。
差 0.006 就决定输出对错，说明赢家通吃在这种并列情况下太脆。

规则
----
若 题材 与 工艺/材质 的分数差在 MARGIN(0.015) 以内，**判题材赢**。
理由：提到一个具体物件（竹简）比提到一个技法类别（竹编）更具体，
用户写"竹简"时指的是那个东西，不是"竹子编织"这种工艺。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "SUBJECT_TIE_MARGIN" not in s:
    s = s.replace("SCENE_FLOOR = 0.36",
                  "SCENE_FLOOR = 0.36\nSUBJECT_TIE_MARGIN = 0.015   # 题材与工艺/材质近似平局时让题材赢",
                  1)

# 在 winner 计算之后加一次修正
anchor = """        winner = max(eligible, key=lambda x: x[1]) if eligible else None"""
assert anchor in s, "winner 计算处变了"
add = anchor + """

        # 近似平局：题材与工艺/材质差在 margin 内时，改判题材
        if winner is not None:
            _by_name = {x[0]: x for x in eligible}
            if (winner[0] in ("工艺", "材质") and "主体" in _by_name
                    and _by_name["主体"][1] >= winner[1] - SUBJECT_TIE_MARGIN):
                dbg = (f"平局修正: 题材 {_by_name['主体'][1]:.4f} 与 {winner[0]} "
                       f"{winner[1]:.4f} 差在 {SUBJECT_TIE_MARGIN} 内 -> 判题材赢\\n" + dbg)
                winner = _by_name["主体"]"""
s = s.replace(anchor, add, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  语法 OK，参数", len(N.LocalStyleHint.INPUT_TYPES()["required"]))
print("  SUBJECT_TIE_MARGIN =", N.SUBJECT_TIE_MARGIN)
