"""
真实查询测试 v2：判读逻辑重写

上一版的错
----------
判读代码写得一团糟，出现了「期望 主体 简牍 / 实得 主体 简牍」还标 ❌ 的情况。
根因是我把「通道名」和「场景/物件」混在一个比较里，还写了一堆自我覆盖的分支。
**测试脚本本身出错，比模型出错更危险——它会把对的判成错的。**

这一版
------
判据只有一个：**命中的实体名对不对**，外加一条「场景/物件」的类型对不对。
类型从调试行读取（节点已在主体行标了 [场景] / [物件]）。

期望写成：
    ("物件", "简牍")   应命中题材里的物件条目
    ("场景", "沙滩")   应命中场景条目
    ("工艺", "汝窑")
    ("材质", "霓虹灯管")
    ("风格", None)     应只走风格
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v9.jsonl")
K = os.path.join(ROOT, "data/raw/crafts_v6.jsonl")
MT = os.path.join(ROOT, "data/raw/materials_v9.jsonl")

CASES = [
    # A 用户在本项目里真实说过的话
    ("一个人拿起桌上的竹简，然后手里的竹简不断变换，最后变成了未来的一份全息册子",
     ("物件", "简牍")),
    ("我想要一段，我和妹妹在沙滩上奔跑的镜头", ("场景", "沙滩")),
    ("一个男孩和一个鲸鱼女孩在卧室里相拥，用两个镜头来描述", ("场景", "卧室")),
    ("我想要在太空中，拍摄太阳的黑子", ("风格", None)),

    # B 口语化（真实用户写法）
    ("我想要一段霓虹灯管照在湿街上的镜头", ("材质", "霓虹灯管")),
    ("帮我做个汝窑天青色的特写", ("工艺", "汝窑")),
    ("能不能给我一个青花瓷瓶放在桌上的画面", ("工艺", "青花瓷")),
    ("给我一个地铁站台等车的镜头", ("场景", "地铁站台")),
    ("想要宣纸上的墨迹慢慢洇开", ("材质", "宣纸")),
    ("做一个有拓片质感的画面", ("工艺", "拓片")),
    ("我想要那种天鹅绒的质感，光吸进去", ("材质", "天鹅绒")),
    ("帮我拍一段巷子里的小跑", ("场景", "巷子")),
    ("想要一个病房窗边的镜头", ("场景", "病房")),

    # C 负样本：纯风格，不该拼内容
    ("我想要一种孤独、空旷的感觉", ("风格", None)),
    ("帮我做个高级一点、克制一点的画面", ("风格", None)),
    ("想要像王家卫那样的感觉", ("风格", None)),
    ("做一个混乱、失序的镜头", ("风格", None)),
]


def parse(dbg):
    """从调试行读出：命中了什么（名字 + 类型），还是只走风格"""
    # 各通道的名字
    names = {}
    m = re.search(r"主体\[(\S+?)\]: (\S+) ([\d.]+)", dbg)
    if m:
        names["subj"] = (m.group(2), m.group(1))
    m = re.search(r"工艺: (\S+) ([\d.]+)", dbg)
    if m:
        names["craft"] = (m.group(1), "工艺")
    m = re.search(r"材质: (\S+) ([\d.]+)", dbg)
    if m:
        names["mat"] = (m.group(1), "材质")

    # 最终谁赢
    if "不拼内容" in dbg:
        return "风格", None
    if "只拼主体" in dbg and "subj" in names:
        name, typ = names["subj"]
        return typ, name
    if "只拼工艺" in dbg and "craft" in names:
        return "工艺", names["craft"][0]
    if "只拼材质" in dbg and "mat" in names:
        return "材质", names["mat"][0]
    return "?", None


def main():
    node = N.LocalStyleHint()
    rows = []
    for q, (want_kind, want_name) in CASES:
        out, dbg = node.run(q, M, C, S, K, MT, True, "文生视频",
                            "片段（英文）", "cpu", "视频", "导演/风格聚合",
                            1, "", False)
        got_kind, got_name = parse(dbg)
        ok = (got_kind == want_kind and got_name == want_name)
        rows.append((ok, q, want_kind, want_name, got_kind, got_name))
        mark = "✅" if ok else "❌"
        want = f"{want_kind} {want_name or ''}".strip()
        got = f"{got_kind} {got_name or ''}".strip()
        print(f"  {mark} {q[:32]:<34} 期望 {want:<14} 实得 {got}")

    n_ok = sum(1 for r in rows if r[0])
    print(f"\n=== {n_ok}/{len(rows)} ===")

    fails = [r for r in rows if not r[0]]
    if fails:
        print("失败项：")
        for _, q, wk, wn, gk, gn in fails:
            print(f"  期望 {wk} {wn or ''} / 实得 {gk} {gn or ''}  <- {q[:30]}")

    # 按类别汇总
    import collections
    cats = collections.Counter()
    for ok, _, wk, wn, _, _ in rows:
        cats[wk] += 1
    print("\n按期望类别：")
    for k, n in cats.items():
        sub = [r for r in rows if r[2] == k]
        print(f"  {k:<6} {sum(1 for r in sub if r[0])}/{len(sub)}")

    print("\n### REAL_QUERIES_V2_DONE")


if __name__ == "__main__":
    main()
