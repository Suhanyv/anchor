"""
语料 v2：多面签名（multi-facet）

问题（真实 query 暴露）：每位导演只有一个固定签名。
  黑泽明 1950s 是黑白雨戏，1980s 是浓烈色彩（乱/影武者）。
  用户说"色彩鲜艳、有秩序又有混乱"，而语料只写了 monochrome -> Q3 排到 37 名。

做法：
  * 保留原有 base facet 不动（357 条）
  * 对风格剧变的导演追加 1 个 extra facet（每位 +3 条）
  * 文档带 facet 字段；query 按 facet 生成，relevant 只指该 facet 的文档
    -> 这样才真正测"能不能区分同一个导演的不同面"

输出：corpus_v2.jsonl / queries_v2b.jsonl
"""
import json
import os
import random

ROOT = r"F:\llm"
BASE_CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
OUT_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl")
OUT_QUERIES = os.path.join(ROOT, "data", "raw", "queries_v2b.jsonl")

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_queries_v2 import T_BOTH, T_STYLE, T_NAME, TPL_INDEX  # noqa: E402

# en: (facet_id, 英文签名, [3 个场景], [3 个中文词])
EXTRA = {
    "Akira Kurosawa": ("color_1980s",
        "vivid saturated colour, ordered chaos, massed banners, theatrical symmetry, painted skies",
        ["armies in crimson banners across a windswept hillside",
         "a lone figure on a ridge above a battlefield in blazing colour",
         "a vast hall of gold and red with massed figures"],
        ["浓烈色彩", "秩序与混乱", "千军万马"]),
    "Stanley Kubrick": ("bw_early",
        "stark black-and-white street photography, wide-angle urban grit, hard flash, boxing-ring sweat",
        ["a boxer in a smoky black-and-white ring",
         "a rain-slicked city street in high-contrast monochrome",
         "a crowded pool hall under bare bulbs"],
        ["黑白粗粝", "街头摄影", "硬闪光"]),
    "Martin Scorsese": ("bw_ring",
        "high-contrast black-and-white, slow-motion boxing, sweat and flashbulbs, documentary immediacy",
        ["a boxer's face in monochrome under ring lights",
         "flashbulbs bursting in a smoky black-and-white arena",
         "a monochrome street crowd shot handheld"],
        ["黑白拳击", "闪光灯", "纪实"]),
    "Francis Ford Coppola": ("expressionist",
        "expressionist saturated colour, painted backdrops, theatrical shadow, dream-opera staging",
        ["a painted stage set in saturated crimson and shadow",
         "a figure before an expressionist painted sky",
         "a theatre curtain of red velvet under hard spotlights"],
        ["表现主义", "舞台感", "浓红"]),
    "Ingmar Bergman": ("color_crimson",
        "saturated crimson interiors, warm summer light, luminous faces in colour, intimate silence",
        ["a room entirely in deep crimson with figures in white",
         "a sunlit summer meadow with figures running",
         "a warm candle-lit interior with searching faces"],
        ["猩红", "夏日暖光", "亲密"]),
    "Federico Fellini": ("neorealist",
        "monochrome neorealist street, postwar rubble, plain faces, documentary plainness",
        ["a black-and-white postwar street with rubble",
         "a shabby provincial piazza in monochrome",
         "plain faces in a crowded monochrome café"],
        ["黑白新写实", "战后废墟", "朴素"]),
    "Michelangelo Antonioni": ("psychedelic",
        "vivid industrial colour, psychedelic 1960s palette, alienated modern surfaces, saturated abstraction",
        ["a vivid green lawn with a giant painted wall",
         "a figure against a saturated abstract industrial facade",
         "a psychedelic desert landscape in hard colour"],
        ["迷幻色彩", "现代性", "抽象"]),
    "Zhang Yimou": ("rural_realism",
        "earthy rural naturalism, dusty daylight, unglamorous faces, documentary plainness",
        ["a dusty village lane in flat natural light",
         "a farmer walking a dirt road at noon",
         "a plain brick courtyard with laundry"],
        ["乡土写实", "尘土地光", "朴素"]),
    "Wong Kar-wai": ("period_elegance",
        "warm tungsten period interiors, elegant 1930s decor, slow sumptuous detail, amber lamplight",
        ["a 1930s interior in warm amber lamplight",
         "a figure in a tailored suit by a lacquered screen",
         "a slow shot of hands over a mahogany table"],
        ["民国质感", "钨丝暖光", "考究"]),
    "Steven Spielberg": ("desaturated_war",
        "desaturated historical realism, handheld war footage, grey-green palette, documentary grain",
        ["soldiers wading through grey surf handheld",
         "a grey-green bombed street in documentary grain",
         "a desaturated field under overcast sky"],
        ["灰绿写实", "手持战争", "纪实颗粒"]),
    "Ridley Scott": ("sunbaked_epic",
        "sun-baked historical epic, dust and gold, vast desert scale, warm amber haze",
        ["a Roman column on a sunbaked dust plain",
         "a crowd in the shadow of a vast desert monument",
         "wheat fields under a hazy amber sun"],
        ["烈日史诗", "尘金", "古罗马"]),
    "James Cameron": ("tropical_daylight",
        "sunlit tropical ocean, warm daylight adventure, clear turquoise water, practical scale",
        ["a figure diving through turquoise sunlit water",
         "a tropical village at warm midday",
         "a ship on a bright open ocean"],
        ["热带日光", "碧蓝海水", "冒险"]),
    "David Lynch": ("sunlit_normal",
        "sun-bleached Americana highway, warm golden normality, wide clean daylight, small-town stillness",
        ["a sunlit small-town main street with a classic car",
         "a golden wheat field beside a highway",
         "a bright diner interior in warm daylight"],
        ["日光美国", "小镇日常", "金调"]),
    "David Cronenberg": ("cold_period",
        "cold literary interiors, muted period palette, grey daylight, restrained clinical austerity",
        ["a grey period study with a single desk",
         "a muted cold apartment in winter light",
         "a clinical corridor in pale grey"],
        ["冷灰", "文学感", "克制"]),
    "Terrence Malick": ("digital_montage",
        "fractured digital montage, fisheye wide-angle intimacy, drifting handheld, impressionistic light",
        ["a fisheye view of a child running through a house",
         "drifting handheld shots of hands in sunlight",
         "a fragmented montage of water and light"],
        ["碎片剪辑", "鱼眼", "印象光"]),
    "Paul Thomas Anderson": ("formal_period",
        "restrained formal period drama, muted palette, precise symmetrical interiors, controlled stillness",
        ["a formal muted 1950s interior with two figures",
         "a symmetrical corridor in pale muted tones",
         "a still shot of a tailored dress in warm grey"],
        ["克制", "对称室内", "哑色"]),
    "Christopher Nolan": ("dust_epic",
        "dust-choked desert scale, sun-bleached sky, vast empty space, cold blue-grey distance",
        ["figures on a dust-choked beach under a pale sky",
         "a frozen white expanse with tiny figures",
         "a dusty desert horizon under cold blue light"],
        ["尘霾", "苍茫", "冷蓝远景"]),
    "Denis Villeneuve": ("intimate_cold",
        "intimate muted domestic tension, cold blue interior light, subdued handheld, quiet dread",
        ["two figures in a cold blue kitchen in silence",
         "a grey suburban house interior in flat light",
         "a muted close-up of a face by a rainy window"],
        ["冷蓝室内", "静默张力", "克制"]),
    "Jean-Luc Godard": ("late_collage",
        "late video-essay collage, layered text and image, saturated digital fragments, self-aware montage",
        ["a collage of overlapping text and saturated video fragments",
         "a figure against layered projections of colour",
         "a screen split between film footage and typography"],
        ["影像论文", "文字拼贴", "分层"]),
    "Lars von Trier": ("formal_symmetry",
        "formal symmetrical staging, muted earth tones, slow stately framing, painterly stillness",
        ["a symmetrical muted interior with a single figure",
         "a slow wide shot of a misty earth-toned field",
         "a painterly still life in low warm light"],
        ["对称", "哑色", "绘画感"]),
    "Michael Haneke": ("luminous_bw",
        "luminous black-and-white, austere village light, precise wide framing, moral coldness",
        ["a black-and-white village street with children",
         "a luminous monochrome interior with a single figure",
         "a wide monochrome field under a pale sky"],
        ["黑白", "冷峻村庄", "精准构图"]),
    "Bong Joon-ho": ("cold_industrial",
        "cold snowy industrial scale, muted blue-grey, cramped mechanical interiors, bleak snow",
        ["a snowbound train exterior in blue-grey",
         "a cramped grey mechanical corridor",
         "figures in a frozen desaturated landscape"],
        ["雪冷", "工业机械", "蓝灰"]),
    "Park Chan-wook": ("romantic_period",
        "lush romantic period colour, warm autumnal palette, poised symmetry, luxurious interiors",
        ["a sumptuous period interior in warm autumn tones",
         "a figure by a rain-streaked window in gold light",
         "a formal garden in rich muted colour"],
        ["唯美年代", "秋色", "考究"]),
    "Hayao Miyazaki": ("industrial_dystopia",
        "industrial smog, mechanical detail, cluttered machines, dystopian air and rust",
        ["a rusted flying machine in hazy smog",
         "a cluttered workshop of gears and pipes",
         "a toxic forest under a sickly sky"],
        ["工业雾霾", "机械细节", "末世"]),
    "Andrei Tarkovsky": ("sculpted_monochrome",
        "luminous monochrome, sculpted light and shadow, austere faces, war-torn ash",
        ["a pale monochrome face lit from one side",
         "a burnt birch forest in monochrome",
         "a column of light in a dark ruined interior"],
        ["黑白雕塑光", "战争灰烬", "脸"]),
    "Robert Bresson": ("ecstatic_face",
        "luminous black-and-white close-ups, spiritual ecstasy, plain faces, transcendent stillness",
        ["an ecstatic face in luminous monochrome close-up",
         "a plain young face against a pale wall",
         "hands clasped in prayer in soft monochrome"],
        ["圣像脸", "黑白", "魂魄"]),
    "Wim Wenders": ("warm_documentary",
        "warm saturated documentary colour, sunlit courtyards, rich textile texture, lived-in rooms",
        ["a sunlit courtyard full of musicians",
         "a warm cluttered room with patterned fabrics",
         "a vibrant street crowd in afternoon light"],
        ["温暖纪录", "庭院", "生活质感"]),
    "Ken Loach": ("golden_rural",
        "warm golden rural light, hillside naturalism, working hands, gentle documentary",
        ["a boy running down a golden hillside",
         "a greyhound in warm afternoon light",
         "a working kitchen in low golden sun"],
        ["金调乡村", "山丘", "手的细节"]),
    "Jia Zhangke": ("digital_spectacle",
        "saturated digital spectacle, neon night China, retro-pop colour, wider-screen energy",
        ["a neon-lit street in a Chinese city at night",
         "figures in retro-pop saturated colour",
         "a wide shot of a transformed skyline at dusk"],
        ["霓虹国潮", "数码饱和", "时代感"]),
    "Hou Hsiao-hsien": ("sumptuous_period",
        "sumptuous period colour, candlelit interiors, silk texture, slow tactile detail",
        ["a candlelit Tang interior with silk hangings",
         "a figure in flowing robes in golden haze",
         "a slow shot of hands on an antique table"],
        ["唐代考究", "烛光", "丝质"]),
    "Ang Lee": ("wuxia_color",
        "vivid wuxia wirework, luminous green bamboo, weightless movement, saturated martial grace",
        ["a figure leaping across a luminous green bamboo forest",
         "a duel on a rooftop against a painted sky",
         "flowing robes in saturated emerald light"],
        ["武侠青绿", "飘逸", "竹林"]),
    "Chen Kaige": ("stark_rural",
        "stark rural black-and-white, harsh naturalism, barren earth, plain faces",
        ["a barren yellow earth plateau in monochrome",
         "a plain peasant face in harsh daylight",
         "a dusty monochrome village lane"],
        ["黑白苍黄", "土地", "朴素"]),
    "Clint Eastwood": ("muted_war",
        "muted desaturated war epic, grey surf, cold overcast palette, restrained scale",
        ["soldiers in grey surf under an overcast sky",
         "a desaturated beach under cold cloud",
         "grey silhouettes on a ridge"],
        ["灰调战争", "阴天", "克制"]),
    "George Miller": ("pastel_stylised",
        "pastel comic-book colour, saturated stylisation, painted sky, graphic flatness",
        ["a pastel painted sky over a stylised city",
         "figures in saturated comic-book colour",
         "a graphic flat landscape in candy tones"],
        ["粉彩漫画", "平面化", "风格化"]),
    "Guillermo del Toro": ("cold_industrial",
        "cold industrial grey, wet concrete, muted teal machinery, melancholy wet surfaces",
        ["a wet concrete corridor in cold teal",
         "a grey industrial room with a single lamp",
         "rain on a metal railing at night"],
        ["冷工业", "青灰混凝土", "潮湿"]),
    "Woody Allen": ("bw_european",
        "luminous black-and-white, elegant European cityscape, romantic wide shots, timeless monochrome",
        ["a black-and-white bridge at dusk",
         "a couple walking a monochrome boulevard",
         "a luminous monochrome skyline"],
        ["黑白欧洲", "浪漫", "桥"]),
    "Spike Lee": ("stark_bw",
        "stark black-and-white documentary, hard contrast, direct-address faces, historical gravity",
        ["a hard-contrast black-and-white crowd",
         "a monochrome close-up of a face speaking to camera",
         "a monochrome street corner in harsh light"],
        ["黑白硬对比", "直面镜头", "历史感"]),
    "Wes Anderson": ("winter_monochrome",
        "muted monochrome palette, precise symmetry in grey and black, deadpan formality, snow",
        ["a symmetrical grey hotel interior in snow light",
         "a monochrome family lineup against a pale wall",
         "a precise black-and-white diorama of a room"],
        ["灰调对称", "冷面", "雪"]),
    "Rainer Werner Fassbinder": ("warm_melodrama",
        "warm saturated melodrama, lush 1950s decor, mirrored glamour, operatic colour",
        ["a lush 1950s interior in warm saturated colour",
         "a woman in a mirrored room of gold light",
         "a glamorous staircase in deep warm tones"],
        ["暖调情节剧", "镜像", "50年代"]),
    "Pier Paolo Pasolini": ("vivid_myth",
        "vivid mythic colour, saturated earth tones, ritual nudity, painterly tableau",
        ["a saturated earth-toned ritual tableau",
         "a crowd in vivid painted costumes",
         "a mythic desert in rich ochre"],
        ["浓彩神话", "壁画感", "仪式"]),
}

