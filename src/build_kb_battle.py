"""
加一批"打斗"知识：铠甲细部 / 战场器物 / 受力材质 / 打击感技法

为什么加
--------
骑士镜的原样输出里，风格和道具都有了，**动作和受力全是空槽**。
库里没有"顿帧""反作用"这类技法，也没有"札甲""剑柄"这类细部，
所以模型只能写"一个骑士和一群人交战"这种笼统句子。

三批
----
题材   铠甲细部 + 战场器物（札甲 / 护腕 / 剑首 / 碎盾 / 断矛 / 军旗…）
材质   受力可见的材质（锻打铁 / 旧皮革 / 粗麻 / 铜绿）
工艺   打击感技法（顿帧 / 速度斜坡 / 接触特写 / 反作用）  ← 这一类此前完全空白

验证
----
按老规矩两组数：新条目命中 + 老条目对照不变。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

# ---------------- 题材：铠甲细部与战场器物 ----------------
SUBJ = [
    ("Lamellar Armour", "札甲",
     "a lamellar cuirass of laced iron plates, each scale tied with leather cord",
     ["札甲", "甲片", "铠甲", "铁甲", "甲胄"],
     "札甲：用皮绳把一片片铁甲叶编起来的甲，贴身、有横向的层叠线，"
     "动起来甲片互相摩擦。"),
    ("Scale Armour", "鳞甲",
     "scale armour, overlapping steel scales like fish skin catching the light",
     ["鳞甲", "鱼鳞甲", "甲片", "铁甲"],
     "鳞甲：甲片像鱼鳞一样层层压叠，光在弧面上滚，比札甲更细密。"),
    ("Vambrace", "护腕",
     "a steel vambrace strapped over the forearm, two buckle straps visible",
     ["护腕", "护臂", "臂甲", "手腕"],
     "护腕：包住小臂的铁护具，两道皮带扣着，抬手时能看见边缘。"),
    ("Pauldron", "护肩",
     "a rounded steel pauldron with a rolled edge, sitting over the shoulder",
     ["护肩", "肩甲", "披膊"],
     "护肩：盖在肩上的圆铁片，边缘卷起，抬臂时会翘起来一道缝。"),
    ("Cloak", "披风",
     "a heavy wool cloak pinned at one shoulder, the hem dragging in the dust",
     ["披风", "斗篷", "披挂"],
     "披风：厚重毛料，一边用扣针别在肩头，下摆在土里拖。"),
    ("Sword Hilt", "剑柄",
     "a worn leather-wrapped sword hilt, the wrap dark where the hand sits",
     ["剑柄", "握柄", "柄"],
     "剑柄：缠着旧皮革，手握的那一段颜色更深。"),
    ("Pommel", "剑首",
     "a disc pommel at the end of the grip, its face polished by the palm",
     ["剑首", "配重", "柄头"],
     "剑首：剑柄末端那块圆铁，掌心磨得发亮。"),
    ("Shattered Shield", "碎盾",
     "a shield split across its face, splinters still standing at the break",
     ["碎盾", "破盾", "盾牌裂", "盾"],
     "碎盾：盾面从中裂开，断口的木刺还立着。"),
    ("Broken Spear", "断矛",
     "a spear broken mid-shaft, the splintered end angled into the ground",
     ["断矛", "断枪", "矛", "枪杆"],
     "断矛：杆子断了，断头斜插在地上。"),
    ("Battle Banner", "军旗",
     "a tall battle banner on a pole, cloth snapping sideways in the wind",
     ["军旗", "旗", "旌旗", "旗杆"],
     "军旗：长杆上的布旗，被风横着扯起来。"),
]

# ---------------- 材质：受力可见 ----------------
MAT = [
    ("Forged Iron", "锻打铁",
     "forged iron with hammer dimples across the surface, black scale in the hollows",
     ["锻打铁", "锻铁", "铁", "锤痕"],
     "锻打铁：表面全是锤子砸出的浅坑，凹处有黑色氧化皮。"),
    ("Worn Leather", "旧皮革",
     "worn leather gone soft and dark at the edges, cracked along the creases",
     ["皮革", "旧皮", "皮带", "牛皮"],
     "旧皮革：用久了发软，边缘发黑，折痕处开裂。"),
    ("Coarse Linen", "粗麻",
     "coarse linen with a visible slub weave, sweat-stained at the collar",
     ["粗麻", "麻布", "亚麻", "布料"],
     "粗麻：经纬粗得看得出来，领口有汗渍。"),
    ("Verdigris Bronze", "铜绿",
     "bronze gone verdigris green in the recesses, worn bright on the high points",
     ["铜绿", "青铜", "铜锈", "铜"],
     "铜绿：凹处生绿锈，凸起处被磨得发亮。"),
]

# ---------------- 工艺：打击感技法（此前完全空白）----------------
CRAFT = [
    ("Freeze on Impact", "顿帧",
     "the frame holds dead still for two frames at the moment of contact, then the recoil",
     ["顿帧", "停格", "定格", "接触停顿", "打击感", "力道", "重量"],
     "顿帧：接触那一瞬间画面停住两帧，再放出去。打击感靠的就是这一停。"),
    ("Speed Ramp", "速度斜坡",
     "the swing ramps from slow to fast and snaps to near-stop as it lands",
     ["速度斜坡", "变速", "快慢变速", "抽帧"],
     "速度斜坡：挥出去时由慢到快，落点前后骤然减速。"),
    ("Impact Insert", "接触特写",
     "an insert right at the contact point, metal and dust filling the frame",
     ["接触特写", "打击特写", "接触点", "火星特写"],
     "接触特写：切到接触点的近景，金属和尘土占满画面。"),
    ("Reaction Beat", "反作用",
     "the struck body answers: the foot slides back, dust jumps, the shield gives",
     ["反作用", "受力", "退步", "后滑"],
     "反作用：被打的一方必须有反应——脚后滑、尘土跳起、盾牌凹陷。没有反作用就没有力。"),
]


def rows_of(data, kind):
    """把上面三张表转成索引行。doc_id 前缀：s/c/m。"""
    out = []
    if kind == "subject":
        for i, (en, zh, phrase, kw, desc) in enumerate(data, 1):
            out.append({
                "doc_id": f"b{i:03d}", "kind": "subject",
                "subject_en": en, "subject_zh": zh, "phrase": phrase,
                "kw_zh": kw, "description": desc,
                "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
                "type": "object",
            })
    elif kind == "craft":
        for i, (en, zh, phrase, kw, desc) in enumerate(data, 1):
            out.append({
                "doc_id": f"bc{i:03d}", "kind": "craft",
                "craft_en": en, "craft_zh": zh, "phrase": phrase,
                "kw_zh": kw, "description": desc,
                "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
            })
    else:
        for i, (en, zh, phrase, kw, desc) in enumerate(data, 1):
            out.append({
                "doc_id": f"bm{i:03d}", "kind": "material",
                "mat_en": en, "mat_zh": zh, "phrase": phrase,
                "kw_zh": kw, "description": desc,
                "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
            })
    return out


def append(src, dst, new_rows):
    rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    have = {(r.get("subject_zh") or r.get("craft_zh") or r.get("mat_zh")) for r in rows}
    added = [r for r in new_rows
             if (r.get("subject_zh") or r.get("craft_zh") or r.get("mat_zh")) not in have]
    with open(dst, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows), len(rows) + len(added), len(added)


if __name__ == "__main__":
    s0, s1, sa = append(os.path.join(RAW, "subjects_v13.jsonl"),
                        os.path.join(RAW, "subjects_v14.jsonl"), rows_of(SUBJ, "subject"))
    c0, c1, ca = append(os.path.join(RAW, "crafts_v6.jsonl"),
                        os.path.join(RAW, "crafts_v7.jsonl"), rows_of(CRAFT, "craft"))
    m0, m1, ma = append(os.path.join(RAW, "materials_v11.jsonl"),
                        os.path.join(RAW, "materials_v12.jsonl"), rows_of(MAT, "material"))
    print(f"  题材 {s0} -> {s1}  (+{sa})")
    print(f"  工艺 {c0} -> {c1}  (+{ca})")
    print(f"  材质 {m0} -> {m1}  (+{ma})")
    print("\n### BATTLE_KB_DONE")
