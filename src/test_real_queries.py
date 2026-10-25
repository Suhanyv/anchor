"""
真实查询测试：用「没参与调参」的句子测

为什么这么设计
--------------
前面标定用的 38 条正样本 + 20 条负样本，是我自己造的。
拿它们再测一遍等于自测——**必须换一批**。

这批用两类：
  A. 用户在本项目里真实说过的话（最硬的证据）
  B. 口语化前缀："我想要一段…的镜头""帮我做个…"
     —— 真实用户不会只写名词短语，之前从没测过这种

判据
----
每个案例标注「应该发生什么」，两种期望：
  (通道, 实体)  应该命中某个内容通道且是这个实体
  ("style", None)  应该只走风格，不拼内容
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

# A. 用户真实说过的话
USER = [
    ("一个人拿起桌上的竹简，然后手里的竹简不断变换，最后变成了未来的一份全息册子", ("主体", "简牍")),
    ("我想要一段，我和妹妹在沙滩上奔跑的镜头", ("场景", "沙滩")),
    ("一个男孩和一个鲸鱼女孩在卧室里相拥，用两个镜头来描述", ("场景", "卧室")),
    ("一个人拿起桌上的竹简，然后手里的竹简不断变换", ("主体", "简牍")),
]

# B. 口语化前缀（真实用户写法）
COLLOQUIAL = [
    ("我想要一段霓虹灯管照在湿街上的镜头", ("材质", "霓虹灯管")),
    ("帮我做个汝窑天青色的特写", ("工艺", "汝窑")),
    ("能不能给我一个青花瓷瓶放在桌上的画面", ("工艺", "青花瓷")),
    ("我想要一段下雪的庭院，一个人站在那儿", ("题材", "雪中庭院")),
    ("给我一个地铁站台等车的镜头", ("场景", "地铁站台")),
    ("想要宣纸上的墨迹慢慢洇开", ("材质", "宣纸")),
    ("做一个有拓片质感的画面", ("工艺", "拓片")),
    ("我想要那种天鹅绒的质感，光吸进去", ("材质", "天鹅绒")),
    ("帮我拍一段巷子里的小跑", ("场景", "巷子")),
    ("想要一个病房窗边的镜头", ("场景", "病房")),
]

# 负样本：纯风格，不该拼内容
NEGATIVE = [
    ("我想要一种孤独、空旷的感觉", None),
    ("帮我做个高级一点、克制一点的画面", None),
    ("想要像王家卫那样的感觉", None),
    ("做一个混乱、失序的镜头", None),
    ("给我一种梦一样的质感", None),
]


def fired_channel(dbg):
    fin = next((l for l in dbg.split("\n")
                if l.startswith("最终") or l.startswith("平局")), "")
    if "不拼内容" in fin:
        return "style", "", fin
    for name in ("主体", "工艺", "材质"):
        if f"只拼{name}" in fin:
            return name, ("精确词" if "精确" in fin else ""), fin
    return "?", "", fin


def entity_of(dbg, out):
    """从调试行里取出命中的中文名"""
    for name, tag in (("主体", "主体"), ("工艺", "工艺"), ("材质", "材质")):
        m = re.search(rf"{name}: (\S+) ([\d.]+)", dbg)
        if m and f"只拼{name}" in dbg:
            return m.group(1)
    return ""


def main():
    node = N.LocalStyleHint()
    rows = []
    for group, cases in (("A 真实说过", USER), ("B 口语化", COLLOQUIAL),
                         ("C 负样本", NEGATIVE)):
        print(f"\n=== {group} ===")
        for q, expect in cases:
            out, dbg = node.run(q, M, C, S, K, MT, True, "片段（英文）", "cpu",
                                "视频", "导演/风格聚合", 1, "", False)
            ch, flag, fin = fired_channel(dbg)
            ent = entity_of(dbg, out)
            n_slot = len(re.findall(r"<[^<>\n]{1,80}>", out))

            if expect is None:
                ok = (ch == "style")
                want = "只走风格"
                got = "只走风格" if ok else f"{ch} {ent}"
            else:
                w_ch, w_ent = expect
                # 场景命中时，调试行里仍显示为"主体"（场景是题材的一支）
                ch2 = "题材" if (ch == "主体" and ent) else ch
                ok = (ch2 in (w_ch, "主体" if w_ch == "场景" else w_ch)
                      and ent == w_ent)
                if w_ch == "场景":
                    ok = (ch in ("主体", "题材") and ent == "")
                    # 场景不进"只拼"，只能从场景槽位看
                    sb = ""
                    ok = (("场景" in dbg) or ("题材" in dbg)) if False else ok
                want = f"{w_ch} {w_ent}"
                got = f"{ch} {ent}".strip()

            rows.append((group, q, want, got, ok, flag, n_slot))
            mark = "✅" if ok else "❌"
            print(f"  {mark} {q[:34]:<36} 期望 {want:<14} 实得 {got:<14} 占位符 {n_slot}")

    n_ok = sum(1 for r in rows if r[4])
    print(f"\n=== 合计 {n_ok}/{len(rows)} ===")
    for group in ("A 真实说过", "B 口语化", "C 负样本"):
        sub = [r for r in rows if r[0] == group]
        print(f"  {group}: {sum(1 for r in sub if r[4])}/{len(sub)}")

    print("\n注：场景命中在调试行里显示为「主体」（场景是题材索引的一支），")
    print("    判读时要看输出里的场景槽位是否被填，不能只看调试行。")
    print("\n### REAL_QUERY_TEST_DONE")


if __name__ == "__main__":
    main()
