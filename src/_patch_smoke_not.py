"""夜市的声音错配成抽烟：因为"油烟"里有个"烟"。给抽烟加排除词。"""
import json
import os
import sys

RAW = r"F:\llm\data\raw"
p = os.path.join(RAW, "sound_ref.json")
d = json.load(open(p, encoding="utf-8"))
ns = list(d["抽烟"].get("not") or [])
for w in ("油烟", "炊烟", "烟囱", "香烟的烟", "冒烟"):
    if w not in ns:
        ns.append(w)
d["抽烟"]["not"] = ns
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  抽烟 排除:", ns)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
dd = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = dd["模型目录"][1]["default"], dd["语料文件"][1]["default"]
S, K, MT = (dd["题材文件"][1]["default"], dd["工艺文件"][1]["default"],
            dd["材质文件"][1]["default"])
for q in ("夜市里，油烟和灯泡底下全是人", "深夜，一个人坐在楼梯上抽烟"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    snd = [x for x in out.split("。") if x.startswith("只使用")]
    print(f"  {q[:18]:<20} {snd[0][6:40] if snd else '<空>'}")
