"""
知识库扩充 v3：玻璃珐琅 / 木漆 / 纺织 / 复合材质

来源同 v2：`harvest_cle_v1.json`（Cleveland 开放 API，CC0，3000 件作品的 technique 词频）。
只取词汇，不取任何作品标题、描述或图像。

本批思路
--------
前两批补的是东亚窑口与石材；这批补**欧洲与中东的工艺语汇**——
它们在我们的库里同样几乎空白，而用户描述"玻璃/织锦/镶嵌"时会用到：

    内填珐琅 / 彩色玻璃 / 光泽陶 / 熔块陶 / 锅岛烧
    细木镶嵌 / 竹刻 / 彩绘木雕 / 缂织 / 妆花锦
    萨米特锦 / 天鹅绒 / 花缎 / 灰泥 / 石膏底 / 胡桃瘿木 / 龟甲 / 琥珀 …

产物
----
    crafts_v6 / materials_v7
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

CRAFTS = [
    ("Champleve Enamel", "内填珐琅",
     "enamel poured into hollows cut in the metal, the metal walls left standing between colours",
     ["内填珐琅", "錾坑", "填烧", "金属胎"],
     ["colour sunk into cut hollows in the copper, the metal ridges left bare",
      "the enamel sitting lower than the surrounding gilt surface",
      "champleve where one hollow has fired unevenly and gone dull"]),

    ("Stained Glass", "彩色玻璃",
     "coloured glass held in lead cames, light passing through rather than falling on it",
     ["彩色玻璃", "铅条", "教堂窗", "透光"],
     ["coloured panes held in lead, the surface lit from behind",
      "silver stain turning the clear glass a warm amber",
      "the lead lines reading as black drawing across the colour"]),

    ("Lusterware", "光泽陶",
     "a metallic film fired onto the glaze, shifting between copper and gold with the angle",
     ["光泽陶", "虹彩", "金属膜", "釉上"],
     ["a thin metallic film fired over glaze, copper shifting to gold with the angle",
      "luster decoration catching light only where the bowl curves",
      "the iridescence breaking up where the film was thin"]),

    ("Fritware", "熔块陶",
     "a quartz-rich body with a white slip, thin-walled and hard, painted under a clear glaze",
     ["熔块陶", "石英胎", "白化妆土", "薄胎"],
     ["a quartz body under a white slip, the wall thin enough to ring",
      "painted decoration sitting under a clear glaze, no depth to it",
      "the body showing sandy where a chip has taken the slip off"]),

    ("Nabeshima Ware", "锅岛烧",
     "porcelain painted in underglaze blue and overglaze enamel, the design kept off the centre",
     ["锅岛烧", "蓝釉上彩", "留白", "日本瓷"],
     ["underglaze blue outlined and filled with overglaze enamel, the centre left bare",
      "a dish where the decoration runs around the rim only",
      "the enamel colours kept to three, each one flat"]),

    ("Marquetry", "细木镶嵌",
     "veneers of different woods cut and laid together, the grain doing the drawing",
     ["细木镶嵌", "木片", "拼花", "纹理"],
     ["cut veneers of different woods laid flush, the grain forming the pattern",
      "a marquetry panel where one piece has lifted at the edge",
      "dark ebony against pale holly, the joint invisible from a distance"]),

    ("Carved Bamboo", "竹刻",
     "bamboo carved so the rind is cut away, the pale inner fibre making the image",
     ["竹刻", "留青", "竹皮", "刻痕"],
     ["bamboo carved back to the inner fibre, the rind left as the ground",
      "a bamboo brushpot incised so shallow the cuts only show in raking light",
      "the carved surface going brown where hands have held it"]),

    ("Polychrome Wood Carving", "彩绘木雕",
     "carved wood with gesso and pigment, the paint worn to the wood at the high points",
     ["彩绘木雕", "贴金", "石膏底", "剥落"],
     ["painted wood where the pigment has worn through on the raised edges",
      "gesso ground cracking along the grain under the colour",
      "gold leaf over red bole, flaking at the corner of a fold"]),

    ("Tapestry Weave", "缂织",
     "weft-faced tapestry where the colour changes mid-pass, slits left between blocks",
     ["缂织", "挂毯", "纬线", "色块"],
     ["weft-faced tapestry, the colour stopping where the design changes",
      "small slits visible between two colour blocks in raking light",
      "the reverse showing loose thread ends and no pattern at all"]),

    ("Lampas", "妆花锦",
     "silk ground with a gold weft floated over it, the metal only on the face",
     ["妆花", "锦缎", "金线", "浮纬"],
     ["a silk ground with gold thread floated across the face only",
      "lampas where the gold catches light and the silk ground stays matte",
      "the reverse showing the gold carried as loose floats"]),
]

MATERIALS = [
    ("Samite", "萨米特锦",
     "a compound twill in silk, the pattern built into the weave rather than applied",
     ["萨米特", "斜纹", "织锦", "内纬"],
     ["a compound silk twill, the pattern part of the structure",
      "samite with the inner warps showing as a slight ridge",
      "the weave catching light in one direction only"]),

    ("Velvet", "天鹅绒",
     "a cut pile surface, light absorbed rather than reflected, darker where it is brushed one way",
     ["天鹅绒", "绒面", "割绒", "吸光"],
     ["cut pile that swallows light, the nap darker brushed one way",
      "velvet crushed where it was folded, the pile standing up again slowly",
      "the edge showing the warp ground beneath the pile"]),

    ("Damask", "花缎",
     "a reversible weave where the pattern reads only by the change of lustre",
     ["花缎", "同色暗花", "缎面", "反光差"],
     ["a monochrome weave where the pattern shows only as a change of lustre",
      "damask turned to the reverse, the pattern inverted but still there",
      "the sheen swinging across the cloth as it moves"]),

    ("Stucco", "灰泥",
     "lime plaster modelled while soft, the surface matte and slightly uneven",
     ["灰泥", "石膏", "抹面", "哑光"],
     ["lime plaster modelled while still soft, matte and slightly uneven",
      "stucco where the trowel sweep is still readable",
      "a moulded stucco edge chipped back to the grey core"]),

    ("Gesso", "石膏底",
     "a chalk ground laid on wood or canvas, absorbent and slightly rough under paint",
     ["石膏底", "粉底", "吸水", "打底"],
     ["a chalk ground under the paint, visible where the colour has worn",
      "gesso scored along the grain so the panel would not split",
      "the white ground drinking the first layer of colour"]),

    ("Walnut Burl", "胡桃瘿木",
     "burl walnut with a chaotic swirling grain, the figure denser than straight timber",
     ["胡桃瘿木", "瘿", "乱纹", "深色"],
     ["burl walnut, the grain swirling without a direction",
      "a veneer of walnut burl where the figure changes within centimetres",
      "the surface sanded flat but the grain still reading as knots"]),

    ("Sycamore Fig", "无花果木",
     "sycamore with a fine even grain and a pale warm tone, often gessoed over",
     ["无花果木", "细纹", "浅黄", "木胎"],
     ["sycamore with a fine even grain, pale and slightly warm",
      "the wood gessoed over so only the grain shows through",
      "a panel of sycamore warped very slightly along the grain"]),

    ("Bone Veneer", "骨贴面",
     "thin bone cut into strips and laid on wood, the joints tight but visible",
     ["骨贴面", "骨片", "拼贴", "接缝"],
     ["thin bone strips laid on a wood core, the joints tight but readable",
      "bone veneer where one strip has lifted slightly",
      "the surface polished so the bone shines and the wood stays dull"]),

    ("Clamshell", "蛤壳",
     "the inside of a shell used as a ground, the nacre catching light at the curve",
     ["蛤壳", "贝壳", "珠光", "内壁"],
     ["the inside of a shell painted on, the nacre still catching light",
      "a shell ground where the paint sits thin on the ridges",
      "the curve of the shell refusing to lie flat under the brush"]),

    ("Tortoiseshell", "龟甲",
     "translucent shell with mottled amber and dark patches, used as a veneer over a bright ground",
     ["龟甲", "玳瑁", "半透", "斑纹"],
     ["translucent shell laid over a bright ground so it glows from behind",
      "mottled amber and dark patches without a repeatable pattern",
      "the edge of a tortoiseshell veneer lifting from the wood"]),

    ("Amber", "琥珀",
     "amber with light passing through and stopping short, inclusions suspended inside",
     ["琥珀", "蜜蜡", "内含物", "暖透"],
     ["light entering amber and stopping short, warm rather than clear",
      "inclusions suspended inside the stone, each one a fleck",
      "the surface polished but soft enough to mark"]),

    ("Leaded Glass", "铅条玻璃",
     "flat glass held in lead cames, the glass itself uneven and slightly wavy",
     ["铅条玻璃", "平板玻璃", "不平", "铅条"],
     ["flat glass in lead cames, the sheet itself wavy enough to distort",
      "the lead thicker than the glass and reading as a dark line",
      "a pane where the glass is thicker at one corner"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def name_keys(sample):
    return (next(k for k in sample if k.endswith("_en")),
            next(k for k in sample if k.endswith("_zh")))


def build(src, out, entries, kind, prefix):
    rows = load(src)
    k_en, k_zh = name_keys(rows[0])
    base_n = len(rows)
    n = base_n
    added = []
    for en, zh, phrase, kw, variants in entries:
        for v in variants:
            n += 1
            added.append({"doc_id": f"{prefix}{n:04d}", "kind": kind,
                          k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                          "description": v,
                          "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"})
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(out):<22} {base_n} -> {len(rows)+len(added)}"
          f"  (+{len(added)} 条 / {len(entries)} 项)")


def main():
    print("=== 第三批：玻璃珐琅 / 木漆 / 纺织 / 复合 ===")
    build(os.path.join(RAW, "crafts_v5.jsonl"), os.path.join(RAW, "crafts_v6.jsonl"),
          CRAFTS, "craft", "c")
    build(os.path.join(RAW, "materials_v6.jsonl"), os.path.join(RAW, "materials_v7.jsonl"),
          MATERIALS, "material", "m")
    print("\n### KB_V3_DONE")


if __name__ == "__main__":
    main()
