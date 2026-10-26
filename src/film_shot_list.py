"""
镜位表：把已有的五个镜头跑一遍，出一张可执行的表

只跑工具，不写内容。输出每镜的：
    风格（检索到的实体）  时长（按运动幅度）  主体/场景（命中的索引项）  置信度
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

SHOTS = [
    ("骑士·起手", "一个骑士手握一把长剑，和一群人交战，想要三个镜头"),
    ("骑士·交战", "一个对手入画劈下，骑士横剑格挡"),
    ("骑士·收", "骑士收剑，前景虚焦身影退开"),
    ("相拥", "一个男孩和一个鲸鱼女孩在卧室里相拥"),
    ("沙滩", "我和妹妹在沙滩上奔跑"),
    ("太阳", "在太空中拍摄太阳的黑子"),
    ("竹简", "一个人拿起桌上的竹简，竹简慢慢变成全息册子"),
]


def one(q):
    items, mode, subj, dom, craft, mat = N._rank(
        q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    sec, kind = N._ref_duration(q)
    return {
        "style": it.get("director_zh") or it.get("director"),
        "score": float(it.get("score") or 0),
        "kw": "、".join((it.get("kw_zh") or [])[:4]),
        "subj": (subj or {}).get("zh", ""),
        "subj_type": (subj or {}).get("type", ""),
        "sec": sec, "kind": kind,
        "ar": (it.get("params") or {}).get("ar", "21:9"),
    }


print(f"{'镜位':<10}{'风格':<9}{'分':<6}{'时长':<10}{'命中':<8}{'类型'}")
print("-" * 62)
rows = []
for tag, q in SHOTS:
    r = one(q)
    rows.append((tag, q, r))
    print(f"{tag:<10}{r['style'][:8]:<9}{r['score']:<6.2f}"
          f"{str(r['sec']) + 's/' + r['kind']:<10}"
          f"{(r['subj'] or '-')[:7]:<8}{r['subj_type'] or '-'}")

print()
print("=== 每镜关键词 ===")
for tag, q, r in rows:
    print(f"  {tag:<10} {r['kw']}")

print()
print("=== 共用块候选（如果整部片要统一 look）===")
from collections import Counter
c = Counter((r["style"], r["kw"]) for _, _, r in rows)
for (st, kw), n in c.most_common():
    print(f"  {n} 镜  {st}  {kw}")

print("\n### SHOT_LIST_DONE")
