"""第五批 + 更严的检测：空位 + 节拍/主体错配"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

CASES = [
    "太空舱里，一个人漂在舷窗前",
    "法庭上，被告站起来说话",
    "教室里，一个学生在窗边发呆",
    "手术室里，医生正在缝合",
    "地铁车厢里，所有人都在看手机",
    "山路上，一个挑夫背着东西往上走",
]

# 主体是"非人"时，节拍不该出现"脚步 / 手"
NONHUMAN = ("车", "船", "机", "舱", "炮", "艇")
HUMAN_ACTS = ("脚步", "手放在", "膝盖", "手指", "抬眼")

for q in CASES:
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    holes = []
    if "只使用<环境声>" in out:
        holes.append("声音")
    if "不要出现：<" in out:
        holes.append("风险")
    if "<风格：库中" in out:
        holes.append("风格")
    if "<写：" in out:
        holes.append("节拍")
    beat = [x for x in out.split("。") if x.startswith(("2 到", "3 到"))]
    bad = ""
    if beat and any(w in q for w in NONHUMAN) and any(a in beat[0] for a in HUMAN_ACTS):
        bad = " ⚠节拍错配"
    seg = [x.strip() for x in out.split("。") if x.strip()]
    print(f"【{q[:20]}】{len(out)} 字  "
          f"{'⚠ ' + '、'.join(holes) if holes else '✓'}{bad}")
    for x in seg[:6]:
        print("   " + x[:62])
    print()

print("### E2E5_DONE")
