"""
工艺/媒介库：独立通道（不混进风格索引）

为什么必须独立
--------------
v15 把 16 个工艺实体（48 条文档）直接加进风格语料，实测**两个基准都掉**：
    场景锚定 top1  55% -> 50%
    材质/光文档级  47% -> 40%
原因：工艺描述里大量出现 paper / ink / glass / silk / gold / light，
      和真正的"材质在物体上"的文档直接抢权重，把材质维度污染了。

这与"题材独立建库"是同一个结论，只是这次有数据背书：
    风格索引（谁拍的）  -> corpus_v14
    题材索引（画什么）  -> subjects_v2
    媒介索引（用什么做的）-> crafts_v1   <- 本文件

工艺清单来源：水仙的AI提示词 part3（署名使用协议，须保留出处并链接回仓库）。
下列英文描述是我们自己写的，未复制原文。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "crafts_v1.jsonl")

# (英文名, 中文名, 输出短语, [英文变体], [中文关键词])
CRAFTS = [
    ("Cyanotype Print", "蓝晒",
     "a cyanotype print, prussian blue on watercolour paper, pale sun-shielded edges",
     ["a face printed in prussian blue on rough paper, edges pale where shielded",
      "leaves laid on coated paper, the blue deepening around their shadow"],
     ["蓝晒", "普鲁士蓝", "感光纸", "铁盐"]),

    ("Copperplate Etching", "铜版画",
     "a copperplate etching, fine bitten lines, plate tone, warm laid paper",
     ["a figure drawn in bitten lines, plate tone darkening the sky",
      "a landscape in bitten cross-hatching, ink left along the plate edge"],
     ["铜版画", "蚀刻", "刻线", "凹版"]),

    ("Mezzotint", "美柔汀",
     "a mezzotint, velvety black rocked ground with lights scraped back",
     ["a portrait emerging from a velvety black ground, lights scraped soft",
      "the deepest black held in the shadows, highlights lifted with a scraper"],
     ["美柔汀", "绒黑", "铜版", "刮亮"]),

    ("Tempera Panel", "蛋彩",
     "a tempera panel, egg-bound matte colour in thin layers, gilded ground",
     ["a face built from thin matte layers, fine hatching in the shadows",
      "figures on a gold ground, colour laid flat and chalky"],
     ["蛋彩", "哑光", "金底", "罩染"]),

    ("Fresco", "湿壁画",
     "a fresco, mineral pigment on wet plaster, cracked and flaking edges",
     ["a painted figure on plaster, the surface cracking out at the edges",
      "mineral colour on a rough wall, one patch of plaster fallen away"],
     ["湿壁画", "灰泥", "矿物颜料", "剥落"]),

    ("Encaustic Wax", "蜡彩",
     "an encaustic panel, fused wax layers, scraped marks, translucent depth",
     ["wax layers fused over a portrait, scraped lines cutting to the layer below",
      "translucent wax holding colour, the surface slightly uneven"],
     ["蜡彩", "蜂蜡", "刮痕", "烫蜡"]),

    ("Scratchboard", "刮刻",
     "a scratchboard drawing, white lines scratched from a black ink ground",
     ["a face drawn in white scratches on black, hatching building the light",
      "grass and fur as scratched white lines on a black board"],
     ["刮刻", "刻痕", "黑白", "刮板"]),

    ("Risograph Print", "孔版印刷",
     "a risograph print, fluorescent inks out of register, coarse halftone",
     ["a portrait in two overprinted fluorescent inks, layers slightly off-register",
      "coarse pink and blue halftone dots, ink uneven across the sheet"],
     ["孔版印刷", "荧光油墨", "套印错位", "网点"]),

    ("Matchbox Lithograph", "火柴盒贴画",
     "a matchbox lithograph, small flat-colour print, worn rounded corners",
     ["a tiny flat-colour print on a matchbox label, corners worn round",
      "four flat inks on cheap board, registration slightly loose"],
     ["火柴盒贴画", "平版套色", "小画片"]),

    ("Stained Glass", "彩绘玻璃",
     "stained glass, leaded colour, coloured light thrown onto the floor",
     ["a tall window of leaded colour, red and blue light falling on stone",
      "figures in coloured glass divided by dark lead, backlit strongly"],
     ["彩绘玻璃", "铅条", "透光", "彩色窗"]),

    ("Kintsugi Ceramic", "金缮陶瓷",
     "kintsugi ceramic, cracked glaze rejoined with gold lacquer seams",
     ["a bowl split and rejoined with gold seams, crackle across the glaze",
      "a ceramic figure with gold-filled fractures catching a side light"],
     ["金缮", "金缝", "釉面开裂", "锔"]),

    ("Silk Embroidery", "丝绸刺绣",
     "silk embroidery, visible stitches on satin, thread sheen on raised pile",
     ["a face worked in silk thread, stitches catching light at different angles",
      "a satin ground with raised embroidery, sheen running along the folds"],
     ["刺绣", "丝线", "缎面", "针脚"]),

    ("Holographic Foil", "全息镭射",
     "holographic foil, iridescent hue shifting with the angle, rainbow diffraction",
     ["a portrait stamped in holographic foil, colour changing across the sheet",
      "rainbow diffraction over a printed surface, mirror sheen at the edges"],
     ["全息", "镭射", "虹彩", "烫金"]),

    ("Marbled Paper", "水拓画",
     "marbled paper, ink combed across a water bath then lifted on the sheet",
     ["ink combed through a water bath, the pattern lifted onto paper",
      "marbled swirls absorbed into the sheet, edges soft where the ink bled"],
     ["水拓画", "大理石纹", "晕边", "浮水"]),

    ("Gobelin Tapestry", "哥布林挂毯",
     "a gobelin tapestry, visible warp and weft, wool nap, stepped colour edges",
     ["a woven figure in wool, the warp showing between blocks of colour",
      "a hanging tapestry with visible weft and a rough pile"],
     ["挂毯", "经纬", "绒面", "织锦"]),

    ("Sugar Painting", "糖画",
     "sugar painting, caramel threads drawn on a marble slab, translucent amber",
     ["a figure drawn in one continuous caramel thread on stone",
      "amber sugar cooled hard and glossy, thin translucent edges"],
     ["糖画", "焦糖", "拉丝", "糖丝"]),
]


def main():
    rows = []
    n = 0
    for en, zh, phrase, variants, kws in CRAFTS:
        for v in variants:
            n += 1
            rows.append({
                "doc_id": f"c{n:04d}",
                "kind": "craft",
                "craft_en": en, "craft_zh": zh,
                "phrase": phrase, "kw_zh": kws,
                "description": v, "text_semantic": v,
            })
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"工艺库: {len(CRAFTS)} 个工艺 / {len(rows)} 条 -> {OUT}")
    print()
    for en, zh, phrase, _, kws in CRAFTS:
        print(f"  {zh:<8} {phrase[:66]}")
    print(f"\n### CRAFTS_V1_DONE")


if __name__ == "__main__":
    main()