PER_FACET_SCENES = 3


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    base = load(BASE_CORPUS)
    # 按导演收集 base 文档
    by_dir = {}
    for d in base:
        by_dir.setdefault(d["director"], []).append(d)

    docs, queries = [], []
    n = 0
    rnd = random.Random(20260121)

    for en, base_docs in by_dir.items():
        zh = base_docs[0]["director_zh"]
        country = base_docs[0]["country"]
        era = base_docs[0]["era"]

        # --- facet: base（沿用原文档，补 facet 字段）
        base_ids = []
        for d in base_docs:
            n += 1
            nd = dict(d)
            nd["facet"] = "base"
            nd["doc_id"] = f"d{n:04d}"
            base_ids.append(nd["doc_id"])
            docs.append(nd)

        # --- facet: extra（若有）
        extra_ids, extra_kw = [], None
        if en in EXTRA:
            fid, sig, scenes, kws = EXTRA[en]
            extra_kw = kws
            for si, scene in enumerate(scenes[:PER_FACET_SCENES]):
                n += 1
                is_video = (si == 2)
                ar = "21:9" if is_video else "2.35:1"
                desc = f"{scene}, {sig}"
                tail = "--v 6 --duration 5s" if is_video else "--v 6 --style raw"
                kind = "video" if is_video else "still"
                nd = {
                    "doc_id": f"d{n:04d}",
                    "domain": "prompt_video" if is_video else "prompt_image",
                    "lang": "en", "director": en, "director_zh": zh,
                    "country": country, "era": era,
                    "facet": fid,
                    "style_tags": [x.strip() for x in sig.split(",")][:6],
                    "kw_zh": kws,
                    "description": desc,
                    "text_semantic": f"{desc}, in the style of {en}",
                    "params": {"ar": ar, "style": "raw"},
                    "prompt": f"cinematic {kind}, {desc}, in the style of {en}, 35mm film, --ar {ar} {tail}",
                }
                extra_ids.append(nd["doc_id"])
                docs.append(nd)

        # --- queries：每个 facet 各出几条
        facets = [("base", base_docs[0]["kw_zh"], base_ids)]
        if extra_ids:
            facets.append((EXTRA[en][0], extra_kw, extra_ids))

        for facet, kws, ids in facets:
            for kind, tpl in [("both", rnd.choice(T_BOTH)),
                              ("style", rnd.choice(T_STYLE)),
                              ("name", rnd.choice(T_NAME))]:
                n_q = rnd.choice([2, 3, 3])
                kw = "、".join(rnd.sample(kws, min(n_q, len(kws))))
                queries.append({
                    "query_id": f"q{len(queries)+1:05d}",
                    "query": tpl.format(kw=kw, zh=zh),
                    "lang": "zh", "domain": "prompt_image",
                    "relevant": ids,                    # 只指该 facet 的文档（更严格）
                    "target_director": en, "facet": facet,
                    "query_kind": kind,
                    "template_id": f"{kind}:{TPL_INDEX[tpl]}",
                    "template": tpl,
                })

    with open(OUT_CORPUS, "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(OUT_QUERIES, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"directors      : {len(by_dir)}")
    print(f"extra facets   : {len(EXTRA)}")
    print(f"docs           : {len(docs)}  (base {len(base)} + extra {len(docs)-len(base)})")
    print(f"queries        : {len(queries)}")
    print(f"  by kind      : {dict(Counter(q['query_kind'] for q in queries))}")
    print(f"  by facet     : {dict(Counter(q['facet'] for q in queries))}")
    print(f"  templates    : {len(set(q['template_id'] for q in queries))}")
    print(f"\n-> {OUT_CORPUS}\n-> {OUT_QUERIES}")
    print("\n黑泽明 facets:")
    for d in docs:
        if d["director"] == "Akira Kurosawa":
            print(f"  [{d['facet']:<12}] {d['text_semantic'][:95]}")
    print("\n### CORPUS_V2_DONE")


if __name__ == "__main__":
    main()
