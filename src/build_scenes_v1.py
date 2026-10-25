"""
场景索引：题材索引的第五条腿（type = scene）

为什么单独做这一批
------------------
填充率审计发现：中文格式只有 29% 填满，7 个镜头里 4 个触发低置信。

规律是：
    查"东西"（汝窑 / 雪中庭院）  -> 填满，0 占位符
    查"场面"（在卧室相拥 / 在沙滩奔跑）-> 空，6 个占位符

因为四个现有通道是 风格 / 题材 / 工艺 / 材质，
**没有一个是"地点"**。而人写镜头的第一句恰恰是"谁、在哪、做什么"。

设计决定（重要）
----------------
场景**不参与赢家通吃**，它只负责填「场景」那一格：

    type = "scene" 的题材条目命中时 -> 填 scene 槽位
    其它题材条目命中时             -> 仍是 subject

这样加一个维度不会改变现有通道的竞争关系，风险最小。

产物
----
    subjects_v8.jsonl （v7 + 60 条场景）
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# (英文名, 中文名, 输出短语, 关键词)
SCENES = [
    ("Bedroom", "卧室", "a small bedroom, the bed unmade, one window with the curtain half drawn",
     ["卧室", "床", "房间", "被子"]),
    ("Kitchen", "厨房", "a narrow kitchen, pots on the counter, steam on the window",
     ["厨房", "灶台", "锅", "切菜"]),
    ("Bathroom", "浴室", "a tiled bathroom, water still running, the mirror fogged",
     ["浴室", "澡", "瓷砖", "水汽"]),
    ("Study", "书房", "a study lined with books, one desk lamp on, papers spread out",
     ["书房", "书桌", "书架", "台灯"]),
    ("Corridor", "走廊", "a long corridor with doors on one side, light falling in stripes",
     ["走廊", "过道", "门", "长廊"]),
    ("Stairwell", "楼梯间", "a concrete stairwell, the railing worn bright at the hand",
     ["楼梯", "台阶", "扶手", "楼道"]),
    ("Lift", "电梯", "inside a lift, the doors closing, the panel light overhead",
     ["电梯", "升降", "轿厢"]),
    ("Hospital Ward", "病房", "a hospital ward, the bed by the window, curtains half closed",
     ["病房", "医院", "输液", "病床"]),
    ("Classroom", "教室", "an empty classroom, desks in rows, chalk dust in the light",
     ["教室", "课桌", "黑板", "上课"]),
    ("Office", "办公室", "an open-plan office at night, screens still on",
     ["办公室", "工位", "电脑", "加班"]),
    ("Subway Platform", "地铁站台", "a subway platform, the edge strip lit, a train not yet arrived",
     ["地铁", "站台", "轨道", "等车"]),
    ("Convenience Store", "便利店", "a convenience store at night, the shelves bright and the street dark behind",
     ["便利店", "超市", "货架", "夜"]),
    ("Rooftop", "天台", "a rooftop with a low parapet, the city spread out beyond it",
     ["天台", "楼顶", "屋顶", "栏杆"]),
    ("Car Park", "停车场", "an underground car park, columns in rows, strip lights on the ceiling",
     ["停车场", "地下车库", "车位", "柱子"]),
    ("Market", "菜市场", "a covered market, produce on wet tables, the aisle narrow",
     ["菜市场", "集市", "摊子", "菜"]),
    ("Hospital Corridor", "医院走廊", "a hospital corridor, benches along the wall, nobody waiting",
     ["医院走廊", "候诊", "长椅"]),
    ("Waiting Room", "候车室", "a station waiting room, rows of seats, a timetable on the wall",
     ["候车室", "候机", "座椅", "车站"]),
    ("Street Corner", "街角", "a street corner with a shopfront on one side and traffic passing",
     ["街角", "路口", "转角", "街头"]),
    ("Crossing", "十字路口", "a wide crossing, lights changing, people waiting at the kerb",
     ["十字路口", "斑马线", "红绿灯", "过马路"]),
    ("Alley", "巷子", "a narrow alley, walls close on both sides, a drain down the middle",
     ["巷子", "小巷", "弄堂", "窄"]),
    ("Bridge", "桥", "a bridge over water, the railing along one side, the far bank low",
     ["桥", "桥面", "栏杆", "过河"]),
    ("Beach", "沙滩", "an open beach, the sand wet at the waterline, the horizon unbroken",
     ["沙滩", "海边", "海岸", "沙"]),
    ("Riverbank", "河岸", "a river bank, the water flat, reeds at the edge",
     ["河岸", "河边", "堤", "水边"]),
    ("Woods", "树林", "a stand of trees, trunks in rows, the ground covered and quiet",
     ["树林", "林子", "树", "森林"]),
    ("Hillside", "山坡", "a hillside of grass, the slope running up out of frame",
     ["山坡", "坡地", "草坡", "山腰"]),
    ("Field", "田野", "open fields, a path cut through them, the far edge out of sight",
     ["田野", "田", "庄稼", "开阔"]),
    ("Highway", "公路", "a highway running straight, the verge dry, no traffic",
     ["公路", "高速", "马路", "公路边"]),
    ("Cafe", "咖啡馆", "a small cafe, tables by the window, the counter at the back",
     ["咖啡馆", "咖啡厅", "吧台", "座位"]),
    ("Library", "图书馆", "a library reading room, long tables, lamps at intervals",
     ["图书馆", "阅览室", "书架", "安静"]),
    ("Construction Site", "工地", "a construction site, scaffolding on the frame, the ground churned",
     ["工地", "脚手架", "施工", "钢筋"]),
]


def main():
    src = os.path.join(RAW, "subjects_v7.jsonl")
    out = os.path.join(RAW, "subjects_v8.jsonl")
    rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    sample = rows[0]
    k_en = next(k for k in sample if k.endswith("_en"))
    k_zh = next(k for k in sample if k.endswith("_zh"))

    n = len(rows)
    added = []
    for en, zh, phrase, kw in SCENES:
        # 每条场景 2 个描述变体（第二句换个观察角度，避免同质化）
        variants = [phrase]
        parts = phrase.split(", ", 1)
        if len(parts) == 2:
            variants.append(f"{parts[0]}, {parts[1]} — seen from a low angle")
        for v in variants:
            n += 1
            added.append({
                "doc_id": f"s{n:04d}", "kind": "subject",
                k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                "type": "scene",
                "description": v,
                "text_semantic": f"{v}，{zh}，{'、'.join(kw)}",
            })

    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  subjects_v7 -> v8 : {len(rows)} -> {len(rows)+len(added)}"
          f"  (+{len(added)} 条 / {len(SCENES)} 个场景)")
    print(f"  其中 type=scene 的条目：{sum(1 for r in rows+added if r.get('type')=='scene')}")
    print("\n### SCENES_DONE")


if __name__ == "__main__":
    main()
