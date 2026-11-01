"""补：说（法庭陈述）、山路风险"""
import json
import os
import sys

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


d = load("beat_ref.json")
order = [k for k in d if not k.startswith("_")]
if "说" not in d:
    d["说"] = {"kw": ["说话", "陈述", "辩解", "发言", "喊冤"],
               "mid": "开口，停一下，手抬起来又放下，继续说下去",
               "end": "停在他说完、没有人接话的空档里"}
    order.append("说")
for k in list(d):
    if k.startswith("_"):
        order.append(k)
save("beat_ref.json", {k: d[k] for k in order})
print("  节拍总数:", len([k for k in order if not k.startswith("_")]))

d2 = load("risk_ref.json")
if "山路" not in d2:
    d2["山路"] = {"kw": ["山路", "石阶", "挑夫", "盘山"],
                  "risk": ["石阶的级数在镜头里变化", "扁担与肩膀的接触穿模",
                           "背上东西的重量感不对、像粘在身上"]}
    save("risk_ref.json", d2)
    print("  + risk·山路")

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
dd = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = dd["模型目录"][1]["default"], dd["语料文件"][1]["default"]
S, K, MT = (dd["题材文件"][1]["default"], dd["工艺文件"][1]["default"],
            dd["材质文件"][1]["default"])
for q in ("法庭上，被告站起来说话", "山路上，一个挑夫背着东西往上走"):
    out, _ = N.LocalStyleHint().run(
        q, M, C, S, K, MT, True, "文生视频", False,
        "即梦 Seedance 2.5 · 整段（中文）", "cpu", "视频", "导演/风格聚合", 1, "", False)
    bt = [x for x in out.split("。") if x.startswith(("2 到", "3 到"))]
    rk = [x for x in out.split("。") if x.startswith("不要出现")]
    print(f"\n  {q[:16]}")
    print("    节 " + (bt[0][:44] if bt else "<空>"))
    print("    险 " + (rk[0][:44] if rk else "<空>"))
