"""
语料 v15：补「工艺/媒介」轴

依据
----
src/extract_craft_vocab.py 从外部提示词库 part3 抽出 95 条「风格：」槽，
识别出 26 个工艺/材质词，对照我们语料：**缺 20 个，有 5 个**。
缺口很整齐：
    我们有 —— 中国传统媒介（水墨 / 年画 / 皮影 / 工笔 / 院体 / 手卷 / 青绿）
    我们缺 —— 西方印刷 / 摄影 / 手工媒介（蓝晒 / 铜版 / 美柔汀 / 蛋彩 / 湿壁画 /
              蜡彩 / 孔版 / 刮刻 / 金缮 / 莳绘 / 刺绣 / 全息 / 彩绘玻璃 / 水拓 / 挂毯 / 糖画）

这揭示了一个缺失的轴：
    风格 = 谁拍的（导演） + 用什么做出来的（工艺/媒介）
我们只有前者。而用户真实提示词里「风格：」槽装的正是后者。

做法
----
沿用已有模式（手卷 / 留白 / 工笔 已经是"美术类实体"），把工艺也建成实体，
director 字段填工艺名。每条 2 个具体场景，签名锚定到**材料本身**（不写"艺术感"这类通用词）。

数据来源标注：工艺清单来自 水仙的AI提示词 part3（署名使用协议，须保留出处），
但下列英文描述是我们自己写的，不是复制原文。

corpus_v14 (795) -> corpus_v15
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v15.jsonl")

# (英文名, 中文名, 签名（锚定材料/工艺）, [英文场景], 中文关键词)
CRAFTS = [
    ("Cyanotype Print", "蓝晒",
     "prussian blue print on watercolour paper, sun-exposed edges, brush-coated corners",
     ["a face printed in prussian blue on rough paper, pale at the sun-shielded edges",
      "leaves laid on coated paper, the blue darkening around their shadow"],
     ["蓝晒", "普鲁士蓝", "感光纸"]),

    ("Copperplate Etching", "铜版画",
     "bitten lines in a copper plate, plate tone, warm laid paper, inked edges",
     ["a figure drawn in fine bitten lines, plate tone darkening the sky",
      "a landscape with bitten cross-hatching, ink left in the plate edges"],
     ["铜版画", "蚀刻", "刻线"]),

    ("Mezzotint", "美柔汀",
     "velvety black ground rocked over, soft lights scraped back out of the dark",
     ["a portrait emerging from a velvety black ground, lights scraped soft",
      "a still life where the shadows hold the darkest black in the print"],
     ["美柔汀", "绒黑", "铜版"]),

    ("Tempera Panel", "蛋彩",
     "egg-bound matte colour in thin layers, fine hatching, gilded ground",
     ["a face built from thin matte colour layers, fine hatching in the shadows",
      "figures on a gold ground, colour laid flat and matte"],
     ["蛋彩", "哑光", "金底"]),

    ("Fresco", "湿壁画",
     "mineral pigment on wet plaster, cracked and flaking edges, wall texture",
     ["a painted figure on plaster, the surface cracking at the edges",
      "mineral colour on a rough wall, one patch of plaster fallen away"],
     ["湿壁画", "灰泥", "矿物颜料"]),

    ("Encaustic Wax", "蜡彩",
     "molten wax layers, scraped marks, translucent depth under the surface",
     ["wax layers fused over a portrait, scraped lines cutting to the layer below",
      "translucent wax holding colour in suspension, surface slightly uneven"],
     ["蜡彩", "蜂蜡", "刮痕"]),

    ("Scratchboard", "刮刻",
     "white lines scratched out of a black ink ground, fine parallel hatching",
     ["a face drawn in white scratches on black, hatching building the light",
      "fur and grass rendered as scratched white lines on black board"],
     ["刮刻", "刻痕", "黑白"]),

    ("Risograph Print", "孔版印刷",
     "fluorescent ink misregistration, coarse halftone dots, paper texture",
     ["a portrait in two overprinted fluorescent inks, the layers slightly off-register",
      "coarse halftone dots of pink and blue, ink uneven on the sheet"],
     ["孔版印刷", "荧光油墨", "套印错位"]),

    ("Matchbox Lithograph", "火柴盒贴画",
     "small flat-colour lithograph, worn rounded corners, coarse screen",
     ["a tiny flat-colour print on a matchbox label, corners worn round",
      "four flat inks on cheap board, registration slightly loose"],
     ["火柴盒贴画", "平版套色", "小画片"]),

    ("Stained Glass", "彩绘玻璃",
     "leaded glass, coloured light thrown onto the floor, dark lead lines",
     ["a tall window of leaded colour, red and blue light falling on stone",
      "figures in coloured glass divided by dark lead, backlit"],
     ["彩绘玻璃", "铅条", "透光"]),

    ("Kintsugi Ceramic", "金缮陶瓷",
     "cracked glaze joined with gold lacquer seams, museum side light",
     ["a bowl split and rejoined with gold seams, glaze crackle across the body",
      "a ceramic figure with gold-filled fractures catching a side light"],
     ["金缮", "金缝", "釉面开裂"]),

    ("Silk Embroidery", "丝绸刺绣",
     "visible stitches on satin, silk thread sheen, raised pile",
     ["a face worked in silk thread, stitches catching light at different angles",
      "satin ground with raised embroidery, thread sheen along the folds"],
     ["刺绣", "丝线", "缎面"]),

    ("Holographic Foil", "全息镭射",
     "iridescent foil shifting hue with the angle, rainbow diffraction, laminated sheen",
     ["a portrait stamped in holographic foil, colour changing across the sheet",
      "rainbow diffraction over a printed surface, mirror sheen"],
     ["全息", "镭射", "虹彩"]),

    ("Marbled Paper", "水拓画",
     "floating ink combed into the water, paper laid on the surface, soft absorbed edges",
     ["ink combed across a water bath, then lifted onto the sheet",
      "marbled swirls absorbing into paper, edges soft where the ink bled"],
     ["水拓画", "大理石纹", "晕边"]),

    ("Gobelin Tapestry", "哥布林挂毯",
     "visible warp and weft, wool nap, woven figure with stepped edges",
     ["a woven figure in wool, the warp showing between colour blocks",
      "a hanging tapestry with visible weft and rough pile"],
     ["挂毯", "经纬", "绒面"]),

    ("Sugar Painting", "糖画",
     "caramel threads drawn on a marble slab, translucent amber, glossy set surface",
     ["a figure drawn in one continuous caramel thread on stone",
      "amber sugar cooled hard and glossy, edges thin and translucent"],
     ["糖画", "焦糖", "拉丝"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new = []
    for en, zh, sig, scenes, kws in CRAFTS:
        for scene in scenes:
            n += 1
            desc = f"{scene}, {sig}"
            new.append({
                "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                "director": en, "director_zh": zh, "facet": "craft",
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws, "batch": "工艺轴", "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": "2.35:1", "style": "raw"},
                "prompt": f"cinematic still, {desc}, in the style of {en}, "
                          f"35mm film, --ar 2.35:1 --style raw",
            })
        # 一条视频
        n += 1
        desc = f"{scenes[0]}, {sig}, slow push-in, steady drift"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
            "director": en, "director_zh": zh, "facet": "craft", "motion": "SLOW",
            "style_tags": [x.strip() for x in sig.split(",")][:4] + ["slow"],
            "kw_zh": kws, "batch": "工艺轴", "description": desc,
            "text_semantic": f"{desc}, in the style of {en}, shot as moving footage",
            "params": {"ar": "21:9", "duration": "6s", "camera": "slow"},
            "prompt": f"cinematic video, {desc}, in the style of {en}, "
                      f"35mm film, --ar 21:9 --duration 6s --style raw",
        })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"corpus_v14 -> v15 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print(f"  新增工艺实体 {len(CRAFTS)} 个（图 {len(CRAFTS)*2} / 视频 {len(CRAFTS)}）")
    print()
    for en, zh, sig, scenes, kws in CRAFTS:
        print(f"  {zh:<8} [{en}]")
        print(f"    签名: {sig[:76]}")
    print()
    generic = ["cinematic", "stunning", "beautiful", "artistic", "creative", "8k"]
    hits = [(d["doc_id"], g) for d in new for g in generic if g in d["description"].lower()]
    print(f"通用质量词自检: {'无' if not hits else hits}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V15_DONE")


if __name__ == "__main__":
    main()
