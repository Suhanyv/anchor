"""
材质/光库 v2：从 46 条扩到约 160 条

为什么要扩（依据）
------------------
c14 + materials_v1（46 条）实测：材质识别只有 4/8。
    暗角   -> 拉丝金属（错）
    帆布   -> 羊皮纸（错）
    混凝土 -> 羊皮纸/湿壁画（错）
    浅景深 -> 0.239 过低
根因是**内容不足**：一个材质只有 2 条英文短句，任何中文变体都很难对上。

扩法（两条硬规则）
------------------
1. **每个材质 6~7 条差异化实现**：不同物件、不同侧面，不是同一句改词。
2. **至少 2~3 条包含英文原名**（vignette / concrete / canvas / grain / parchment …）。
   理由：e5 是双语模型，中文"暗角"对得上英文 "vignette" 这个词本身，
   词面权重很高。第一版每个材质只有 1 条带原名，是被自己的写法拖累了。

materials_v1 (46) -> materials_v2 (~160)
"""
import json
import os

ROOT = r"F:\llm"
OUT = os.path.join(ROOT, "data", "raw", "materials_v2.jsonl")

# 材质英文名, 中文名, 输出短语, 中文关键词, [6~7 条英文实现]
DATA = [
    ("Scratched Steel", "钢/金属",
     "scratched steel plate with a hard rim light on the bevel",
     ["钢铁", "金属", "钢甲", "铠", "硬"],
     ["scratched steel plate, a hard rim of light on the bevel",
      "armour of worn steel, scratched, one hard rim of light",
      "a steel pauldron, the metal scratched and catching light",
      "steel surfaces dulled by wear, one edge catching the light",
      "brushed and scratched steel, cold grey metal, hard light"]),

    ("Brushed Metal", "拉丝金属",
     "brushed steel with fine parallel grain running one way",
     ["拉丝", "细纹", "金属表面"],
     ["brushed steel with fine parallel grain running one way",
      "a brushed metal panel, fine grain all in one direction",
      "spun metal with concentric fine scratches under a hard light",
      "brushed aluminium, the streaks catching a low light",
      "a brushed steel surface, matte with directional grain"]),

    ("Polished Metal", "抛光金属",
     "polished chrome throwing small hard specular points",
     ["抛光", "镜面", "高光", "反光"],
     ["polished chrome throwing small hard specular points",
      "mirror-polished metal, reflections bending at the profile",
      "a polished steel surface, one small bright specular point",
      "chrome so polished it mirrors the room, hard highlights",
      "polished brass, dulled in the hollows, bright on the raised forms"]),

    ("Silk", "丝绸",
     "silk draping in long soft falls, sheen travelling down the cloth",
     ["丝绸", "缎", "垂坠", "褶皱"],
     ["silk draping in long soft falls, sheen travelling down the cloth",
      "a silk robe hanging, the sheen sliding along every fall",
      "heavy silk curtain, light gliding down the drape",
      "silk satin, soft sheen, the fabric falling in long soft columns",
      "raw silk with a low sheen, folds catching a soft light",
      "silk embroidery ground, the satin catching light in long sweeps"]),

    ("Sheer Gauze", "薄纱",
     "sheer gauze layered, translucent where the light passes",
     ["薄纱", "半透明", "透光", "纱"],
     ["sheer gauze layered, translucent where the light passes",
      "thin gauze veiling a darker surface, light coming through",
      "translucent fabric, the shape behind it half readable",
      "layers of sheer tulle, each layer dimming what is behind",
      "gauze curtains, sun coming through the weave"]),

    ("Parchment", "羊皮纸",
     "parchment, dry fibrous grain, browned at the edges",
     ["羊皮纸", "泛黄", "纤维", "纸"],
     ["parchment, dry fibrous grain, browned at the edges",
      "an old parchment sheet, fibre visible, the margins darkened",
      "vellum with faint stains, matte and slightly cockled",
      "aged paper gone brittle, foxing across the surface",
      "a scroll of parchment, creased where it was rolled"]),

    ("Glazed Ceramic", "陶瓷",
     "glazed ceramic, fine crackle in the glaze, one wet highlight",
     ["陶瓷", "釉", "开片", "瓷"],
     ["glazed ceramic, fine crackle in the glaze, one wet highlight",
      "porcelain with a thin glaze and a small sharp reflection",
      "a celadon bowl, the glaze pooling at the foot",
      "ceramic crackle glaze, crazed evenly across the body",
      "stoneware, the glaze breaking over the rim"]),

    ("Coarse Canvas", "帆布",
     "coarse canvas, the weave wide open, stiff with size",
     ["帆布", "粗布", "织纹", "麻布"],
     ["coarse canvas, the weave wide open, stiff with size",
      "heavy canvas cloth, warp and weft clearly separate",
      "raw canvas stretched on a frame, the threads distinct",
      "duck canvas, thick and stiff, seams standing proud",
      "a canvas sail, patched, the weave showing through the paint"]),

    ("Raw Concrete", "混凝土",
     "raw concrete, form-tie holes, a chalky matte face",
     ["混凝土", "水泥", "粗糙", "墙面"],
     ["raw concrete, form-tie holes, a chalky matte face",
      "poured concrete, the board marks of the formwork showing",
      "bare concrete wall, chalky, dusting at the touch",
      "a brutalist concrete slab, seams and tie holes visible",
      "rough concrete, aggregate showing where it has eroded"]),

    ("Wet Concrete", "湿混凝土",
     "wet concrete, dark sheen, water standing in the low spots",
     ["湿", "积水", "地面", "反光"],
     ["wet concrete, dark sheen, water standing in the low spots",
      "a soaked concrete floor throwing a cold broken reflection",
      "concrete under water, the surface gone dark and glossy",
      "rain on concrete, the reflection smeared by the fall"]),

    ("Thick Glass", "玻璃",
     "thick glass, green at the cut edge, a hard reflection across the face",
     ["玻璃", "透明", "折射"],
     ["thick glass, green at the cut edge, a hard reflection across the face",
      "a glass pane, hard specular streak, refraction at the rim",
      "heavy glass block, distorted light behind it",
      "glass so thick it goes green, reflections stacked on reflections"]),

    ("Oiled Wood", "木纹",
     "oiled wood, open grain, a low sheen along the grain",
     ["木纹", "木头", "木"],
     ["oiled wood, open grain, a low sheen along the grain",
      "old timber, grain open, worn smooth where hands have been",
      "a wooden beam, coarse grain, catching a soft side light",
      "waxed wood floor, the grain running away into the dark"]),

    ("Worn Leather", "皮革",
     "stiff worn leather straps, rubbed smooth where they bend",
     ["皮革", "皮", "磨旧"],
     ["stiff worn leather straps, rubbed smooth where they bend",
      "a leather belt dull from handling, stiff to the touch",
      "old leather harness, cracked at the fold, polished at the wear points",
      "leather book binding, scuffed at the corners, dull sheen"]),

    ("Gold Leaf", "金箔",
     "gold leaf laid in overlapping sheets, seams catching light",
     ["金箔", "贴金", "金"],
     ["gold leaf laid in overlapping sheets, seams catching light",
      "gilt worn thin so the ground shows through in places",
      "gold foil pressed onto a surface, dull warm sheen",
      "gilded frame, the leaf lifting at one corner",
      "gold on a dark ground, seams of the leaf visible"]),

    ("Specular Highlight", "高光",
     "a hard specular highlight running along the rim",
     ["高光", "亮点", "镜面"],
     ["a hard specular highlight running along the rim",
      "one small bright specular point on a curved surface",
      "a specular highlight sliding along an edge as the light moves",
      "highlights sharp and small, the material reading as hard",
      "a specular streak across a glossy surface, everything else falling dark"]),

    ("Backlight", "逆光",
     "strong backlight, edges rimmed, the centre falling into shadow",
     ["逆光", "背光", "轮廓", "剪影"],
     ["strong backlight, edges rimmed, the centre falling into shadow",
      "the light behind the subject, only the outline reading",
      "backlit so the form is a silhouette with a bright halo",
      "rim light from behind separating the shape from the dark"]),

    ("Diffused Light", "柔光",
     "soft diffused light, no hard shadow edge anywhere",
     ["柔光", "漫射", "散射", "柔"],
     ["soft diffused light, no hard shadow edge anywhere",
      "flat diffused daylight, shadows open and shallow",
      "light through frosted glass, even and directionless",
      "overcast light, soft modelling, the transitions gentle"]),

    ("Volumetric Light", "体积光",
     "volumetric light, dust turning slowly inside the beam",
     ["体积光", "光束", "丁达尔", "尘"],
     ["volumetric light, dust turning slowly inside the beam",
      "a shaft of light with smoke making the beam visible",
      "god rays between columns, the air itself lit",
      "light cutting a path through haze, edges of the beam readable"]),

    ("Vignette", "暗角",
     "a photographic vignette, the four corners of the picture going dark",
     ["暗角", "压暗", "边缘"],
     ["a photographic vignette, the four corners of the picture going dark",
      "vignette: brightness falling off toward the corners of the frame",
      "the corners of the photo underexposed, the middle held bright",
      "a dark vignette closing in the four corners of the image",
      "lens vignette, the perimeter of the picture dropping off",
      "the image darkening in a ring around the corners",
      "corners of the photograph lost to shadow, centre correctly exposed"]),

    ("Film Grain", "胶片颗粒",
     "fine film grain across the whole frame",
     ["颗粒", "胶片", "噪点"],
     ["fine film grain across the whole frame",
      "visible silver grain, coarser in the shadows",
      "film grain: a fine random texture over every part of the image",
      "35mm grain, the texture of the emulsion showing",
      "high-ISO noise, coloured speckle in the dark areas"]),

    ("Shallow Depth", "浅景深",
     "shallow depth of field, the background thrown out of focus",
     ["浅景深", "虚化", "背景"],
     ["shallow depth of field, the background thrown out of focus",
      "shallow focus: only the near subject sharp, the rest melting",
      "a wide aperture look, background turned to soft discs",
      "depth of field shallow, the far plane dissolved into bokeh",
      "only one narrow plane in focus, foreground and background soft"]),

    ("Hard Light", "硬光",
     "one hard directional source, the shadow edge crisp",
     ["硬光", "强光", "硬"],
     ["one hard directional source, the shadow edge crisp",
      "hard light from the side, the falloff abrupt",
      "a single bare bulb, hard shadows thrown onto the wall",
      "sunlight hard and high, shadows with sharp edges"]),

    ("Suspended Dust", "浮尘/雪粒",
     "fine grains suspended in the air, each one catching the light",
     ["尘", "雪粒", "飞", "颗粒"],
     ["fine grains suspended in the air, each one catching the light",
      "dust drifting in a shaft of light, bright points against the dark",
      "snow grains hanging in the beam, sharp small highlights",
      "pollen and dust turning in the sun, out of focus and bright"]),
]


