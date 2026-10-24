"""
材质/光库：第四条通道

为什么需要独立通道
------------------
材质/光文档级评测 47%，且审计确认 8/8 失败都是「真错」（top1 与概念的余弦相似度
接近零甚至负数），不是词面判分不公。根因：
    v12 补的材质词只存在于 795 条里的约 24 条，被稀释得几乎不起作用。

今天已经三次实测证明「混在一起就互相抢」：
    350 条视频文档进风格索引 -> 风格 -1.5pp
    48 条工艺文档进风格索引   -> 场景 -5pp、材质 -7pp
    全局去偏（不减分类）      -> 场景 -10pp
-> 材质/光也必须是独立通道。

与其它通道的关系
----------------
    题材（画什么）  vs  工艺 / 材质（怎么做）   -> **互斥**（谁分高谁说话）
    工艺              vs  材质                  -> **可共存**（"蓝晒的丝绸照片"成立）

phrases 写成可直接拼进提示词的描述，锚定具体表象（不写"高级感"这类通用词）。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "materials_v1.jsonl")

# (英文名, 中文名, 输出短语, [英文变体], [中文关键词])
MATERIALS = [
    ("Scratched Steel", "钢/金属",
     "scratched steel plate, one hard rim of light on the bevel",
     ["worn steel plate, a thin hard light grazing the scratches",
      "matte steel, one hard rim of light and a black falloff beside it"],
     ["钢铁", "金属", "钢甲", "铠", "硬"]),

    ("Brushed Metal", "拉丝金属",
     "brushed steel with fine parallel grain catching the light",
     ["a brushed metal panel, fine grain running one way",
      "spun metal with concentric fine scratches under a hard light"],
     ["拉丝", "金属", "细纹"]),

    ("Polished Metal", "抛光金属",
     "polished metal throwing a small hard specular highlight",
     ["mirror-polished metal with one small bright specular point",
      "polished chrome, hard reflections bending at the edges"],
     ["抛光", "高光", "镜面"]),

    ("Silk", "丝绸",
     "silk draping in long soft falls, a sheen sliding down the drape",
     ["silk hanging in long soft falls, light sliding along the drape",
      "heavy silk draping, sheen travelling down the fall of the cloth"],
     ["丝绸", "缎", "垂坠", "褶皱"]),

    ("Sheer Gauze", "薄纱",
     "sheer gauze, translucent where the light passes through",
     ["layered sheer fabric, the light coming through it",
      "thin translucent gauze over a darker surface"],
     ["薄纱", "半透明", "透光", "纱"]),

    ("Parchment", "羊皮纸",
     "parchment with a dry fibrous grain and browned edges",
     ["an aged parchment sheet, fibre showing, edges browned",
      "dry vellum with faint stains and a matte surface"],
     ["羊皮纸", "纸", "泛黄", "纤维"]),

    ("Glazed Ceramic", "陶瓷",
     "glazed ceramic with a fine crackle and one wet highlight",
     ["a glazed ceramic surface, crackle in the glaze, wet highlight",
      "porcelain with a thin glaze and a small sharp reflection"],
     ["陶瓷", "釉", "开片", "瓷"]),

    ("Coarse Canvas", "帆布",
     "coarse canvas cloth, the weave wide open and stiff with size",
     ["heavy canvas cloth, warp and weft clearly separate",
      "raw canvas stretched on a frame, the threads of the cloth distinct"],
     ["帆布", "粗布", "织纹"]),

    ("Raw Concrete", "混凝土",
     "raw concrete with form-tie holes and a chalky surface",
     ["poured concrete, tie holes and a chalky matte face",
      "board-marked concrete with the grain of the formwork"],
     ["混凝土", "水泥", "粗糙", "墙"]),

    ("Wet Concrete", "湿混凝土",
     "wet concrete with a dark sheen and standing water",
     ["wet concrete reflecting a cold light, water standing in the low spots",
      "a soaked concrete floor, reflections breaking up"],
     ["湿", "积水", "反光", "地面"]),

    ("Thick Glass", "玻璃",
     "thick glass with a green edge tint and a hard reflection",
     ["thick glass, green at the cut edge, hard reflection across the face",
      "a glass pane with a hard specular streak and refraction at the rim"],
     ["玻璃", "透明", "折射"]),

    ("Oiled Wood", "木纹",
     "oiled wood with open grain and a low sheen",
     ["oiled timber, open grain catching a soft side light",
      "old wood with visible grain and worn edges"],
     ["木纹", "木头", "木"]),

    ("Worn Leather", "皮革",
     "stiff worn leather straps, rubbed smooth where they bend",
     ["old stiff leather straps, the surface rubbed smooth with use",
      "a leather belt and straps, dull from handling, stiff to the touch"],
     ["皮革", "皮", "磨旧"]),

    ("Gold Leaf", "金箔",
     "gold leaf with a dull warm sheen and visible seams",
     ["gold leaf laid in overlapping sheets, seams catching light",
      "gilt worn thin so the ground shows through in places"],
     ["金箔", "贴金", "金"]),

    ("Specular Highlight", "高光",
     "a hard specular highlight running along the edge",
     ["one hard specular highlight along the rim, everything else falling dark",
      "a small bright specular point on a curved surface"],
     ["高光", "反光", "亮点"]),

    ("Backlight", "逆光",
     "strong backlight, edges rimmed and the centre in shadow",
     ["the light behind the subject, edges glowing, face in shadow",
      "backlit so only the outline reads clearly"],
     ["逆光", "背光", "轮廓"]),

    ("Diffused Light", "柔光",
     "soft diffused light with no hard shadow edge",
     ["flat diffused daylight, shadows soft and open",
      "light through frosted glass, even and shadowless"],
     ["柔光", "漫射", "柔", "散射"]),

    ("Volumetric Light", "体积光",
     "volumetric light with dust suspended in the beam",
     ["a shaft of light with dust turning slowly inside it",
      "beam cutting through smoke, edges of the beam visible"],
     ["体积光", "光束", "丁达尔", "尘"]),

    ("Vignette", "暗角",
     "a photographic vignette, the four corners of the photo going dark, the middle still lit",
     ["a lens vignette, brightness dropping toward the four corners of the photograph",
      "darkened corners in the photograph, the centre of the image exposed correctly"],
     ["暗角", "压暗", "边缘"]),

    ("Film Grain", "胶片颗粒",
     "fine film grain across the whole frame",
     ["visible silver grain throughout the image",
      "coarse grain in the shadows, fine in the highlights"],
     ["颗粒", "胶片", "噪点"]),

    ("Shallow Depth", "浅景深",
     "shallow depth of field in a photograph, the lens throwing the background out of focus",
     ["a photograph with only the near subject sharp, the lens blurring all behind it",
      "a narrow plane of focus in the photograph, near and far both soft"],
     ["浅景深", "虚化", "背景"]),

    ("Hard Light", "硬光",
     "hard directional light throwing a sharp shadow edge",
     ["one hard source, the shadow edge crisp on the wall",
      "hard light from the side, the transition dark to light abrupt"],
     ["硬光", "强光", "硬"]),

    ("Suspended Dust", "浮尘/雪粒",
     "fine grains suspended in the air, lit from behind",
     ["dust turning in the light, each grain catching it",
      "snow grains hanging in the beam, bright points against the dark"],
     ["尘", "雪粒", "飞", "颗粒"]),
]


def main():
    rows = []
    n = 0
    for en, zh, phrase, variants, kws in MATERIALS:
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

    print(f"材质/光库: {len(MATERIALS)} 个 / {len(rows)} 条 -> {OUT}")
    print()
    for en, zh, phrase, variants, kws in MATERIALS:
        print(f"  {zh:<10} {phrase[:64]}")
    print()
    print(f"### MATERIALS_V1_DONE")


if __name__ == "__main__":
    main()
