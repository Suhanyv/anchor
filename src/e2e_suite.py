"""
端到端回归套件：30 条自然句 + 四类判据

为什么要固化
------------
2026-11-01 一天里测了五批，每批现写脚本、现挑句子、现想判据。
其中一次被自己的检测骗了：**"没有占位符"放过了"车在追、写人跑"** ——
夜里的追车那条，节拍是"跑出两三步，脚步在水或土上留下痕迹"。

所以判据必须有四条，而且必须落盘：

    ① 空位      声音 / 风险 / 风格 / 节拍 是不是还留着占位符
    ② 错配      主体不是人（车/船/舱）时，节拍里不该出现脚步、手、膝盖
    ③ 泄漏      技术指令的名字（85mm、跳漂法、空镜…）不该出现在正文句子里
    ④ 矛盾      空镜 + 两人同框；黑白 + 暖金；无人 + 两人同框

用法
----
    python src/e2e_suite.py            # 跑全部，报通过数
    python src/e2e_suite.py 追车 法庭   # 只跑含这些字的

基线
----
2026-11-01 固化时：**15/30**。
失败集中在两处，且都不是逻辑 bug：
    · 风格空 ×12   日常场景（菜市场、理发店、阳台、考场…）检索不到风格
    · 缺条目        出租车停着、渔船、厨房、猎人 —— 节拍/声音/风险还没写
这说明下一阶段的重心是**补日常，不是改逻辑**。
"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

# 30 条：五批测试用过的自然句，全部来自人话，不是模板
CASES = [
    # 第一批
    "一个女人在菜市场挑鱼", "深夜，一辆出租车停在桥上",
    "一个老人坐在公园长椅上喂鸽子", "雪天，一个猎人蹲在树后",
    "海上，一艘渔船在暴风雨里", "赛博朋克，一个女孩在巷子里走",
    # 第二批
    "一个女人在厨房里做饭", "一个人站在电梯口等电梯",
    "下雨了，一个男人撑着伞在路边等", "一个人在数钱",
    "一个小男孩蹲在地上看蚂蚁", "深夜，一个人坐在楼梯上抽烟",
    # 第三批
    "医院的走廊里，一个护士推着车走过", "便利店夜班，一个店员在擦货架",
    "一个男人在理发店剃头", "一个女人在阳台上晾衣服",
    "一个修车工钻在车底下", "婚礼上，一桌人在敬酒",
    # 第四批
    "夜里的追车，两辆车在桥上别", "审讯室里，一个人被问了三个小时",
    "古代法场，一个犯人跪着", "夜市里，油烟和灯泡底下全是人",
    "考场里，所有人都在低头写", "车站月台上，两个人告别",
    # 第五批
    "太空舱里，一个人漂在舷窗前", "法庭上，被告站起来说话",
    "教室里，一个学生在窗边发呆", "手术室里，医生正在缝合",
    "地铁车厢里，所有人都在看手机", "山路上，一个挑夫背着东西往上走",
]

NONHUMAN = ("车", "船", "舱", "艇", "炮", "飞机")
HUMAN_ACTS = ("脚步", "手放在", "膝盖", "手指", "抬眼", "抬手")
TECH_NAMES = ("85mm", "35mm", "50mm", "跳漂法", "空镜", "低角度", "大特写",
              "伦勃朗光", "分脸光", "对称构图", "三分构图")


def check(q, out):
    """返回 (问题列表, 节拍句)"""
    bad = []
    if "只使用<环境声>" in out:
        bad.append("声音空")
    if "不要出现：<" in out:
        bad.append("风险空")
    if "<风格：库中" in out:
        bad.append("风格空")
    if "<写：" in out:
        bad.append("节拍空")

    beat = next((x for x in out.split("。") if x.startswith(("2 到", "3 到", "6 到"))), "")
    # 人推车 / 人抬东西不算"非人主体"——护士推着车走过，脚步是对的
    _human_driving = any(w in q for w in ("推着车", "推车", "抬着", "抱着", "背着", "骑着"))
    if (beat and not _human_driving and any(w in q for w in NONHUMAN)
            and any(a in beat for a in HUMAN_ACTS)):
        bad.append("节拍错配")

    body = out.split("。")[2] if len(out.split("。")) > 2 else out
    for t in TECH_NAMES:
        if t in body:
            bad.append(f"泄漏:{t}")
            break

    # ③ 主体是动物，节拍里不该出现"人"
    ANIMALS = ("狗", "猫", "鸟", "鸽子", "马", "牛", "鲸", "鱼", "蛇", "熊")
    if beat and any(w in q for w in ANIMALS) and "人" in beat:
        bad.append("动物配了人的动作")

    # ④ 没写兵器，节拍里不该出现兵器
    WEAPON_WORDS = ("剑", "刀", "枪", "斧", "矛", "棍", "弓", "兵器")
    if beat and "兵器" in beat and not any(w in q for w in WEAPON_WORDS):
        bad.append("空手却写兵器")

    two = any(x.startswith("景别") and "两个人同框" in x for x in out.split("。"))
    empty = any("人不入画" in x for x in out.split("。"))
    if two and empty:
        bad.append("空镜+两人同框")
    return bad, beat


def main(filt=None):
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
    S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                d["材质文件"][1]["default"])
    cases = [q for q in CASES if not filt or any(f in q for f in filt)]
    ok = 0
    fails = []
    for q in cases:
        out, _ = N.LocalStyleHint().run(
            q, M, C, S, K, MT, True, "文生视频", False,
            "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频",
            "导演/风格聚合", 1, "", False)
        bad, beat = check(q, out)
        if not bad:
            ok += 1
        else:
            fails.append((q, bad, beat))
    print(f"\n=== {ok}/{len(cases)} 通过 ===")
    for q, bad, beat in fails:
        print(f"  [{ '、'.join(bad) }] {q[:22]}")
        if beat:
            print(f"        节拍: {beat[:52]}")
    print("\n### SUITE_DONE")
    return ok, len(cases)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