def main():
    rows = []
    n = 0
    for en, zh, phrase, kws, variants in DATA:
        for v in variants:
            n += 1
            rows.append({
                "doc_id": f"m{n:04d}",
                "kind": "material",
                "mat_en": en, "mat_zh": zh,
                "phrase": phrase, "kw_zh": kws,
                "description": v, "text_semantic": v,
            })
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    c = Counter(r["mat_zh"] for r in rows)
    print(f"材质库 v2: {len(DATA)} 个材质 / {len(rows)} 条 -> {OUT}")
    print()
    print(f"{'材质':<12} 条数  含英文原名的条数")
    canon = {"暗角": "vignette", "胶片颗粒": "grain", "浅景深": "depth of field",
             "混凝土": "concrete", "帆布": "canvas", "羊皮纸": "parchment",
             "丝绸": "silk", "金箔": "gold leaf", "陶瓷": "glaze",
             "薄纱": "gauze", "玻璃": "glass", "皮革": "leather", "木纹": "wood",
             "拉丝金属": "brushed", "抛光金属": "polished", "钢/金属": "steel",
             "高光": "specular", "逆光": "backlit", "柔光": "diffused",
             "体积光": "volumetric", "硬光": "hard", "浮尘/雪粒": "grain"}
    for zh, k in sorted(c.items()):
        word = canon.get(zh, "")
        has = sum(1 for r in rows if r["mat_zh"] == zh and word and word in r["text_semantic"].lower())
        flag = "" if has >= 2 else "  <-- 含原名不足 2 条"
        print(f"  {zh:<12} {k:>3}   {has}{flag}")
    print(f"\n### MATERIALS_V2_DONE")


if __name__ == "__main__":
    main()
