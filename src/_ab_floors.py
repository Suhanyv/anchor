"""
门槛 A/B：现值 vs 标定建议值，用同一批用例比命中

为什么要 A/B：标定表里正负样本是**重叠**的
    subject  正最低 0.397 < 负最高 0.498
    material 正最低 0.522 = 负最高 0.522
说明任何单一阈值都分不干净（C1 那条教训）。所以不能只看建议值就改，
要用真实用例看改了之后是涨还是跌。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

RAW = r"F:\llm\data\raw"
M = r"F:\llm\models\e5-director-c27"
C = f"{RAW}/corpus_v26.jsonl"
S = f"{RAW}/subjects_v20.jsonl"
K = f"{RAW}/crafts_v9.jsonl"
MT = f"{RAW}/materials_v12.jsonl"

# (查询, 期望实体, 渠道)
CASES = [
    ("雪天，两个武士在长满狗尾巴草山上对决", "武士", "subjects"),
    ("一个剑客站在雪里", "剑客", "subjects"),
    ("浪人戴着斗笠", "浪人", "subjects"),
    ("武将骑着马，后面有旗", "武将", "subjects"),
    ("侠客独自面对一群人", "侠客", "subjects"),
    ("一个人形机器人坐在草地上看星空", "人形机器人", "subjects"),
    ("雨里，一个女孩抱着纸箱跑", "女孩", "subjects"),
    ("两辆拉力赛车在沙地赛场上竞速", "拉力赛车", "subjects"),
    ("一个道士，和僵尸对打", "道士", "subjects"),
    ("拿起一把剑", "长剑", "subjects"),
    ("竹简", "简牍", "subjects"),
    ("汝窑天青色", "汝窑", "crafts"),
    ("青花瓷瓶", "青花瓷", "crafts"),
    ("蓝晒印相", "蓝晒", "crafts"),
    ("银丝掐丝", "银丝掐丝", "crafts"),
    ("雕漆", "雕漆", "crafts"),
    ("宣纸", "宣纸", "materials"),
    ("青瓷釉", "青瓷釉", "materials"),
    ("镜面", "镜面", "materials"),
    ("雾", "雾", "materials"),
]


def run(config):
    for k, v in config.items():
        setattr(N, k, v)
    hit = 0
    miss = []
    for q, want, ch in CASES:
        items, _m, subj, _d, craft, mat = N._rank(
            q, M, C, "cpu", 1, "导演/风格聚合", "不限", S, K, MT, True)
        obj = {"subjects": subj, "crafts": craft, "materials": mat}[ch]
        got = (obj or {}).get("zh", "")
        # 只看"有没有被选中"，不看是否拼进正文
        ok = bool(got) and (want in got or got in want)
        hit += ok
        if not ok:
            miss.append((q[:16], want, got or "无"))
    return hit, miss


CUR = {"SUBJECT_FLOOR": 0.52, "CRAFT_FLOOR": 0.52, "MAT_FLOOR": 0.52, "SCENE_FLOOR": 0.39}
SUG = {"SUBJECT_FLOOR": 0.52, "CRAFT_FLOOR": 0.52, "MAT_FLOOR": 0.54, "SCENE_FLOOR": 0.43}

h1, m1 = run(CUR)
h2, m2 = run(SUG)
print(f"  现值   命中 {h1}/{len(CASES)}")
print(f"  建议值 命中 {h2}/{len(CASES)}")
print()
if h2 > h1:
    print("  建议值更好 —— 改")
elif h2 < h1:
    print("  现值更好 —— 不改")
else:
    print("  一样 —— 不改（少动一次就少一次风险）")
for q, w, g in m1[:6]:
    print(f"    [现值未中] {q:<18} 期望 {w:<8} 实得 {g}")
print("\n### AB_DONE")
