"""
补怪兽片的基本件：怪兽 / 记者 / 新闻现场

为什么
------
实测查询「怪兽还有三小时空降地球，各家媒体争先报道」：
    风格 德尔·托罗 0.4166  ← 这个对了（冷工业、哥特）
    主体 地球 0.3414        ← 错了：地球是"空降"的目的地，不是主角

库里没有怪兽、没有记者、没有摄像机。所以它只能抓住"地球"这个最好抓的词，
把一场地面上的灾难片写成了太空里的行星镜头。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "subjects_v16.jsonl")
OUT = os.path.join(RAW, "subjects_v17.jsonl")

ITEMS = [
    ("Kaiju", "怪兽", "object",
     "a colossal creature standing between buildings, its hide wet, "
     "dust falling off its back",
     ["怪兽", "巨兽", "怪物", "巨物", "巨影"],
     "怪兽：站在楼群之间的巨大躯体，表皮湿的，背上有尘土落下来。"),
    ("Reporter", "记者", "character",
     "a reporter holding a microphone, hair blown across the face, "
     "camera light on them",
     ["记者", "主播", "主持人", "出镜", "现场报道"],
     "记者：举着话筒出镜，头发被风吹乱，摄影灯打在脸上。"),
    ("Press Crowd", "媒体人群", "scene",
     "a pack of cameras and tripods packed together, lenses pointed one way",
     ["媒体", "记者群", "长枪短炮", "摄像机", "直播"],
     "媒体人群：一堆摄像机和三脚架挤在一起，镜头全对着一个方向。"),
]


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    have = {r.get("subject_zh") for r in rows}
    added = 0
    for en, zh, typ, phrase, kw, desc in ITEMS:
        if zh in have:
            print(f"  跳过（已存在）{zh}")
            continue
        rows.append({
            "doc_id": f"s{len(rows)+1:04d}",
            "kind": "subject",
            "subject_en": en,
            "subject_zh": zh,
            "phrase": phrase,
            "kw_zh": kw,
            "description": desc,
            "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
            "type": typ,
        })
        added += 1
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  subjects_v16 -> v17 : {len(rows)} 行（+{added}）")
    print("\n### MONSTER_KB_DONE")


if __name__ == "__main__":
    main()
