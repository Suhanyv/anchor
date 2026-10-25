"""
知识库扩充 v1：给三个零样本索引各补一批中国传统媒介与器物

为什么走这条路
--------------
今天验证过的成本差：
    零样本索引（题材/工艺/材质）  加数据立刻生效，不重训  <- 「竹简」7 行就修好了
    风格语料（导演/流派）        要重训，而且会挤掉老维度（c30 就是例子）

所以先补便宜的。而且方向选**中国传统媒介**——使用场景在那里，库也最薄：
    风格语料里有敦煌/唐卡/波斯/伊斯兰，但中国自己的书写与器物系统几乎是空的。

补什么
------
    工艺 8 个   拓片 / 篆刻 / 漆器 / 螺钿 / 青花瓷 / 剪纸 / 木版年画 / 竹编
    题材 8 个   团扇 / 灯笼 / 屏风 / 案几 / 荷塘 / 雪中庭院 / 山寺 / 渡口
    材质 6 个   宣纸 / 大漆 / 青瓷釉 / 竹 / 铜 / 亚麻

字段按现有文件的 schema 自动镜像，不手写猜字段名。

产物
----
    data/raw/subjects_v6.jsonl    (47 -> 55+)
    data/raw/crafts_v4.jsonl      (32 -> 48+)
    data/raw/materials_v5.jsonl   (109 -> 121+)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# ---- 工艺（媒介/技艺）：英文名, 中文名, 输出短语, 关键词, 描述变体 ----
CRAFTS = [
    ("Rubbing", "拓片", "ink rubbed over paper laid on carved stone, the incised lines left white",
     ["拓片", "拓本", "碑刻", "拓印", "凹凸", "石碑", "墨扑", "字口"],
     ["ink pressed over paper laid on a carved stone stele, the incised characters left white",
      "a rubbing lifted off a stone tablet, the paper cockled where it pressed into the cuts",
      "the ink pad tamped over the paper on stone, only the recessed lines resisting"]),

    ("Seal Carving", "篆刻", "a carved stone seal pressed into red paste, the cut lines crisp",
     ["篆刻", "印章", "封泥", "朱红印泥", "边款", "印石", "刀刻", "印面"],
     ["a carved stone seal pressed into red seal paste, the characters recessed below the face",
      "the seal lifted away leaving a square red impression stamped on paper",
      "an engraving knife cutting a character into the base of a seal stone"]),

    ("Lacquerware", "漆器", "urushi lacquer brushed onto a wooden core, the film reading wet even when cured",
     ["漆器", "大漆", "漆面", "罩漆", "漆盒", "生漆"],
     ["urushi lacquer brushed onto a wooden core, the cured film still reading wet",
      "a lacquered box with dust settling on the last brushed coat",
      "worn lacquer on a tray showing the red ground under the black where hands have been"]),

    ("Mother-of-Pearl Inlay", "螺钿", "shell inlay set into dark lacquer, each piece catching a different colour",
     ["螺钿", "贝壳镶嵌", "夜光贝", "嵌片"],
     ["shell cut into shapes and set into black lacquer, colour shifting with the angle",
      "the inlay catching violet and green as the light moves",
      "a lacquer panel with shell fragments still half-set"]),

    ("Blue-and-White Porcelain", "青花瓷", "cobalt painted under a clear glaze, blue sinking into the white",
     ["青花", "钴蓝", "釉下彩", "瓷瓶"],
     ["cobalt lines painted under glaze, the blue slightly diffused by the white",
      "a blue-and-white vase, the porcelain wall thin enough to glow",
      "the brush loaded with cobalt touching damp clay body"]),

    ("Papercut", "剪纸", "paper cut into a connected lattice, the negative space doing the drawing",
     ["剪纸", "窗花", "镂空", "红纸"],
     ["red paper cut into a repeating lattice, the holes shaping the image",
      "a window flower pasted on glass, light passing through the cut",
      "scissors turning a folded square without a drawn line"]),

    ("Woodblock New-Year Print", "木版年画", "woodblock printed in flat colour blocks, keyline printed last",
     ["年画", "木版", "套色", "门神"],
     ["flat colour blocks printed in register, the black keyline laid last",
      "a door god printed in vermilion and green, registration slightly off",
      "the block inked and pressed by hand, paper laid over it"]),

    ("Bamboo Weaving", "竹编", "bamboo split into strips and woven, the pattern readable in the over-under",
     ["竹编", "篾条", "编织", "竹器"],
     ["bamboo split into even strips and woven over-under",
      "a woven bamboo basket, the strips polished by use",
      "hands splitting a bamboo culm into strips of equal width"]),
]

# ---- 题材（可被画出来的物件/场景） ----
SUBJECTS = [
    ("Round Fan", "团扇", "a round silk fan held at an angle, the handle plain",
     ["团扇", "纨扇", "扇面"],
     ["a round silk fan held at an angle, the painted face half turned",
      "a fan laid on a table, the silk slightly slack in the frame"]),

    ("Lantern", "灯笼", "a paper lantern lit from inside, the ribs showing through",
     ["灯笼", "宫灯", "纸灯", "灯影"],
     ["a paper lantern lit from within, the bamboo ribs visible as dark lines",
      "row of lanterns under an eave, each one slightly different in glow"]),

    ("Folding Screen", "屏风", "a folding screen of hinged panels dividing the room, each panel painted",
     ["屏风", "插屏", "隔断", "折叠", "屏面", "多扇"],
     ["a folding screen of hinged panels standing across a room, each panel painted on silk",
      "the hinged screen half folded, its painted figures cut by the panel edges",
      "seen from behind the screen, figures moving as shadows on the paper panels"]),

    ("Low Table", "案几", "a low wooden table with an object set on it, the surface worn pale",
     ["案几", "矮桌", "书案"],
     ["a low wooden table, the surface worn pale where hands have rested",
      "an object set alone on a low table, the rest of the frame empty"]),

    ("Lotus Pond", "荷塘", "a pond of lotus leaves, water moving under them",
     ["荷塘", "荷花", "莲叶"],
     ["lotus leaves standing above still water, the undersides pale",
      "a pond surface broken by stems, light scattered on the water"]),

    ("Snow Courtyard", "雪中庭院", "a courtyard under fresh snow, only the paths walked",
     ["雪", "庭院", "雪地", "脚印"],
     ["a walled courtyard under fresh snow, one path of footprints",
      "snow gathering on a tile roof, the ridge line drawn in white"]),

    ("Mountain Temple", "山寺", "a temple roof among trees on a slope, mist below it",
     ["寺庙", "山寺", "殿顶", "钟"],
     ["a temple roof among pines on a slope, mist filling the valley below",
      "stone steps climbing to a gate, the building mostly hidden"]),

    ("Ferry Crossing", "渡口", "a small ferry at a river landing, the bank muddy and worn",
     ["渡口", "渡船", "码头", "河岸"],
     ["a ferry tied at a river landing, the bank worn to mud",
      "a boat crossing in mist, the far bank barely readable"]),
]

# ---- 材质（质感/光） ----
MATERIALS = [
    ("Xuan Paper", "宣纸", "xuan paper with visible fibres, ink bleeding slightly at the wet edge",
     ["宣纸", "生宣", "纸纤维", "洇墨"],
     ["xuan paper with visible fibres, ink wicking out at the wet edge",
      "raw paper cockling where the wash went down",
      "the sheet held up to the light, fibres uneven across it"]),

    ("Lacquer Surface", "大漆", "lacquer so deep the surface reads wet even when dry",
     ["大漆", "漆面", "光泽", "深"],
     ["lacquer so deep it reads wet even when dry",
      "a lacquer surface reflecting a single window, everything else black",
      "dust caught in the last coat before it set"]),

    ("Celadon Glaze", "青瓷釉", "celadon glaze pooling pale green at the foot, crackling across the body",
     ["青瓷", "釉", "开片", "青绿"],
     ["celadon pooling pale green where the glaze ran thick",
      "a crackle network across a pale green glaze",
      "the glaze thin at the rim so the body shows through"]),

    ("Bamboo", "竹", "bamboo with a matte green skin and pale nodes, light along the culm",
     ["竹", "竹节", "竹皮", "青"],
     ["a bamboo culm, matte green skin, the node a pale ring",
      "split bamboo strips, pale inner fibre and a green outer face"]),

    ("Bronze", "铜", "cast bronze gone brown-black, verdigris crusted in the cut recesses of vessels",
     ["铜", "青铜", "青铜器", "绿锈", "包浆", "鼎", "兵刃"],
     ["a cast bronze vessel gone brown-black, verdigris crusted where water collected",
      "the raised ornament of a bronze weapon polished by handling, the cut lines green",
      "patina breaking into pale green crust on the shoulder of a bronze cauldron"]),

    ("Linen", "亚麻", "coarse linen with slubs in the weave, creased where it folds",
     ["亚麻", "粗布", "织纹", "褶皱"],
     ["coarse linen, slubs breaking the weave, creased at the fold",
      "unbleached linen held against the light, threads uneven"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def name_keys(sample):
    """从现有行里认出 name_en / name_zh 字段名，不猜。"""
    en = next(k for k in sample if k.endswith("_en"))
    zh = next(k for k in sample if k.endswith("_zh"))
    return en, zh


def build(src, out, entries, kind, prefix, extra_type=None):
    rows = load(src)
    sample = rows[0]
    k_en, k_zh = name_keys(sample)
    base_n = len(rows)
    n = base_n
    added = []
    for en, zh, phrase, kw, variants in entries:
        for v in variants:
            n += 1
            row = {
                "doc_id": f"{prefix}{n:04d}",
                "kind": kind,
                k_en: en, k_zh: zh,
                "phrase": phrase,
                "kw_zh": kw,
                "description": v,
                # 零样本索引的中文锚点（已验证的做法）
                "text_semantic": f"{v}，{zh}，{'、'.join(kw)}",
            }
            if extra_type and "type" in sample:
                row["type"] = extra_type
            added.append(row)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(out):<24} {base_n} -> {len(rows)+len(added)}"
          f"  (+{len(added)} 条 / {len(entries)} 项)")
    return added


def main():
    print("=== 扩充三个零样本索引 ===")
    build(os.path.join(RAW, "subjects_v5.jsonl"),
          os.path.join(RAW, "subjects_v6.jsonl"),
          SUBJECTS, "subject", "s", extra_type="object")
    build(os.path.join(RAW, "crafts_v3.jsonl"),
          os.path.join(RAW, "crafts_v4.jsonl"),
          CRAFTS, "craft", "c")
    build(os.path.join(RAW, "materials_v4.jsonl"),
          os.path.join(RAW, "materials_v5.jsonl"),
          MATERIALS, "material", "m")

    print("\n=== 自检：新条目都有中文锚点 ===")
    for f in ("subjects_v6", "crafts_v4", "materials_v5"):
        rows = load(os.path.join(RAW, f + ".jsonl"))
        ok = all("，" in r["text_semantic"] for r in rows)
        print(f"  {f:<16} {len(rows):>4} 条  全部含中文锚点: {ok}")

    print("\n### KB_V1_DONE")


if __name__ == "__main__":
    main()
