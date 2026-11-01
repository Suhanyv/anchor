"""
收尾三处：
1. 动物风险不适用于菜市场（"鱼"会带出"多出来的腿或尾巴"）
2. 菜市场要有光：顶棚下的日光 + 灯管，湿地面反光
3. 公园用斑驳树影
"""
import json
import os

RAW = r"F:\llm\data\raw"


def load(fn):
    return json.load(open(os.path.join(RAW, fn), encoding="utf-8"))


def save(fn, d):
    json.dump(d, open(os.path.join(RAW, fn), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


# 1) 动物风险排除市场语境
d = load("risk_ref.json")
if "动物" in d:
    ns = list(d["动物"].get("not") or [])
    for w in ("菜市场", "市场", "摊", "集市", "鱼摊", "冰冻", "砧板"):
        if w not in ns:
            ns.append(w)
    d["动物"]["not"] = ns
    save("risk_ref.json", d)
    print("  动物风险排除:", ns)

# 2) 加「市场光」
d = load("light_ref.json")
if "市场光" not in d:
    d["市场光"] = {
        "zh": "顶棚漏下的日光和几支灯管混在一起，湿地面把这两种光都反一遍",
        "en": "daylight through a canopy mixed with strip lights, both mirrored off wet floor",
        "kw": ["菜市场", "市场", "集市", "早市"],
    }
    save("light_ref.json", d)
    print("  + light_ref·市场光")

# 3) 场景 -> 光 的规则
p = os.path.join(RAW, "scene_light.json")
d = json.load(open(p, encoding="utf-8"))
rules = d["rules"]
have = {r["light"] for r in rules}
if not any(r["light"] == "市场光" for r in rules):
    rules.insert(0, {"when": ["菜市场", "集市", "早市", "摊位", "鱼摊"],
                     "light": "市场光",
                     "note": "市场是顶棚日光加灯管的混合光，不是纯荧光灯"})
if not any(r["light"] == "斑驳树影" for r in rules):
    rules.insert(0, {"when": ["公园", "树荫", "树下", "长椅"],
                     "light": "斑驳树影",
                     "note": "公园靠树影，光是被叶子切碎的"})
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  scene_light 规则前两条:", [r["light"] for r in rules[:2]])
