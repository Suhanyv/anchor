"""
语料 v21：补 25 个最常被问到的视觉传统

为什么要补
----------
查重发现一个尴尬的事实：我们的 148 个实体里，
**巴洛克、印象派、立体主义、超现实主义、赛博朋克、黑色电影一个都没有。**
这些是中文 AIGC 场景里最常被点名的词，现在问「巴洛克的光」「印象派的色彩」查不到任何东西。

选谁（按中文使用频率）
----------------------
西方美术流派  巴洛克 / 印象派 / 后印象派 / 立体主义 / 超现实主义 / 野兽派 / 表现主义
设计风格      包豪斯 / 构成主义 / 波普 / 极简主义 / 欧普
数字亚文化    赛博朋克 / 蒸汽波 / 合成器浪潮 / 像素艺术 / Y2K / 梦核 / 暗黑学院 / 废土
电影风格      黑色电影
东方与摄影    琳派 / 新版画 / 莫卧儿细密画 / 伊斯兰几何 / 宝丽来

每个实体 5 条（3 base + 1 facet + 1 video）。
描述自己写；术语取自公开的艺术史与设计通名，不依赖任何单一来源。

corpus_v20 (910) -> corpus_v21
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v20.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v21.jsonl")

# (中文, 英文, 国别, 年代, 标签, 视频运镜, 时长, [(类型, 描述, kw), ...])
E = [
    ("巴洛克", "Baroque", "EU", "1600-1750",
     ["chiaroscuro", "deep crushed shadow", "gold ornament", "diagonal composition"],
     "the camera holds a dark interior while a single light source rakes across it", "5s",
     [("image", "a figure emerging from deep shadow, one shaft of light on the raised hand", ["强光", "深影", "举起的手"]),
      ("image", "gilded ornament curling over a dark cornice, almost black around it", ["金色装饰", "檐口", "暗部"]),
      ("image", "a body twisting on a diagonal, cloth thrown into heavy folds", ["对角线", "扭转的身体", "厚重布褶"]),
      ("facet", "image", "a still life with a split skin, light falling across the table edge", ["静物", "果皮", "桌沿光"]),
      ("video", "a dark room where one candle gutters and shadow shifts across a face", ["烛光", "影子移动", "暗房"])]),

    ("印象派", "Impressionism", "FR", "1870s-1880s",
     ["broken brushwork", "outdoor light", "blue-violet shadow", "no hard contour"],
     "the camera drifts slowly as light changes across the same surface", "4s",
     [("image", "a river bank in open daylight, broken strokes, violet in the shadows", ["河岸", "碎笔触", "紫影"]),
      ("image", "a crowd on a sunlit street, faces unreadable, colour vibrating", ["阳光街道", "人群", "脸部模糊"]),
      ("image", "water lilies floating, no outline anywhere, only patches", ["睡莲", "无轮廓", "色块"]),
      ("facet", "image", "a haystack at noon, colour varying across its surface", ["草垛", "正午", "表面变色"]),
      ("video", "the same view under shifting light, everything staying soft", ["光变化", "柔边", "静止视点"])]),

    ("后印象派", "Post-Impressionism", "FR", "1886-1905",
     ["heavy visible strokes", "unnatural colour", "flattened depth", "strong rhythm"],
     "the camera holds still while the painted surface seems to pulse", "4s",
     [("image", "a night sky over a village, strokes curling, stars swollen", ["夜空", "卷曲笔触", "星"]),
      ("image", "a mountain under a violet sky, depth flattened into bands", ["山", "紫色天空", "压平成层"]),
      ("image", "figures in a field, colour used against nature", ["田野", "人物", "非自然色"]),
      ("facet", "image", "a chair and a pipe seen from a high corner, floor tilted", ["椅子", "烟斗", "倾斜地面"]),
      ("video", "the camera pushes into the surface until the strokes dominate", ["推近", "笔触放大"])]),

    ("立体主义", "Cubism", "FR", "1907-1920s",
     ["multiple viewpoints", "faceted planes", "muted brown grey", "collage fragments"],
     "the camera orbits a still object and the planes fail to reconcile", "4s",
     [("image", "a face broken into planes seen from two angles at once", ["多视点", "碎裂面", "侧脸与正面"]),
      ("image", "a guitar and table cut into flat angular facets", ["吉他", "桌子", "几何面"]),
      ("image", "a figure in brown and grey, edges doubled and displaced", ["褐灰", "边缘错位"]),
      ("facet", "image", "newspaper fragments pasted into a flat brown field", ["报纸碎片", "拼贴", "平褐"]),
      ("video", "the camera slides across facets, no single view holding", ["横移", "多视角", "无法统一"])]),

    ("超现实主义", "Surrealism", "EU", "1924-1960s",
     ["impossible scale", "dream logic", "photographic detail", "empty horizon"],
     "the camera holds a still frame in which one thing slowly does not make sense", "6s",
     [("image", "a clock draped over a branch, marshland behind, nothing dripping", ["软钟", "树枝", "沼泽"]),
      ("image", "an empty plain with one door standing free, shadows long", ["荒原", "独立门", "长影"]),
      ("image", "a room where the ceiling is water and furniture hangs", ["天花板是水", "倒置家具"]),
      ("facet", "image", "two faces fused into one volume, both clearly detailed", ["双脸融合", "清晰细节"]),
      ("video", "a still frame where a shadow detaches from its object", ["静止", "影子脱离"])]),

    ("野兽派", "Fauvism", "FR", "1905-1908",
     ["unmixed colour", "flat areas", "no shading", "outline optional"],
     "the camera holds a flat coloured field, only edges vibrating", "3s",
     [("image", "a woman's face painted in orange and green, no shading at all", ["橙绿脸", "无明暗"]),
      ("image", "boats on water in raw red and blue, drawn plainly", ["红蓝船", "水面", "简笔"]),
      ("image", "a window open onto pure colour, interior in flat patches", ["窗", "纯色", "平涂"]),
      ("facet", "image", "a dancer cut from flat crimson against flat blue", ["舞者", "平红", "平蓝"]),
      ("video", "colour fields held still, no gradient moving", ["纯色", "静止"])]),

    ("表现主义", "Expressionism", "DE", "1910s-1920s",
     ["distorted forms", "clashing dark colour", "angular line", "crowded frame"],
     "the camera pushes in while the shapes refuse to settle", "5s",
     [("image", "a street of leaning buildings, windows like wounds, acid green light", ["倾斜建筑", "尖窗", "酸绿"]),
      ("image", "a face stretched vertically, mouth too wide, dark outlines", ["拉伸的脸", "宽嘴", "黑边"]),
      ("image", "figures crowded at a table, shoulders squared, colour clashing", ["挤在桌边", "方肩", "冲突色"]),
      ("facet", "image", "a staircase broken into jagged steps in black and ochre", ["锯齿楼梯", "黑与土黄"]),
      ("video", "the frame tilts and the architecture leans further", ["倾斜", "压迫感"])]),

    ("包豪斯", "Bauhaus", "DE", "1919-1933",
     ["primary colour", "geometric", "asymmetric balance", "no ornament"],
     "the camera holds a geometric frame while one element rotates", "4s",
     [("image", "red square, yellow circle, blue triangle on off-white, no texture", ["三原色", "几何", "无质感"]),
      ("image", "a tubular steel chair against a bare wall, shadow hard", ["钢管椅", "白墙", "硬影"]),
      ("image", "a staircase of pure geometry, diagonals meeting cleanly", ["几何楼梯", "对角线"]),
      ("facet", "image", "a poster grid of circles and bars, asymmetric and balanced", ["海报网格", "圆与条", "不对称平衡"]),
      ("video", "one geometric element rotates while the rest hold", ["旋转", "静止其余"])]),

    ("构成主义", "Constructivism", "RU", "1915-1930s",
     ["red black white", "diagonal axis", "industrial type", "photographic fragments"],
     "the camera tracks along a diagonal as elements slide past", "4s",
     [("image", "red and black bars cutting a white field on a hard diagonal", ["红黑条", "白底", "对角线"]),
      ("image", "a worker's silhouette merged with machinery, seen from below", ["工人剪影", "机器", "仰视"]),
      ("image", "heavy sans-serif type stacked at an angle", ["粗体字", "倾斜排版"]),
      ("facet", "image", "a photograph cut into a red geometric field", ["照片", "切入红块"]),
      ("video", "elements slide along the diagonal, no easing", ["滑动", "对角", "匀速"])]),

    ("波普艺术", "Pop Art", "US", "1955-1970s",
     ["halftone dots", "flat commercial colour", "repeated image", "hard edge"],
     "the camera holds while the same image repeats across the frame", "3s",
     [("image", "a face repeated four times in different flat colours, dots visible", ["重复脸", "四色", "网点"]),
      ("image", "a soup can rendered flat, outline heavy, no shadow", ["罐头", "平涂", "粗边"]),
      ("image", "a comic panel with a speech bubble, halftone shading", ["漫画格", "对话框", "网点"]),
      ("facet", "image", "a bright flower decal on flat colour", ["花朵贴纸", "平色"]),
      ("video", "the same frame repeating with the colour scheme swapping", ["重复", "换色"])]),

    ("极简主义", "Minimalism", "US", "1960s-1970s",
     ["single colour field", "no texture", "exact edges", "empty space"],
     "the camera holds absolutely still for the whole duration", "6s",
     [("image", "one pale grey field with a thin black line near the bottom", ["单色场", "细黑线"]),
      ("image", "a bare room where only light on the floor indicates time", ["空房间", "地面光"]),
      ("image", "two identical white cubes on a white surface", ["白方块", "白背景"]),
      ("facet", "image", "a single vertical black band down an off-white wall", ["黑竖条", "白墙"]),
      ("video", "nothing moves; only the light level shifts very slightly", ["完全静止", "光微变"])]),

    ("欧普艺术", "Op Art", "UK", "1960s",
     ["optical vibration", "high contrast lines", "warped grid", "no subject"],
     "the camera pushes slowly so the pattern appears to move", "4s",
     [("image", "concentric black and white rings that seem to bulge", ["同心圈", "黑白", "凸起感"]),
      ("image", "a grid warped at the centre, lines thickening", ["扭曲网格", "线变粗"]),
      ("image", "vertical stripes interrupted by a wave, edges buzzing", ["竖条", "波纹", "边缘震动"]),
      ("facet", "image", "two chevron fields meeting at a seam, depth illusion", ["人字纹", "接缝", "纵深错觉"]),
      ("video", "the pattern rotates slowly and the surface appears to breathe", ["旋转", "呼吸感"])]),

    ("赛博朋克", "Cyberpunk", "JP/US", "1980s-",
     ["neon signage", "wet street", "dense cabling", "holographic ad"],
     "the camera drifts forward through steam while signage flickers past", "6s",
     [("image", "a narrow street at night, Chinese and Japanese signage stacked, rain", ["霓虹招牌", "汉字招牌", "雨夜街道"]),
      ("image", "a cyborg arm being serviced under a hard lamp, cables everywhere", ["义肢", "维修", "线缆"]),
      ("image", "a megacity seen from a rooftop, haze and red aircraft lights", ["巨型城市", "雾霾", "红色航行灯"]),
      ("facet", "image", "a holographic advertisement flickering over a wet crowd", ["全息广告", "人群", "湿地"]),
      ("video", "steam crosses the lens, signage blinking, camera tracking forward", ["蒸汽", "闪烁", "前移"])]),

    ("蒸汽波", "Vaporwave", "US/JP", "2010s",
     ["pink and cyan", "marble statue", "grid horizon", "Japanese text"],
     "the camera drifts very slowly as a grid horizon slides", "5s",
     [("image", "a marble bust against a pink gradient, palm shadow across it", ["大理石胸像", "粉渐变", "棕榈影"]),
      ("image", "a checkered floor running to a grid horizon under a sunset", ["棋盘地面", "网格地平线", "落日"]),
      ("image", "a 90s desktop window floating over a magenta field", ["旧电脑窗口", "洋红"]),
      ("facet", "image", "Japanese characters floating on a soft purple gradient", ["日文", "紫色渐变"]),
      ("video", "the grid slides under the camera, everything else static", ["网格滑动", "静止"])]),

    ("合成器浪潮", "Synthwave", "US", "2000s-",
     ["magenta cyan split", "chrome", "sun with stripes", "strong horizon"],
     "the camera tracks forward toward a striped sun on the horizon", "6s",
     [("image", "a striped sun setting behind a chrome grid, magenta and cyan", ["条纹太阳", "镀铬网格", "洋红青"]),
      ("image", "a lone car on an endless night road, headlights and haze", ["夜路", "车灯", "雾"]),
      ("image", "a chrome motorcycle seen from a low angle, sunset behind", ["镀铬摩托", "低角度", "落日"]),
      ("facet", "image", "a wireframe mountain range under a purple sky", ["线框山脉", "紫天"]),
      ("video", "forward tracking on a night road, horizon lines rushing past", ["前推", "地平线掠过"])]),

    ("像素艺术", "Pixel Art", "JP", "1980s-",
     ["low resolution grid", "limited palette", "no anti-aliasing", "hard dithering"],
     "the camera pans in whole-pixel steps, no smoothing", "3s",
     [("image", "a castle at night drawn in 16 colours, pixels visible", ["城堡", "16色", "可见像素"]),
      ("image", "a character sprite on a tiled floor, eight directions implied", ["角色", "地块", "八方向"]),
      ("image", "a forest path built from dither patterns", ["森林小路", "抖动纹理"]),
      ("facet", "image", "a health bar and score in blocky type over a dark field", ["血条", "方块字"]),
      ("video", "the scene scrolls one tile at a time, no interpolation", ["逐格滚动", "无插值"])]),

    ("Y2K 千禧美学", "Y2K", "US", "1999-2004",
     ["chrome silver", "translucent plastic", "bubble form", "digital gloss"],
     "the camera orbits a translucent object while highlights slide across", "5s",
     [("image", "a translucent blue iMac-like form on white, reflections hard", ["半透明", "硬反光", "白底"]),
      ("image", "inflated silver bubbles and blurry chrome type", ["充气泡", "镀铬字"]),
      ("image", "a figure in silver puffer fabric, lens flare across the frame", ["银色羽绒", "镜头光"]),
      ("facet", "image", "a translucent pink handheld device in a bare hand", ["半透明装置", "手持"]),
      ("video", "the object turns slowly, chrome highlights sweeping", ["旋转", "高光扫过"])]),

    ("梦核", "Dreamcore", "US", "2010s-",
     ["liminal space", "unnatural emptiness", "low fidelity", "familiar but wrong"],
     "the camera holds an empty space too long", "8s",
     [("image", "an empty indoor pool under fluorescent light, no people", ["空泳池", "日光灯"]),
      ("image", "a corridor of doors with the same carpet, slightly low resolution", ["走廊", "同款地毯", "低清"]),
      ("image", "a playground at dusk with nobody there, sky too even", ["游乐场", "无人", "均匀天空"]),
      ("facet", "image", "a bedroom that looks familiar but the proportions are off", ["卧室", "比例不对"]),
      ("video", "the camera stays on an empty room, nothing entering", ["静止", "空房间", "过久"])]),

    ("暗黑学院", "Dark Academia", "UK/US", "2010s-",
     ["old library", "gothic stone", "wool tweed", "low candle light"],
     "the camera tracks along a library shelf, dust in the light", "6s",
     [("image", "a library with tall shelves, one window throwing a shaft", ["图书馆", "高书架", "光柱"]),
      ("image", "gothic stone arches in fog, ivy on the wall", ["哥特拱", "雾", "常春藤"]),
      ("image", "a desk with old books, ink, and a cold cup of tea", ["旧书", "墨水", "冷茶"]),
      ("facet", "image", "a student in tweed reading under a green lamp", ["粗呢外套", "绿罩灯", "阅读"]),
      ("video", "the camera glides along the shelf, dust turning in the beam", ["横移", "书脊", "尘埃"])]),

    ("废土", "Wasteland", "US", "1970s-",
     ["sand blasted metal", "improvised armour", "dust haze", "dead ground"],
     "the camera tracks a vehicle across dead ground, dust boiling behind", "6s",
     [("image", "a modified car with welded plate crossing cracked ground, dust behind", ["改装车", "焊铁", "裂地", "尘土"]),
      ("image", "a figure in improvised armour and goggles against a dust wall", ["护目镜", "拼装护甲", "沙尘"]),
      ("image", "a dead fuel station under a bleached sky, nothing green", ["废弃加油站", "漂白天空"]),
      ("facet", "image", "a water tank guarded by two figures, rust everywhere", ["水罐", "守卫", "锈"]),
      ("video", "long lens on a vehicle, heat shimmer, dust plume held", ["长焦", "热浪", "尘柱"])]),

    ("黑色电影", "Film Noir", "US", "1940s-1950s",
     ["hard key light", "venetian blind shadow", "wet asphalt", "smoke in the beam"],
     "the camera holds while a blind shadow cuts across a face", "5s",
     [("image", "a man in a fedora lit by a hard side key, half the face black", ["礼帽", "硬侧光", "半张脸黑"]),
      ("image", "venetian blind shadows thrown across a wall and a bed", ["百叶窗影", "墙面", "床"]),
      ("image", "a wet street at night, one streetlamp, long reflections", ["湿街", "路灯", "长反光"]),
      ("facet", "image", "a cigarette lit in the dark, smoke caught by a low lamp", ["香烟", "烟", "低灯"]),
      ("video", "the camera holds a doorway, a shadow arriving before the person", ["静止", "影子先到"])]),

    ("琳派", "Rimpa", "JP", "17th-19th c.",
     ["gold leaf ground", "bold flat motif", "high viewpoint", "negative space"],
     "the camera drifts across a gold ground, one motif held", "4s",
     [("image", "a river rendered as flat silver bands on a gold ground", ["金地", "银水", "平涂河"]),
      ("image", "iris flowers in flat colour, huge empty gold beside them", ["燕子花", "平涂", "大片金"]),
      ("image", "a screen of cranes seen from above, gold behind", ["鹤", "俯视", "金底"]),
      ("facet", "image", "a single branch crossing a large gold plane", ["一枝", "金面", "留白"]),
      ("video", "a slow lateral drift across gold, motif entering at one edge", ["横移", "金地", "入画"])]),

    ("新版画", "Shin-hanga", "JP", "1915-1950s",
     ["night blue", "gradient sky", "fine carved line", "lamp light"],
     "the camera holds a night scene, colour gradation doing all the work", "5s",
     [("image", "a snowy street at night in deep blue, one warm window", ["雪夜", "深蓝", "暖窗"]),
      ("image", "a mountain printed with a graded sky from indigo to pale", ["山", "渐变天空"]),
      ("image", "a woman in a kimono under a paper lamp, rain outside", ["和服", "纸灯", "雨"]),
      ("facet", "image", "a bridge at dusk, silhouettes flat against a graded sky", ["桥", "剪影", "渐变天色"]),
      ("video", "still night frame, only falling snow moving", ["静止", "落雪"])]),

    ("莫卧儿细密画", "Mughal Miniature", "IN", "16th-19th c.",
     ["flat layered space", "fine detail", "gold and lapis", "ornate border"],
     "the camera drifts across layered planes, ornament everywhere", "5s",
     [("image", "an emperor on a terrace, garden below in flat layers", ["皇帝", "露台", "分层花园"]),
      ("image", "a hunt with riders at the edge of a gold field", ["狩猎", "骑手", "金地"]),
      ("image", "a dense ornamental border around a small centred scene", ["装饰边框", "小场景"]),
      ("facet", "image", "lapis ground with gold leaves, every surface patterned", ["青金石", "金叶", "满纹样"]),
      ("video", "a slow drift across stacked planes, no perspective shift", ["横移", "平层"])]),

    ("伊斯兰几何纹样", "Islamic Geometric", "ME", "8th c.-",
     ["infinite tessellation", "star polygon", "no figure", "flat tile"],
     "the camera pushes into a tessellation that never resolves", "5s",
     [("image", "an eight-fold star tessellation in blue and white tile", ["八角星", "无限拼接", "瓷砖"]),
      ("image", "a muqarnas ceiling seen from below, geometry stacking", ["穹顶", "钟乳拱", "仰视"]),
      ("image", "a screen of pierced geometry, light passing through", ["透雕", "镂空", "光穿过"]),
      ("facet", "image", "a single rosette filling the frame, symmetrical to the edge", ["玫瑰纹", "满幅", "对称"]),
      ("video", "a slow push inward, the pattern repeating without end", ["推近", "无限重复"])]),

    ("宝丽来", "Polaroid", "US", "1970s-",
     ["soft focus", "colour shift", "white border", "faded contrast"],
     "the camera holds and the image almost imperceptibly drifts in colour", "5s",
     [("image", "a group on a beach, colours shifted green, soft everywhere", ["海滩合影", "偏绿", "柔焦"]),
      ("image", "a white bordered instant frame with a date stamp", ["白框相纸", "日期印"]),
      ("image", "a face flash-lit too close, background swallowed", ["近距离闪灯", "背景吞掉"]),
      ("facet", "image", "a scratched instant photo of a doorway, colours bled", ["刮痕", "门口", "色彩溢出"]),
      ("video", "a still instant photo, colour creeping slowly warmer", ["静止", "色彩渐变"])]),

    ("街头摄影", "Street Photography", "INTL", "1950s-",
     ["decisive moment", "wide angle close", "high contrast", "unposed"],
     "the camera moves through a crowd at walking speed", "5s",
     [("image", "a man stepping over a puddle, shadow and reflection meeting", ["跨水坑", "影子", "倒影"]),
      ("image", "two strangers passing, one looking back", ["路人交错", "回头"]),
      ("image", "a bus window framing a face inside, street reflected over it", ["车窗", "脸", "反射"]),
      ("facet", "image", "a hand and a cigarette at the edge of frame, rest out of focus", ["手", "香烟", "边缘"]),
      ("video", "handheld at chest height moving through the street", ["手持", "步行速度"])]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)
    print(f"corpus_v20: {len(corpus)} 条")

    added = []
    for zh, en, country, era, tags, cam, dur, rows in E:
        for row in rows:
            # base 行是 3 元组 (kind, desc, kw)；facet 行多一个前缀 (facet, kind, desc, kw)
            if len(row) == 4:
                facet, kind, desc, kw = row
            else:
                facet, kind, desc, kw = "base", row[0], row[1], row[2]
            n += 1
            is_video = (kind == "video")
            doc = {
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": country, "era": era,
                "facet": facet,
                "style_tags": tags[:4],
                "kw_zh": kw, "batch": "视觉传统补充",
                "description": desc,
                "text_semantic": (f"{desc}, {cam}, one continuous shot, in the style of {en}"
                                  if is_video else f"{desc}, in the style of {en}"),
                "params": ({"ar": "21:9", "duration": dur, "camera": "slow"} if is_video
                           else {"ar": "2.35:1", "style": "raw"}),
                "prompt": (f"cinematic {'video' if is_video else 'still'}, {desc}, "
                           f"in the style of {en}, --ar {'21:9' if is_video else '2.35:1'} --style raw"),
            }
            if is_video:
                doc["motion"] = "SLOW"
            added.append(doc)

    out = corpus + added
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"新增 {len(added)} 条（{len(E)} 实体 x 5）")
    print(f"corpus_v20 -> v21 : {len(corpus)} -> {len(out)}   实体 148 -> {148+len(E)}")
    print()
    for zh, en, *_ in E:
        print(f"  {zh:<14} {en}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V21_DONE")


if __name__ == "__main__":
    main()
