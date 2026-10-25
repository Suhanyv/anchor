"""
知识库扩充 v4：现代材质 12 项 + 自然元素 12 项

为什么是这两个方向
------------------
前三批从博物馆元数据里挖的是**历史工艺**（窑口、珐琅、织锦）。
但用户描述现代画面时最常缺的是另外两类：

    现代材质   霓虹灯管 / 亚克力 / 镜面 / LED / 清水混凝土 / 铬 / 树脂 …
    自然元素   雾 / 浪 / 火 / 烟 / 雨 / 冰 / 雪 / 尘 / 水 / 云 / 树影 / 沙

这些在博物馆词表里根本没有，只能自己写。
它们都属于「材质」通道——这个通道的定位就是**质感与光**，
雾和雨本质上也是质感与光，所以放这里比放题材更合适。

产物
----
    materials_v8
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

MODERN = [
    ("Neon Tube", "霓虹灯管",
     "a bent glass tube glowing at its core, the colour spilling onto the nearest surface",
     ["霓虹", "灯管", "发光", "粉紫"],
     ["a bent glass tube lit from inside, the bend brightest",
      "neon reflected on wet ground but not lighting the air",
      "the tube dead at one end where the gas has gone"]),

    ("Acrylic", "亚克力",
     "cast acrylic thick enough to carry light along its edge, everything behind it slightly displaced",
     ["亚克力", "有机玻璃", "透光", "厚边"],
     ["a thick acrylic edge lit so the light travels inside it",
      "clear acrylic with a shape behind it faintly doubled",
      "the cut face polished, the flat faces not quite"]),

    ("Mirror", "镜面",
     "a mirror flat enough that the reflection has no depth of its own, the edge beveled",
     ["镜面", "反射", "倒影", "镀银"],
     ["a mirror whose reflection has no depth, only the surface it faces",
      "the bevel at the edge splitting the reflection into two",
      "dust on the glass reading as a haze over the whole reflection"]),

    ("LED Strip", "LED 灯带",
     "a strip of diodes hidden behind an edge, the light falling in soft dots",
     ["灯带", "LED", "点状光", "冷白"],
     ["an LED strip tucked behind a lip, each diode faintly separate on the wall",
      "the source hidden, only the falloff visible",
      "a cool white line where two surfaces meet"]),

    ("Fair-faced Concrete", "清水混凝土",
     "concrete left as it came out of the formwork, the tie holes and board marks kept",
     ["清水混凝土", "模板痕", "对拉孔", "灰"],
     ["concrete with the board grain still in it and tie holes at intervals",
      "the surface sealed so it reads grey rather than white",
      "a formwork joint running diagonally across the whole wall"]),

    ("Stainless Steel", "不锈钢",
     "polished stainless that reflects a room as a smear without edges",
     ["不锈钢", "拉丝", "反射", "冷"],
     ["polished stainless reflecting the room as an unreadable smear",
      "brushed stainless where the reflection stretches along the grain",
      "fingerprints the only thing that reads on the surface"]),

    ("Frosted Glass", "磨砂玻璃",
     "frosted glass where a shape moves behind it as a change of brightness only",
     ["磨砂", "半透", "模糊", "背光"],
     ["a shape moving behind frosted glass, only its brightness changing",
      "the glass lit from behind so the frost reads as grain",
      "a hand pressed to the far side, no detail at all"]),

    ("Chrome", "电镀铬",
     "chrome with a hard highlight and a reflection bent out of shape at the curve",
     ["铬", "电镀", "硬高光", "变形"],
     ["chrome with a hard specular edge and everything else falling to black",
      "the reflection stretched and bent at the tightest curve",
      "the plating worn through to yellow at a corner"]),

    ("Epoxy Resin", "树脂",
     "poured resin with objects held inside it, the top surface flat and glassy",
     ["树脂", "浇注", "透明", "悬浮"],
     ["objects suspended in poured resin, their edges slightly softened",
      "the top surface glassy while the sides stay matte",
      "bubbles caught where the pour folded over itself"]),

    ("Rubber", "橡胶",
     "matte black rubber that takes light without returning any, the texture fine and even",
     ["橡胶", "哑黑", "吸光", "细纹"],
     ["matte rubber taking light and returning nothing",
      "a fine even grain across the surface, no sheen anywhere",
      "the edge of a rubber sheet lifting but still black"]),

    ("Asphalt", "沥青",
     "asphalt still wet, reading black with the sky lying in it",
     ["沥青", "路面", "积水", "黑"],
     ["wet asphalt holding the sky in it",
      "dry asphalt going pale grey where traffic has polished the aggregate",
      "a repair patch darker than the road around it"]),

    ("Painted Steel", "喷漆钢",
     "painted steel with the paint thick enough to soften the edge, chips showing grey underneath",
     ["喷漆", "钢", "掉漆", "平整"],
     ["paint thick enough to round the edge of the metal under it",
      "chips down to grey primer at the corner",
      "one coat over another, the second slightly different in colour"]),
]

NATURAL = [
    ("Mist", "雾",
     "mist thick enough to delete the far bank, the near surface left dry",
     ["雾", "水汽", "低能见度", "灰白"],
     ["mist erasing everything past twenty metres, the near ground still sharp",
      "fog lying in layers, each one showing the one behind it",
      "breath adding to the mist instead of clearing it"]),

    ("Surf", "浪",
     "a wave breaking into white with the face still holding colour behind it",
     ["浪", "碎浪", "白沫", "海面"],
     ["a wave breaking at the top, the face behind it still green",
      "foam running up the sand and stopping short",
      "the back of a swell reading as a smooth wall"]),

    ("Sand", "沙",
     "dry sand moving in a sheet across the surface, the grains too fine to resolve",
     ["沙", "沙丘", "颗粒", "干"],
     ["sand moving as a sheet rather than grain by grain",
      "ripples cut into dry sand by the wind, no footprints",
      "wet sand dark and holding a reflective skin"]),

    ("Fire", "火",
     "flame with no hard edge, the light it throws hard and flickering",
     ["火", "火焰", "跳动", "暖"],
     ["flame with no fixed outline, the light it throws much harder",
      "embers going from orange to grey without passing through red",
      "fire seen through its own smoke, the edges doubled"]),

    ("Smoke", "烟",
     "smoke lit from one side so only its edge registers, the body transparent",
     ["烟", "烟雾", "侧光", "透明"],
     ["smoke lit from the side so only the lit edge exists",
      "smoke thinning upward until it stops being visible at all",
      "a plume holding shape for a moment before losing it"]),

    ("Rain", "雨",
     "rain visible only where it crosses a light, the ground taking it without a splash",
     ["雨", "落雨", "细线", "反射"],
     ["rain visible only where it crosses a light source",
      "drops on a window running together into one line",
      "heavy rain flattening the background into grey"]),

    ("Ice", "冰",
     "ice with trapped air and a crack running along a plane it will not cross",
     ["冰", "冰面", "裂纹", "气泡"],
     ["ice with air trapped in layers, the crack stopping at a seam",
      "the surface wet where it has begun to melt, the body still solid",
      "light entering ice and going milky after a few centimetres"]),

    ("Snow", "雪",
     "snow falling thick enough to flatten the frame, every edge softened at once",
     ["雪", "落雪", "白", "柔边"],
     ["snow falling close to the lens, each flake a soft disc",
      "snow settling on a dark surface and erasing the texture first",
      "the far distance gone white before the near ground is covered"]),

    ("Dust", "尘",
     "dust hanging in a shaft of light, visible only because it is lit",
     ["尘", "浮尘", "光束", "细颗粒"],
     ["dust in a shaft of light, invisible outside it",
      "a surface where the dust shows every place a hand has been",
      "dust settling slowly, the air otherwise still"]),

    ("Water Surface", "水面",
     "a water surface broken into small hard highlights, the depth unreadable",
     ["水面", "波纹", "反光", "倒影"],
     ["water broken into small hard highlights with no readable depth",
      "a still surface reflecting everything at half contrast",
      "one stone dropping and the rings widening past the frame"]),

    ("Cloud", "云",
     "cloud layer on layer, only the nearest edge lit and the rest flat",
     ["云", "云层", "边缘光", "层"],
     ["clouds stacked so each layer shows as a band of tone",
      "the underside of a cloud lit from below by a city",
      "a single cloud with a hard lit edge and a soft body"]),

    ("Foliage Shadow", "树影",
     "leaf shadow moving on a wall, the edges soft because the source is broad",
     ["树影", "叶影", "斑驳", "移动"],
     ["leaf shadow on a wall, edges soft because the light is broad",
      "the shadow moving without the branch being visible",
      "sun through leaves breaking into patches rather than shapes"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    src = os.path.join(RAW, "materials_v7.jsonl")
    out = os.path.join(RAW, "materials_v8.jsonl")
    rows = load(src)
    sample = rows[0]
    k_en = next(k for k in sample if k.endswith("_en"))
    k_zh = next(k for k in sample if k.endswith("_zh"))

    n = len(rows)
    added = []
    for group, entries in (("现代材质", MODERN), ("自然元素", NATURAL)):
        for en, zh, phrase, kw, variants in entries:
            for v in variants:
                n += 1
                added.append({"doc_id": f"m{n:04d}", "kind": "material",
                              k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                              "description": v,
                              "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"})

    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  materials_v7 -> v8 : {len(rows)} -> {len(rows)+len(added)}"
          f"  (+{len(added)} 条 / {len(MODERN)+len(NATURAL)} 项)")
    print(f"    现代材质 {len(MODERN)} 项 · 自然元素 {len(NATURAL)} 项")
    print("\n### KB_V4_DONE")


if __name__ == "__main__":
    main()
