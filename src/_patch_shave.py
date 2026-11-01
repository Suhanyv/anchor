"""补「剃/剪」节拍"""
import json
import os

RAW = r"F:\llm\data\raw"
p = os.path.join(RAW, "beat_ref.json")
d = json.load(open(p, encoding="utf-8"))
if "剃" not in d:
    d["剃"] = {"kw": ["剃", "剪头发", "推子", "理发"],
               "mid": "推子从下往上推过去，头发成片落下，停一下再推第二道",
               "end": "停在他头发落到肩上的那一刻，镜子里的表情还在"}
    print("  + beat·剃")
order = [k for k in d if not k.startswith("_")]
if "剃" in order:
    order.remove("剃")
    order.insert(order.index("擦") + 1 if "擦" in order else len(order), "剃")
json.dump({k: d[k] for k in order}, open(p, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("  beat 总数:", len([k for k in order if not k.startswith("_")]))

import sys
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
dd = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = dd["模型目录"][1]["default"], dd["语料文件"][1]["default"]
S, K, MT = (dd["题材文件"][1]["default"], dd["工艺文件"][1]["default"],
            dd["材质文件"][1]["default"])
out, _ = N.LocalStyleHint().run(
    "一个男人在理发店剃头", M, C, S, K, MT, True, "文生视频", False,
    "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
bt = [x for x in out.split("。") if x.startswith(("2 到", "0 到"))]
for x in bt:
    print("  " + x[:60])
