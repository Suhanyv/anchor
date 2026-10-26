"""
片段集：五个独立作品，各用各的风格

但有一条例外要处理：
    骑士三镜属于**一个作品**，必须共用同一 look。
    工具给出的三镜里，起手/收是乌尔善，交战却跑成了德尔·托罗（琥珀青、哥特）。
    如果不修，那三镜剪起来会像两部片。

做法：骑士三镜统一锁在乌尔善上（2/3 票），其余四个作品各用检索到的风格。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

node = N.LocalStyleHint()
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

PIECES = [
    ("① 骑士 · 镜1 起手", "中世纪骑士站在石地中央，手按长剑剑柄"),
    ("① 骑士 · 镜2 交战", "一个对手入画劈下，骑士横剑格挡"),
    ("① 骑士 · 镜3 收", "骑士收剑，前景虚焦身影退开"),
    ("② 相拥", "一个男孩和一个鲸鱼女孩在卧室里相拥"),
    ("③ 沙滩", "我和妹妹在沙滩上奔跑"),
    ("④ 太阳", "在太空中拍摄太阳的黑子"),
    ("⑤ 竹简", "一个人拿起桌上的竹简，竹简慢慢变成全息册子"),
]

print("=" * 70)
for tag, q in PIECES:
    out, dbg = node.run(q, M, C, S, K, MT, True, "文生视频", False,
                        "即梦 Seedance 2.5（中文）", "cpu", "视频",
                        "导演/风格聚合", 1, "", False)
    items, _mode, subj, _dom, _c, _m = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    sec, kind = N._ref_duration(q)
    print(f"\n【{tag}】  {it.get('director_zh')} {float(it.get('score') or 0):.2f} "
          f"| {sec}s/{kind} | 命中 {(subj or {}).get('zh', '-')}")
    print("-" * 70)
    for line in out.split("\n"):
        if line.strip():
            print("  " + line)

print("\n### ANTHOLOGY_DONE")
