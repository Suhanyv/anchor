"""再补三条风险：数钱（手部小物件）、抽烟（烟与火）、电梯楼道（墙面与透视）"""
import json
import os

RAW = r"F:\llm\data\raw"
p = os.path.join(RAW, "risk_ref.json")
d = json.load(open(p, encoding="utf-8"))

adds = {
    "手部小物件": {
        "kw": ["数钱", "点钞", "递", "接过", "钥匙", "零钱", "票"],
        "risk": ["手指数量与关节不对", "纸币边缘糊成一团", "手里的东西重量感像飘着"],
    },
    "烟与火": {
        "kw": ["抽烟", "点烟", "香烟", "打火机"],
        "risk": ["烟的形态循环重复、像贴图", "火苗不在烟头上", "烟挡住脸的位置不对"],
    },
    "楼道电梯": {
        "kw": ["电梯", "楼道", "楼梯间", "走廊"],
        "risk": ["墙面和门牌上的字错乱", "楼梯的级数在镜头里变化", "灯在电梯内闪得不自然"],
    },
}
for k, v in adds.items():
    if k not in d:
        d[k] = v
        print(f"  + risk·{k}")
    else:
        print(f"  跳过 risk·{k}")
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

import sys
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
dd = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = dd["模型目录"][1]["default"], dd["语料文件"][1]["default"]
S, K, MT = (dd["题材文件"][1]["default"], dd["工艺文件"][1]["default"],
            dd["材质文件"][1]["default"])
for q in ("一个人在数钱", "深夜，一个人坐在楼梯上抽烟", "一个人站在电梯口等电梯"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    rk = [x for x in out.split("。") if x.startswith("不要出现")]
    print(f"  {q[:16]:<18} {rk[0][:50] if rk else '?'}")
