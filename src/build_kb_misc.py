"""
补四类空白：家具构件 / 交通工具 / 城市设施 / 人物服装（共 24 项）

它们填的是不同格子
------------------
    场景槽位  窗台 门槛 台阶 阳台 栏杆 长椅 桌面 树杈 天桥 公交站
    主体槽位  自行车 列车 飞机 船 摩托车 公交车
              红绿灯 自动售货机 路灯
              医生 工人 学生 老人 新娘 军人

人物为什么不写"性格"
--------------------
提示词里"善良的老人"没有用，"手背有可见的筋、头发稀疏"才有用。
所以人物也按**可被拍到的东西**写：服装、道具、体态、疲态。

军人那条刻意不写武器——Veo 的审核会挡，而且不需要。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
RAW = os.path.join(ROOT, "data", "raw")

# (英文名, 中文名, 输出短语, 关键词, 类型, [描述变体])
ENTRIES = [
    # ---------- A 家具与构件（场景）----------
    ("Window Sill", "窗台", "a window sill, paint worn where hands rest, light lying across it",
     ["窗台", "窗口", "窗边", "窗沿"], "scene",
     ["a windowsill, the paint worn pale where hands have rested",
      "light lying flat across a sill, the glass above it cold",
      "a sill with a dead plant and a glass of water on it"]),
    ("Threshold", "门槛", "a doorway threshold, the stone worn into a shallow curve",
     ["门槛", "门口", "门道"], "scene",
     ["a stone threshold worn into a shallow curve by feet",
      "the light changing as a figure crosses the threshold",
      "the strip of floor on one side of the door, darker than the other"]),
    ("Steps", "台阶", "a flight of steps, edges rounded by use, each tread slightly hollowed",
     ["台阶", "楼梯", "石阶", "阶梯"], "scene",
     ["steps with every edge rounded by use, the treads slightly hollowed",
      "a long flight seen from below, the top out of frame",
      "rain standing in the corners where the treads meet the risers"]),
    ("Balcony", "阳台", "a balcony with a railing, the street visible between the bars",
     ["阳台", "露台", "栏杆"], "scene",
     ["a balcony railing, the street below cut into strips by the bars",
      "washing hung on a balcony, moving with the wind",
      "a balcony at night, one light on inside behind it"]),
    ("Railing", "栏杆", "a metal railing, paint chipped, the top rail polished by hands",
     ["栏杆", "扶手", "护栏"], "scene",
     ["a metal railing, the top rail polished where hands have held it",
      "paint lifting from a railing in flakes, rust beneath",
      "a railing seen against a bright background, reading as a black line"]),
    ("Bench", "长椅", "a bench with wooden slats worn pale, one armrest missing",
     ["长椅", "凳子", "公园椅"], "scene",
     ["a bench, the slats worn pale in the middle where people sit",
      "a bench with one armrest gone and the paint stripped from it",
      "an empty bench under a light, the seat wet"]),
    ("Tabletop", "桌面", "a tabletop, scratched and ringed, one object set on it",
     ["桌面", "桌子", "桌上", "台面"], "scene",
     ["a tabletop with rings from wet glasses and a long scratch across it",
      "one object set on an otherwise empty table, the rest out of frame",
      "the edge of a table, the surface going dull where arms rest"]),
    ("Branch", "树杈", "a branch, bark rough in one direction and smooth in the other",
     ["树枝", "树杈", "树干"], "scene",
     ["a branch, the bark rough one way and smooth the other",
      "a fork in a branch where two limbs separate",
      "leaves moving while the branch itself stays still"]),
    ("Footbridge", "天桥", "a pedestrian footbridge over a road, railings on both sides",
     ["天桥", "过街桥", "人行桥"], "scene",
     ["a footbridge over a road, railings on both sides and traffic below",
      "the shadow of a footbridge lying across the lanes",
      "someone crossing a footbridge, small against the structure"]),
    ("Bus Stop", "公交站", "a bus stop with a shelter and a bench, the timetable behind glass",
     ["公交站", "车站", "候车亭"], "scene",
     ["a bus stop shelter, the timetable behind scratched plastic",
      "the bench at a bus stop, wet, nobody waiting",
      "a bus arriving, the shelter lighting up as it does"]),

    # ---------- B 交通工具（主体）----------
    ("Bicycle", "自行车", "a bicycle leaning on its stand, the chain dry, spokes catching light",
     ["自行车", "单车", "脚踏车", "车轮"], "object",
     ["a bicycle leaning on its stand, spokes turning slowly to a stop",
      "a bicycle ridden past, the rider's coat lifting",
      "a bicycle lying on its side, one wheel still turning"]),
    ("Train", "列车", "a train at a platform, doors open, the interior lit",
     ["列车", "火车", "地铁", "车厢"], "object",
     ["a train at a platform, doors open, the interior brighter than outside",
      "a train passing without stopping, the windows running together",
      "the front of a train entering a tunnel, light collapsing"]),
    ("Airplane", "飞机", "an aircraft on the ground, engines turning slowly",
     ["飞机", "客机", "航班"], "object",
     ["an aircraft on the apron, engines turning slowly, heat off the tarmac",
      "a plane lifting, the gear still down",
      "a plane at altitude, the wing flexing very slightly"]),
    ("Boat", "船", "a small boat on flat water, the hull dark at the waterline",
     ["船", "小艇", "渔船", "渡船"], "object",
     ["a small boat on flat water, the hull dark at the waterline",
      "a boat moving slowly, wake widening behind it",
      "a boat tied up, rope slack, the hull knocking against the dock"]),
    ("Motorcycle", "摩托车", "a motorcycle parked, engine ticking as it cools",
     ["摩托车", "机车", "摩托"], "object",
     ["a motorcycle parked on a stand, the engine ticking as it cools",
      "a motorcycle ridden past, the rider leaning into the turn",
      "chrome on a motorcycle catching one line of light"]),
    ("Bus", "公交车", "a city bus, the interior lit, people standing in the aisle",
     ["公交车", "巴士", "大巴"], "object",
     ["a city bus with the interior lit, silhouettes in the windows",
      "a bus pulling away from a stop, exhaust in cold air",
      "the inside of a bus, straps swinging together with the motion"]),

    # ---------- C 城市设施 ----------
    ("Traffic Light", "红绿灯", "a traffic light changing, the housing hooded against glare",
     ["红绿灯", "信号灯", "路口灯"], "object",
     ["a traffic light changing, the lit lens brighter than everything around it",
      "the housing hooded so the colour only shows under it",
      "a reflection of a traffic light stretched on wet road"]),
    ("Vending Machine", "自动售货机", "a vending machine lit from within, the rows of products bright",
     ["售货机", "自动贩卖机", "饮料机"], "object",
     ["a vending machine lit from inside, the products the brightest thing in frame",
      "the glow of a vending machine on wet ground at night",
      "a machine humming, one row empty"]),
    ("Street Lamp", "路灯", "a street lamp with a hard cone of light and nothing outside it",
     ["路灯", "街灯", "灯柱"], "object",
     ["a street lamp throwing a hard cone, the rest of the frame black",
      "lamps receding in a line, each one dimmer than the last",
      "insects held in the light under a lamp"]),

    # ---------- D 人物与服装 ----------
    ("Doctor", "医生", "a doctor in a white coat, a stethoscope, the coat creased at the elbow",
     ["医生", "白大褂", "护士", "医"], "object",
     ["a doctor in a white coat, creased at the elbows, a stethoscope around the neck",
      "a doctor's hands, the nails short, one wrist bare",
      "a doctor sitting down heavily, the coat open over scrubs"]),
    ("Worker", "工人", "a worker in a hard hat and dusty overalls, boots grey with dust",
     ["工人", "工地", "安全帽", "劳作"], "object",
     ["a worker in a hard hat, dust on the shoulders and grey on the boots",
      "a worker resting, elbows on knees, helmet pushed back",
      "gloves off, hands pale where they were covered"]),
    ("Student", "学生", "a student with a backpack, the strap pulling one shoulder down",
     ["学生", "校服", "书包", "上学"], "object",
     ["a student with a backpack, the strap pulling one shoulder lower",
      "a student at a desk, one leg jittering under it",
      "a school uniform worn loose, the collar turned"]),
    ("Elder", "老人", "an old person, veins visible on the back of the hands, hair thin",
     ["老人", "老年", "白发", "皱纹"], "object",
     ["old hands, veins standing up on the back, the skin thin and loose",
      "an old face, the hair thin and lifted by a breeze",
      "an older person standing slowly, one hand finding the table"]),
    ("Bride", "新娘", "a bride in white, the veil lifted and held, the dress heavy at the hem",
     ["新娘", "婚纱", "婚礼", "白纱"], "object",
     ["a bride in white, the veil lifted off the face and held",
      "the hem of a wedding dress darkening where it touched the ground",
      "a bride standing still while everyone else moves"]),
    ("Soldier", "军人", "a soldier in uniform, helmet on, dust on the boots, no weapon in frame",
     ["军人", "士兵", "军装", "列队"], "object",
     ["a soldier in uniform, dust on the boots, hands empty",
      "a soldier standing at rest, the helmet pushed back",
      "a uniform jacket hung on a chair, boots below it"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    src = os.path.join(RAW, "subjects_v10.jsonl")
    out = os.path.join(RAW, "subjects_v11.jsonl")
    rows = load(src)
    sample = rows[0]
    k_en = next(k for k in sample if k.endswith("_en"))
    k_zh = next(k for k in sample if k.endswith("_zh"))

    n = len(rows)
    added = []
    for en, zh, phrase, kw, typ, variants in ENTRIES:
        for v in variants:
            n += 1
            added.append({"doc_id": f"s{n:04d}", "kind": "subject",
                          k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                          "type": typ, "description": v,
                          "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"})

    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    scenes = sum(1 for r in added if r["type"] == "scene")
    print(f"  subjects_v10 -> v11 : {len(rows)} -> {len(rows)+len(added)}")
    print(f"    +{len(added)} 条 / {len(ENTRIES)} 项（场景 {scenes} 条 / 主体 {len(added)-scenes} 条）")
    print("\n### KB_MISC_DONE")


if __name__ == "__main__":
    main()
