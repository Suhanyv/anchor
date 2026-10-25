"""
天文批次：天体（题材）+ 天文现象（材质）

来源说明
--------
术语取自 NASA 图像库 API 的元数据（公共领域，脚本 `harvest_space.py`，
243 条元数据 / 218 个关键词）。**只取术语，不取图片、不抄描述**；
下面的英文描述与中文名都是本项目自己写的。

为什么天文属于"缺的那块"
------------------------
用户的真实请求「在太空中拍摄太阳的黑子」实测：
    题材 太空船内 0.4801（未过门槛）
    风格 斯皮尔伯格 0.3397（低置信）
**库里一个天体都没有。** 太阳/黑子/地球/星云这一整类缺失。

分配
----
    题材 +10  地球 / 月面 / 太阳黑子 / 土星环 / 木星 / 彗星 / 星云 / 星系 / 黑洞 / 极光
    材质 +6   日冕 / 明暗交界线 / 星轨 / 空间尘埃 / 太阳耀斑 / 真空黑

本脚本建完直接跑验证（新条目 + 累计对照）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

SUBJECTS = [
    ("Earth", "地球", "a planet seen from space, ocean and cloud bands, a hard day-night line",
     ["地球", "行星", "海洋", "云带"],
     ["a planet from space, oceans dark and cloud bands bright",
      "the day-night line crossing the globe at an angle",
      "thin blue haze along the limb only"]),
    ("Lunar Surface", "月面", "a grey cratered surface, shadows long and edges sharp, no atmosphere",
     ["月面", "月球", "环形山", "月壤"],
     ["a cratered grey surface, every edge sharp because there is no air",
      "long shadows from a low sun, the ground pale and granular",
      "bootprints holding their edges in fine dust"]),
    ("Sunspot", "太阳黑子", "a dark umbra inside a radiating penumbra on granulated photosphere",
     ["黑子", "本影", "半影", "太阳表面"],
     ["a dark umbra ringed by a fibrous penumbra on boiling granulation",
      "the penumbra filaments reaching out and thinning",
      "the spot smaller than the granulation around it suggests its scale"]),
    ("Saturns Rings", "土星环", "concentric bands seen nearly edge-on, gaps and a shadow cast on the planet",
     ["土星环", "环带", "行星环", "缝隙"],
     ["ring bands seen nearly edge-on, thinner than expected",
      "a gap in the rings where the planet shows through",
      "the planet's shadow cutting a dark band across the rings"]),
    ("Jupiter", "木星", "a banded gas giant, belts of ochre and cream, an oval storm",
     ["木星", "气态巨行星", "条纹", "风暴"],
     ["ochre and cream belts running parallel, edges turbulent not smooth",
      "an oval storm with a ragged edge rotating",
      "the limb hazy, atmosphere softening every contour"]),
    ("Comet", "彗星", "a nucleus with a dust tail and a straight ion tail pointing away from the sun",
     ["彗星", "彗尾", "尘埃尾", "离子尾"],
     ["two tails: one curved and dusty, one straight and ionised",
      "the coma bright and small next to a tail many times longer",
      "the tail always pointing away from the light source"]),
    ("Nebula", "星云", "a cloud of emission gas with dark dust lanes crossing it",
     ["星云", "气体云", "尘埃带", "发光"],
     ["emission gas glowing from within, dust lanes cutting across it",
      "the nebula edge sharp on one side and dissolving on the other",
      "stars visible through the thin parts only"]),
    ("Galaxy", "星系", "a spiral galaxy seen at an angle, arms and dust lanes, a bright core",
     ["星系", "旋臂", "尘埃带", "核心"],
     ["a spiral seen at an angle, arms trailing from a bright core",
      "dust lanes reading darker than the arms around them",
      "the outer arms dissolving into unresolved stars"]),
    ("Black Hole", "黑洞", "a dark disc with a thin bright ring bent around it, no surface",
     ["黑洞", "吸积盘", "引力透镜", "事件视界"],
     ["a dark disc with a thin bright ring bent around it",
      "the far side of the disc lifted over the top by lensing",
      "no surface anywhere, only the edge of what can be seen"]),
    ("Aurora", "极光", "curtains of green and violet light hanging above a dark horizon",
     ["极光", "极夜", "绿紫", "帘幕"],
     ["curtains of green hanging vertically, violet at the lower edge",
      "the light reflecting faintly off snow below",
      "structure inside the curtain, streaks not a flat glow"]),
]

MATERIALS = [
    ("Solar Corona", "日冕", "the sun's outer atmosphere, streamers radiating out, visible only against black",
     ["日冕", "日全食", "流束", "外大气"],
     ["streamers radiating outward, structure visible only against black",
      "the corona brightest at the limb and thinning with distance",
      "loops standing above the surface, faint and filamentary"]),
    ("Terminator", "明暗交界线", "the day-night line crossing a sphere, hard at the surface, softened by atmosphere",
     ["昼夜线", "明暗界线", "晨昏线", "半明半暗"],
     ["a hard line crossing a sphere, one side lit and one not",
      "the line softened by atmosphere into a band of twilight",
      "the line moving across a surface that has no detail of its own"]),
    ("Star Trails", "星轨", "stars drawn into arcs around a pole, accumulating over a long exposure",
     ["星轨", "长曝光", "同心弧", "极轴"],
     ["stars drawn into concentric arcs around a pole",
      "the arcs brighter where the stars were brighter",
      "the centre of rotation holding still while everything turns"]),
    ("Space Dust", "空间尘埃", "fine particles lit by a single source, everything else falling to black",
     ["尘埃", "微粒", "侧光", "真空"],
     ["particles catching light, visible only where they are lit",
      "a few grains crossing close to the lens, blurred",
      "everything else falling to absolute black"]),
    ("Solar Flare", "太阳耀斑", "a bright ribbon of emission above an active region, brightest at the ribbon",
     ["耀斑", "活动区", "磁环", "爆发"],
     ["a bright ribbon above an active region, brightest along its length",
      "loops reconnecting, brightness jumping then holding",
      "the ribbon's ends anchored in the surface"]),
    ("Vacuum Black", "真空黑", "black with no atmospheric scatter, stars remaining point-sharp",
     ["真空", "纯黑", "星星不闪", "无大气"],
     ["absolute black with no haze lifting it",
      "stars staying point-sharp, no twinkle anywhere",
      "no glow around bright objects, edges cut clean"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def name_keys(sample):
    return (next(k for k in sample if k.endswith("_en")),
            next(k for k in sample if k.endswith("_zh")))


def build(src, out, entries, kind, prefix, extra_type=None):
    rows = load(src)
    k_en, k_zh = name_keys(rows[0])
    n = len(rows)
    added = []
    for en, zh, phrase, kw, variants in entries:
        for v in variants:
            n += 1
            row = {"doc_id": f"{prefix}{n:04d}", "kind": kind,
                   k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                   "description": v, "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"}
            if extra_type and "type" in rows[0]:
                row["type"] = extra_type
            added.append(row)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(out):<20} {len(rows)} -> {len(rows)+len(added)}"
          f"  (+{len(added)} / {len(entries)} 项)")


def main():
    print("=== 天文批次 ===")
    build(os.path.join(RAW, "subjects_v8.jsonl"), os.path.join(RAW, "subjects_v9.jsonl"),
          SUBJECTS, "subject", "s", extra_type="object")
    build(os.path.join(RAW, "materials_v8.jsonl"), os.path.join(RAW, "materials_v9.jsonl"),
          MATERIALS, "material", "m")
    print("\n### KB_SPACE_DONE")


if __name__ == "__main__":
    main()
