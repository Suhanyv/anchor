"""把节点里的门控逻辑换成「赢家通吃」（一次性改文件，避免手写巨型字面量）"""
import os
import ast
import re

P = os.path.join(ROOT, "comfyui/local_style_hint.py")
s = open(P, encoding="utf-8").read()

START = "        # 题材通道：相对判据 —— 只有题材比风格更贴合时才拼进去"
END = '        if subj and subj.get("hit"):\n            text = subj["phrase"] + ", " + text'

i = s.index(START)
j = s.index(END) + len(END)

NEW = '''        # ================= 赢家通吃：四渠道比大小 =================
        # 实测（6 条 query 全渠道打分）：6 条里 5 条正确答案就是分最高的那个渠道。
        # 相对比值（渠道分 >= 风格分 x 0.95）在风格分低时会误开，已被推翻。
        # 现在只用「每渠道绝对下限 + 必须高于风格分」。
        top_style = items[0]["score"]
        floors = {"主体": SUBJECT_FLOOR, "工艺": CRAFT_FLOOR, "材质": MAT_FLOOR}

        if subj:
            dbg = (f"主体: {subj['zh']} {subj['score']:.4f} (下限{SUBJECT_FLOOR}) "
                   f"{'过' if subj['score'] >= SUBJECT_FLOOR else '未过'}\\n" + dbg)
        if craft:
            dbg = (f"工艺: {craft['zh']} {craft['score']:.4f} (下限{CRAFT_FLOOR}) "
                   f"{'过' if craft['score'] >= CRAFT_FLOOR else '未过'}\\n" + dbg)
        if mat:
            dbg = (f"材质: {mat['zh']} {mat['score']:.4f} (下限{MAT_FLOOR}) "
                   f"{'过' if mat['score'] >= MAT_FLOOR else '未过'}\\n" + dbg)

        eligible = []
        for name, obj in (("主体", subj), ("工艺", craft), ("材质", mat)):
            if obj and obj["score"] > top_style and obj["score"] >= floors[name]:
                eligible.append((name, obj["score"], obj))

        winner = max(eligible, key=lambda x: x[1]) if eligible else None
        if winner is None:
            dbg = (f"最终: 风格最高或无人过门槛 -> 不拼内容 (风格 {top_style:.4f})\\n" + dbg)
        else:
            name, sc, obj = winner
            dbg = (f"最终: {name}分最高且过门槛 -> 只拼{name} "
                   f"({sc:.4f} > 风格 {top_style:.4f})\\n" + dbg)
            if name == "主体":
                text = obj["phrase"] + ", " + text
            elif name == "工艺":
                text = text + ", rendered as " + obj["phrase"]
            else:
                text = text + ", " + obj["phrase"]

        # 保留用户原话（中文）
        if 包含原文 and 中文描述 and 中文描述.strip():
            text = 中文描述.strip() + ", " + text'''

s = s[:i] + NEW + s[j:]
ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("已替换为赢家通吃，语法 OK")

# 确认没有残留的旧逻辑关键字
for kw in ("SUBJECT_RATIO", "CRAFT_RATIO", "互斥", "过门槛"):
    n = s.count(kw)
    print(f"  残留 {kw}: {n}")
