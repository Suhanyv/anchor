"""
知识库扩充 v2：从博物馆元数据里捞出的东方窑口、金属工艺、装裱形制、石材

来源
----
`harvest_cle_v1.json` —— 克利夫兰美术馆开放 API（CC0）3000 件作品的 technique 词频。
**只取词汇，不取任何作品标题、描述或图像。**

为什么挑这些
------------
高频段（oil on canvas 196 次、bronze 103 次）我们已有覆盖；
低频段里反而藏着中文用户最会问、而库里一条都没有的东西：

    汝窑 / 建窑 / 唐三彩 / 兔毫 / 定窑 / 钧窑 / 哥窑 / 粉彩 / 斗彩
    立轴 / 册页 / 扇面
    鎏金 / 掐丝珐琅 / 错金银 / 錾刻 / 乌银
    片岩 / 滑石 / 雪花石膏 / 玉 / 青金石

产物
----
    subjects_v7 / crafts_v5 / materials_v6
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

CRAFTS = [
    ("Ru Ware", "汝窑", "porcelaneous stoneware under a pale blue-grey glaze webbed with fine crackle",
     ["汝窑", "天青", "开片", "汝瓷"],
     ["a Ru ware bowl, the glaze a pale blue-grey, fine crackle across the whole body",
      "the glaze stopping short of the foot in an irregular line",
      "light sinking into the glaze rather than reflecting off it"]),
    ("Jian Ware", "建窑", "dark iron-rich stoneware with a streaked hare's-fur glaze running down the bowl",
     ["建窑", "兔毫", "黑釉", "茶盏"],
     ["iron-rich dark stoneware, the glaze streaking silver down the inner wall",
      "a tea bowl where the glaze pools thick and dark at the foot",
      "hare's-fur striations radiating from the rim"]),
    ("Sancai Ware", "唐三彩", "lead-glazed earthenware in amber, green and cream running into each other",
     ["三彩", "唐三彩", "铅釉", "琥珀绿"],
     ["amber, green and cream lead glazes running together and stopping mid-body",
      "a camel figure glazed in three colours, the glaze crawling at the edges",
      "cream ground breaking through where the glaze ran thin"]),
    ("Ding Ware", "定窑", "ivory-white porcelain with incised ornament, the rim often bound in metal",
     ["定窑", "白瓷", "刻花", "芒口"],
     ["ivory-white porcelain with a lotus incised under the glaze",
      "the unglazed rim bound in a thin copper band",
      "soft white wall thin enough to show the shadow of a hand behind it"]),
    ("Jun Ware", "钧窑", "lavender and sky-blue glaze breaking into purple where it thins at the rim",
     ["钧窑", "窑变", "天蓝", "紫斑"],
     ["lavender and sky-blue glaze mottled with purple at the rim",
      "a Jun dish with a splashed copper-red mark sunk in the blue",
      "the glaze thick enough to run in a visible tongue down the side"]),
    ("Ge Ware", "哥窑", "grey-green glaze cut by a dark crackle network, the lines finer than a hair",
     ["哥窑", "冰裂", "金丝铁线", "开片"],
     ["a grey-green glaze webbed with dark crackle, the lines uneven in weight",
      "two crackle scales crossing, one dark and one gold",
      "the crackle continuing over the rim and into the interior"]),
    ("Famille Rose", "粉彩", "opaque pink and green enamels laid over glaze, slightly raised where they were painted",
     ["粉彩", "洋彩", "胭脂红", "玻璃白"],
     ["opaque pink enamel over glaze, the painted area sitting a little proud",
      "a famille-rose dish with a white ground holding a soft pink bloom",
      "the enamel shading from rose to white without a hard edge"]),
    ("Doucai", "斗彩", "under-glaze blue outline filled in with over-glaze enamel, the two never quite meeting",
     ["斗彩", "填彩", "青花勾线", "釉上"],
     ["a blue under-glaze outline filled with green and yellow enamel",
      "the enamel stopping just short of the blue line",
      "a chicken cup where blue and enamel are visibly two layers"]),
    ("Gilt Bronze", "鎏金", "gold leaf fired onto bronze, rubbed through at the high points",
     ["鎏金", "镀金", "火镀", "铜鎏金"],
     ["gold fired onto a bronze figure, worn through where hands have touched",
      "the gilt brightest in the recesses and thin on the raised edges",
      "mercury gilding gone patchy, the bronze showing brown underneath"]),
    ("Cloisonne Enamel", "掐丝珐琅", "wire cells filled with opaque enamel and fired, the gilding left bright",
     ["掐丝珐琅", "景泰蓝", "铜丝", "填珐琅"],
     ["copper wire bent into cells and filled with opaque enamel",
      "the gilding on the wires left bright against the fired colour",
      "a cloisonne vase where one cell has sunk slightly in firing"]),
    ("Metal Inlay", "错金银", "silver or gold wire hammered into channels cut in bronze, flush with the surface",
     ["错金银", "嵌错", "金银错", "錾槽"],
     ["silver wire beaten into a cut channel in bronze, flush with the surface",
      "a gold inlay following the curve of a bronze vessel",
      "the channel visible where a wire has worked loose"]),
    ("Chased Metal", "錾刻", "metal worked from the front with punches, the hammer marks left visible",
     ["錾刻", "锤揲", "打制", "浮雕"],
     ["a silver sheet raised from behind and chased from the front",
      "hammer marks left on the surface instead of being polished out",
      "the ornament standing a few millimetres above the ground"]),
    ("Niello", "乌银", "a black alloy fused into engraved lines, the silver ground left bright",
     ["乌银", "黑金", "嵌黑", "银胎"],
     ["black niello fused into engraved lines, the silver left bright between",
      "a niello plaque where the black has worn out of the deepest cuts",
      "the design reading as pure line, no colour anywhere else"]),
]

SUBJECTS = [
    ("Hanging Scroll", "立轴", "a hanging scroll on a wall, silk mounting above and below the painting",
     ["立轴", "挂轴", "装裱", "天头地头"],
     ["a hanging scroll on a wall, the silk mounting wider than the painting",
      "the scroll's bottom roller weighting the paper flat",
      "a hanging scroll half unrolled, the unshown part still furled"]),
    ("Album Leaf", "册页", "a single album leaf mounted flat, its border wider than the image",
     ["册页", "开", "裱边", "册"],
     ["an album leaf mounted flat, the silk border wider than the painting",
      "two leaves of an album open side by side",
      "a leaf turned, the blank verso showing through thin paper"]),
    ("Fan Leaf", "扇面", "a painting made for a folding fan, its shape a segment of an arc",
     ["扇面", "折扇", "扇骨", "弧形"],
     ["a painting shaped as an arc segment, made to be mounted on a fan",
      "the fan leaf spread, ribs showing as lines through the paper",
      "a fan folded so only one panel of the painting shows"]),
    ("Mural", "壁画", "pigment on a plaster wall, the surface uneven and the colour matte",
     ["壁画", "墙面", "矿物颜料", "剥落"],
     ["pigment on plaster, matte and slightly uneven in density",
      "a wall painting where the plaster has fallen away at one edge",
      "the surface showing the sweep of the trowel under the paint"]),
]

MATERIALS = [
    ("Schist", "片岩", "grey schist with a visible foliation, carved surfaces reading slightly granular",
     ["片岩", "片理", "灰", "石质"],
     ["grey schist, the foliation showing as fine parallel lines",
      "carved schist with a slightly granular, non-reflective surface",
      "the stone splitting along its layers where it was worked thin"]),
    ("Steatite", "滑石", "steatite carved soft, the surface soapy and slightly translucent at the edges",
     ["滑石", "皂石", "软", "半透"],
     ["steatite carved with a soft, slightly soapy surface",
      "the edges of a steatite carving going faintly translucent",
      "tool marks smoothing out rather than cutting clean"]),
    ("Alabaster", "雪花石膏", "alabaster translucent enough to glow, veined white and faintly warm",
     ["雪花石膏", "透光", "白", "纹理"],
     ["alabaster thin enough to let light through, warm rather than cold",
      "white alabaster with faint veins running across the carved face",
      "the surface polished but never glossy"]),
    ("Limestone", "石灰岩", "limestone with a chalky matte surface, fossil flecks in the grain",
     ["石灰岩", "白垩", "哑光", "化石"],
     ["limestone with a chalky matte surface and small fossil flecks",
      "a carved limestone relief, the background left rough",
      "the stone dusting white where it has been cut"]),
    ("Sandstone", "砂岩", "sandstone with visible grit, the colour running red or grey through the block",
     ["砂岩", "颗粒", "红砂岩", "粗"],
     ["sandstone with visible grit, red running through grey",
      "carved sandstone where the grain breaks the edge of the cutting",
      "the surface dry and absorbent, no polish at all"]),
    ("Granite", "花岗岩", "granite speckled black and white, hard enough that carvings stay blunt",
     ["花岗岩", "斑点", "硬", "结晶"],
     ["granite speckled black and white, the crystals visible at arm's length",
      "a granite surface polished to a cold even sheen",
      "carving on granite staying blunt, no fine detail possible"]),
    ("Nephrite Jade", "玉", "nephrite jade with a waxy lustre, colour uneven from grey-green to near white",
     ["玉", "和田玉", "温润", "油脂光"],
     ["nephrite with a waxy rather than glassy lustre",
      "jade uneven in colour, grey-green running to a near-white patch",
      "light entering the stone a little before stopping"]),
    ("Lapis Lazuli", "青金石", "lapis blue with pyrite flecks catching light, the ground a deep uneven blue",
     ["青金石", "群青", "金斑", "深蓝"],
     ["lapis blue with small pyrite flecks that catch the light",
      "the blue uneven, darker where the stone was richer",
      "a ground of lapis left matte so the flecks read"]),
    ("Ivory", "象牙", "ivory with a fine grain and a warm cream tone, ageing to amber at the surface",
     ["象牙", "牙质", "米黄", "细纹"],
     ["ivory with a fine grain, cream going amber where it aged",
      "a carved ivory surface polished but not glassy",
      "the grain running in fine lines across the cut face"]),
    ("Lindenwood", "椴木", "lindenwood carved close-grained and pale, the tool cuts holding their edges",
     ["椴木", "木雕", "浅色", "刀痕"],
     ["lindenwood carved close-grained and pale, cuts holding a clean edge",
      "the wood showing faint tool facets rather than sanded smooth",
      "gesso and paint sitting in the hollows of a lindenwood carving"]),
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
    base_n = len(rows)
    n = base_n
    added = []
    for en, zh, phrase, kw, variants in entries:
        for v in variants:
            n += 1
            row = {"doc_id": f"{prefix}{n:04d}", "kind": kind,
                   k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                   "description": v,
                   "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"}
            if extra_type and "type" in rows[0]:
                row["type"] = extra_type
            added.append(row)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(out):<22} {base_n} -> {len(rows)+len(added)}"
          f"  (+{len(added)} 条 / {len(entries)} 项)")


def main():
    print("=== 从博物馆词表扩充（v2）===")
    build(os.path.join(RAW, "crafts_v4.jsonl"), os.path.join(RAW, "crafts_v5.jsonl"),
          CRAFTS, "craft", "c")
    build(os.path.join(RAW, "subjects_v6.jsonl"), os.path.join(RAW, "subjects_v7.jsonl"),
          SUBJECTS, "subject", "s", extra_type="object")
    build(os.path.join(RAW, "materials_v5.jsonl"), os.path.join(RAW, "materials_v6.jsonl"),
          MATERIALS, "material", "m")
    print("\n### KB_V2_DONE")


if __name__ == "__main__":
    main()
