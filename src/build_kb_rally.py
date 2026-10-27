"""
补赛车与赛道：拉力赛车 / 赛车手 / 沙地赛道

为什么
------
实测「两辆拉力赛车在沙地赛场上竞速」：
    主体 沙漠商队 0.3697（未过门槛）
库里车辆有 自行车/列车/飞机/船/摩托车/公交车 —— **没有汽车**。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "subjects_v17.jsonl")
OUT = os.path.join(RAW, "subjects_v18.jsonl")

ITEMS = [
    ("Rally Car", "拉力赛车", "object",
     "a rally car sliding sideways on loose sand, rooster tail of dust "
     "behind it, mud flaps, roof lights",
     ["赛车", "拉力赛车", "赛车手", "车轮", "尾尘", "漂移"],
     "拉力赛车：在松沙上侧滑，车尾甩起一道尘，挡泥板和后视镜上全是土。"),
    ("Rally Driver", "赛车手", "character",
     "a driver in a helmet and harness, hands locked on the wheel, "
     "eyes straight ahead",
     ["车手", "赛车手", "头盔", "安全帽", "方向盘"],
     "赛车手：戴头盔、绑着安全带，两手死握方向盘，眼睛只看前面。"),
    ("Desert Track", "沙地赛道", "scene",
     "a sand track cut across open desert, tyre ruts, marker flags, "
     "dust hanging in the air",
     ["赛道", "沙地赛场", "沙地", "沙漠赛道", "赛段", "尘土"],
     "沙地赛道：一条车辙压出来的沙路，边上有标志旗，空中的土还没落。"),
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
    print(f"  subjects_v17 -> v18 : {len(rows)} 行（+{added}）")
    print("\n### RALLY_KB_DONE")


if __name__ == "__main__":
    main()
