"""
补现代/科幻词：人形机器人 / 机甲 / 草地 / 星空

为什么
------
实测查询「一个人形机器人坐在草地上看星空」：
    主体找到「星云」0.4018（望远镜里的天体，不是抬头看的夜空）
    机器人、草地、星空 —— 库里一个都没有

库里 133 个实体，绝大多数是古代、博物馆、自然物。**现代与科幻是整片空白。**
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "subjects_v15.jsonl")
OUT = os.path.join(RAW, "subjects_v16.jsonl")

ITEMS = [
    ("Humanoid Robot", "人形机器人", "character_object",
     "a humanoid robot sitting still, seams along the forearms, one lens for an eye",
     ["机器人", "人形机器", "金属关节", "缝线", "镜头眼"],
     "人形机器人：坐着的姿态，小臂上有接缝，一只眼睛是镜头。"),
    ("Mecha", "机甲", "object",
     "a mecha standing idle in the field, panel lines and a cold status light",
     ["机甲", "机器人装甲", "机械", "反应装甲", "面板线"],
     "机甲：立在野外的巨大机身，面板线清晰，有一盏冷光指示灯。"),
    ("Grass Field", "草地", "scene",
     "a low grass field at night, blades catching what little light there is",
     ["草地", "草坪", "青草", "野草", "草甸"],
     "草地：低矮的草，风过时整片动，夜里几乎全暗。"),
    ("Starry Sky", "星空", "scene",
     "a dense star field overhead, the milky way as a pale band, no moon",
     ["星空", "夜空", "银河", "星野", "天上全是星"],
     "星空：头顶密密的星，一条淡白的银河横过，没有月亮。"),
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
    print(f"  subjects_v15 -> v16 : {len(rows)} 行（+{added}）")

    # 光表补一条：星空夜
    lp = os.path.join(RAW, "light_ref.json")
    light = json.load(open(lp, encoding="utf-8"))
    if "星空夜" not in light:
        light["星空夜"] = {
            "zh": "夜空为唯一光源，地面几乎全暗，人和物体只被星光勾出一点轮廓",
            "en": "the night sky as the only source, ground nearly black, "
                  "figures reduced to the faintest edge",
            "kw": ["星空", "夜空", "银河", "星野", "夜里看天"],
        }
        json.dump(light, open(lp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("  光表 +1：星空夜")
    print("\n### ROBOT_KB_DONE")


if __name__ == "__main__":
    main()
