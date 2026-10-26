"""
提示词填充率审计：库里的知识到底能填满多少格？

为什么测这个
------------
"库够厚了吗"这个问题，不能靠感觉回答。可测的代理指标是：

    一个格式的模板里有 N 个槽位，其中多少个被库真实填上，多少个还留着 <占位符>

填充率高 = 用户只需要改一点就能用
填充率低 = 库帮不上忙，用户得自己写

这比"命中率"更接近真实体验：命中率只说明检索对不对，
填充率说明**检索到的东西能不能变成可用的提示词**。

做法
----
对一组真实镜头描述 x 全部活格式跑一遍，数 <...> 占位符。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v8.jsonl")
K = os.path.join(ROOT, "data/raw/crafts_v6.jsonl")
MT = os.path.join(ROOT, "data/raw/materials_v8.jsonl")

CASES = [
    ("一个男孩和一个鲸鱼女孩在卧室里相拥", "视频"),
    ("一个人拿起桌上的竹简，竹简慢慢变成全息册子", "视频"),
    ("我和妹妹在沙滩上奔跑", "视频"),
    ("霓虹夜色，一个人走过湿漉漉的街", "视频"),
    ("下雪的庭院里只有一行脚印", "图片"),
    ("汝窑天青色，满身细开片", "图片"),
    ("雾大到看不见对岸，一个人站在渡口", "视频"),
]

# 跳过存档格式
SKIP = ("Sora 2",)


def count_slots(text):
    """返回 (槽位总数, 已填数)。占位符形如 <...>"""
    slots = re.findall(r"<[^<>\n]{1,80}>", text)
    return len(slots)


# --- 统一路径：以节点默认值为准，避免脚本与部署漂移 ---
try:
    from paths import DEFAULTS as _PATHS
    M, C = _PATHS["model"], _PATHS["corpus"]
    S, K, MT = _PATHS["subjects"], _PATHS["crafts"], _PATHS["materials"]
except Exception:
    pass


def main():
    node = N.LocalStyleHint()
    fmts = [f for f in node.INPUT_TYPES()["required"]["输出格式"][0]
            if not any(s in f for s in SKIP)]

    # 每个格式的"模板槽位数"用一次空白查询估出来（占位符最多的那次即模板骨架）
    print("=== 填充率审计 ===\n")
    print(f"格式 {len(fmts)} 种 x 镜头 {len(CASES)} 个\n")

    rows = []
    for fmt in fmts:
        per_case = []
        for q, dom in CASES:
            try:
                text, _ = node.run(q, M, C, S, K, MT, True, fmt, "cpu", dom,
                                   "导演/风格聚合", 1, "", False)
            except Exception as e:  # noqa: BLE001
                per_case.append((q, -1, 0))
                continue
            # 该格式的模板骨架 = 各案例里占位符最多的一次
            per_case.append((q, count_slots(text), len(text)))
        max_slot = max((x[1] for x in per_case), default=0)
        # 实填率 = 1 - 该案例占位符数 / 模板槽位数（按案例平均）
        filled = []
        for _, slots, _ in per_case:
            if slots < 0 or max_slot == 0:
                continue
            filled.append(1.0 - slots / max_slot)
        avg = sum(filled) / len(filled) if filled else 0.0
        rows.append((fmt, max_slot, avg))

    rows.sort(key=lambda x: -x[2])
    print(f"{'格式':<34} {'模板槽位':>8} {'平均填充率':>10}")
    print("-" * 56)
    for fmt, slots, avg in rows:
        bar = "█" * int(round(avg * 20))
        print(f"{fmt:<34} {slots:>8} {avg:>9.0%}  {bar}")

    print("\n判读：")
    print("  填充率高 = 库里能填的格子多，用户改几处就能用")
    print("  填充率低 = 模板里主要靠 <占位符>，库帮不上，用户得自己写")
    print("  槽位为 0 = 该格式没有占位符（输出全是库给的内容）")

    # 逐案例明细（挑一个中文格式看）
    probe = "即梦 Seedance 2.5（中文）"
    if probe in fmts:
        print(f"\n=== 逐案例明细：{probe} ===")
        for q, dom in CASES:
            text, dbg = node.run(q, M, C, S, K, MT, True, probe, "cpu", dom,
                                 "导演/风格聚合", 1, "", False)
            n_slot = count_slots(text)
            warn = "⚠️ 低置信" if any(l.startswith("⚠️") for l in dbg.split("\n")) else ""
            print(f"  {q[:30]:<32} 占位符 {n_slot}  {warn}")

    print("\n### FILL_AUDIT_DONE")


if __name__ == "__main__":
    main()
