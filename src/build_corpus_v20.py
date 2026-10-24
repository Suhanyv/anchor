"""
语料 v20：从开源风格库补 14 个实体

来源与许可
----------
[YanKaFei/art-aesthetic-vault](https://github.com/YanKaFei/art-aesthetic-vault)
    - 卡片文本 MIT
    - 它的「七层拆解」给了我们三样此前没有的东西：
        ① 每个实体的「运动」层写得具体（眨眼 / 呼吸 / 发丝轻动 / 焦点微漂）
        ② 每个实体自己的「建议时长」
        ③ 「常见翻车点」—— 比通用技术负面词好得多的负面提示词来源
    - **我们只取术语与结构，描述文本全部自己写**（与其「宁可少不要错」的原则一致）

补什么、为什么
--------------
我们从 44 个导演卡里比出 8 个库里没有的（5 个日本动画/惊悚，正是「动画」这块的空白）：

    蔡明亮 Chantal Akerman        威廉·弗里德金 William Friedkin
    高畑勋 Isao Takahata          大友克洋 Katsuhiro Otomo
    黑泽清 Kiyoshi Kurosawa        押井守 Mamoru Oshii
    尼古拉斯·温丁·雷弗恩 Refn      今敏 Satoshi Kon

另加 6 个我们缺的视觉传统（用户会问，但库里没有）：
    浮世绘 / 敦煌壁画 / 藏传唐卡 / 波斯细密画 / 韩国民画 / 新艺术运动

corpus_v19 (826) -> corpus_v20
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v19.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v20.jsonl")

# (中文名, 英文名, 国家, 年代, 风格标签, 运动层, 建议时长, 翻车点(负面))
ENTITIES = [
    ("今敏", "Satoshi Kon", "JP", "1990s-2010s",
     ["match-cut transitions", "reality folding into illusion", "saturated red", "dense Tokyo"],
     ["the frame holds a face then cuts on the same shape into another scene",
      "a reflection steps out of the glass while the room stays still",
      "background figures move while the subject freezes"],
     "6s", ["smooth continuous camera moves", "empty backgrounds", "flat lighting"]),

    ("押井守", "Mamoru Oshii", "JP", "1980s-2010s",
     ["information-dense city", "static long takes", "canals and water", "cold cyan"],
     ["the camera holds still while traffic and signage flicker past",
      "a long still frame of a canal, water moving, nothing else",
      "slow lateral drift past layered signage and ducts"],
     "8s", ["fast cutting", "empty frame", "warm orange grade"]),

    ("大友克洋", "Katsuhiro Otomo", "JP", "1980s-2010s",
     ["neo-Tokyo megastructure", "explosive debris", "mechanical detail", "hard white light"],
     ["debris expands outward in one long shot, the camera holding",
      "a wide frame held as a structure collapses toward the lens",
      "fast lateral track past pipes and cabling"],
     "5s", ["clean minimal backgrounds", "soft pastel colour"]),

    ("高畑勋", "Isao Takahata", "JP", "1980s-2010s",
     ["watercolour countryside", "quiet domestic detail", "slow seasonal change", "muted earth"],
     ["the camera stays on a field while weather changes across the frame",
      "a long static shot of a room, light shifting on the floor",
      "slow pan across a hillside, people small inside it"],
     "8s", ["fast motion", "high saturation", "dense mechanical detail"]),

    ("黑泽清", "Kiyoshi Kurosawa", "JP", "1990s-2020s",
     ["empty frame held too long", "flat grey light", "distant figures", "dread in stillness"],
     ["the camera holds an empty room long after the figure has left",
      "a slow zoom into a corridor where nothing moves",
      "a single figure walks away down a long frame, held"],
     "10s", ["fast cutting", "close framing", "warm colour"]),

    ("蔡明亮", "Chantal Akerman", "TW", "1990s-2020s",
     ["extreme long static takes", "apartment interiors", "rain on concrete", "minimal dialogue"],
     ["a single take holds a room for an uncomfortably long time",
      "the camera stays locked while a person eats, in real time",
      "a still frame of a leaking ceiling, water moving"],
     "12s", ["cuts", "camera movement", "fast pacing"]),

    ("尼古拉斯·温丁·雷弗恩", "Nicolas Winding Refn", "DK", "2000s-2020s",
     ["neon magenta and cyan", "symmetrical slow shots", "silence before violence", "electronic pulse"],
     ["a slow dolly forward on a still figure, holding",
      "the camera holds a symmetrical frame, only neon flickering",
      "a slow reverse track away from a doorway"],
     "6s", ["handheld", "fast cutting", "natural daylight"]),

    ("威廉·弗里德金", "William Friedkin", "US", "1970s-2010s",
     ["documentary grit", "available light", "hard handheld", "urban street noise"],
     ["the camera runs handheld through a crowd, losing and finding the subject",
      "a hard handheld push into a doorway",
      "the frame shakes as something moves fast across it"],
     "5s", ["steady framing", "clean studio light", "symmetry"]),

    ("浮世绘", "Ukiyo-e", "JP", "Edo period",
     ["flat colour fields", "strong contour line", "patterned textiles", "wave and mountain motifs"],
     ["the frame holds a static tableau, only fabric and water moving",
      "a slow lateral drift across a flat patterned surface"],
     "4s", ["3d shading", "cast shadows", "photorealism"]),

    ("敦煌壁画", "Dunhuang Murals", "CN", "4th-14th c.",
     ["mineral pigment", "weathered plaster ground", "flying figures", "ochre and malachite"],
     ["the camera holds a wall, pigment flaking, no movement",
      "a slow vertical drift down a painted register"],
     "6s", ["clean digital surface", "saturated neon", "western perspective"]),

    ("藏传唐卡", "Tibetan Thangka", "CN", "17th-20th c.",
     ["flat gold ground", "symmetric mandala", "fine line", "lapis and vermilion"],
     ["the camera holds a centred mandala, nothing moves",
      "a slow push into the centre of a symmetric composition"],
     "5s", ["asymmetry", "photographic depth", "muted colour"]),

    ("波斯细密画", "Persian Miniature", "IR", "14th-17th c.",
     ["flat stacked planes", "fine detail", "garden and hunt motifs", "lapis blue and gold"],
     ["the camera drifts across stacked planes of a garden, no perspective",
      "a still frame held on a dense ornamental field"],
     "5s", ["single-point perspective", "cast shadow", "photographic realism"]),

    ("韩国民画", "Minhwa", "KR", "18th-20th c.",
     ["bold flat shapes", "folk humour", "unmodulated colour", "asymmetric placement"],
     ["a static frame holds a bold flat composition, only a bird moving",
      "a slow pan across unpainted paper with one bright figure"],
     "4s", ["realistic shading", "fine rendering", "grey palette"]),

    ("新艺术运动", "Art Nouveau", "EU", "1890s-1910s",
     ["sinuous line", "floral ornament", "muted jewel tones", "poster flatness"],
     ["the camera holds a decorative frame while a motif curls slowly",
      "a slow vertical drift along a sinuous ornament"],
     "5s", ["straight mechanical edges", "harsh industrial grey", "photoreal skin"]),
]

# 每个实体写 6 条：3 图像 + 1 图像特写 + 2 视频
SCENES = {
    "今敏": [
        ("base", "image", "a woman's face reflected in a train window, the city sliding past behind her",
         ["镜面", "列车窗", "都市", "倒影"]),
        ("base", "image", "identical hallway shapes repeating as one scene folds into the next",
         ["重复走廊", "场景折叠", "现实与幻觉"]),
        ("base", "image", "a crowd of commuters walking in step, one figure standing still among them",
         ["人群", "同步行走", "静止的人"]),
        ("facet", "image", "a saturated red room where the walls have started to breathe",
         ["饱和红", "房间", "异变"]),
        ("video", "two scenes joined on the same shape, the cut happening inside a movement",
         ["同形转场", "剪辑", "连续动作"]),
        ("video", "a reflection stepping out of a mirror while the camera holds completely still",
         ["镜中走出", "静止镜头", "超现实"]),
    ],
    "押井守": [
        ("base", "image", "a canal city at night, signage layered over ducts and water",
         ["运河", "霓虹招牌", "管道", "水面"]),
        ("base", "image", "an empty apartment with a television on, cold cyan light",
         ["空房间", "电视", "冷青色"]),
        ("base", "image", "a wide frame of traffic on an elevated road, no focal subject",
         ["高架", "车流", "无主体"]),
        ("facet", "image", "a diving figure suspended in dark water, bubbles rising",
         ["潜水", "深水", "气泡"]),
        ("video", "a long still frame while signage and traffic flicker behind the subject",
         ["静止长镜", "信息密度", "霓虹闪烁"]),
        ("video", "slow lateral drift past layered pipes, cables and signs",
         ["横移", "管道", "招牌"]),
    ],
    "大友克洋": [
        ("base", "image", "a megastructure of pipes and concrete over a ruined street",
         ["巨构", "管道", "混凝土", "废墟"]),
        ("base", "image", "a motorcycle skidding, debris and dust flung outward",
         ["摩托", "碎屑", "尘土"]),
        ("base", "image", "a laboratory wall of cabling and gauges under hard white light",
         ["实验室", "线缆", "仪表", "硬白"]),
        ("facet", "image", "a blast wave expanding through a city block, everything lifted",
         ["爆炸", "冲击波", "街区"]),
        ("video", "debris expanding outward in one held shot, the camera not moving",
         ["爆炸", "静止机位", "碎屑扩散"]),
        ("video", "a fast lateral track past pipes and cabling, motion blur",
         ["快速横移", "管道", "动态模糊"]),
    ],
    "高畑勋": [
        ("base", "image", "a watercolour hillside with small figures working in it",
         ["水彩", "山坡", "小人影", "劳作"]),
        ("base", "image", "a domestic interior, tatami and a low table, afternoon light",
         ["室内", "榻榻米", "矮桌", "午后光"]),
        ("base", "image", "a field under changing weather, colour muted and earthy",
         ["田野", "天气变化", "土色"]),
        ("facet", "image", "a child standing in a doorway looking out at rain",
         ["孩子", "门口", "看雨"]),
        ("video", "the camera holds a field while weather changes across the frame",
         ["静止长镜", "天气变化", "田野"]),
        ("video", "slow pan across a hillside with people small inside it",
         ["横摇", "山坡", "小人影"]),
    ],
    "黑泽清": [
        ("base", "image", "an empty corridor in flat grey light, a door open at the far end",
         ["空走廊", "灰光", "开着的门"]),
        ("base", "image", "a figure standing at the far edge of a wide empty frame",
         ["极简构图", "远景", "人影"]),
        ("base", "image", "a suburban street with nothing happening, sky overcast",
         ["郊区街道", "空景", "阴天"]),
        ("facet", "image", "a room where the objects have been moved while no one was there",
         ["房间", "异样", "无人"]),
        ("video", "the camera holds an empty room long after the figure has left",
         ["静止长镜", "空房间", "余留"]),
        ("video", "a slow zoom into a corridor where nothing moves",
         ["缓慢变焦", "走廊", "静止"]),
    ],
    "蔡明亮": [
        ("base", "image", "an apartment interior, water stains on the wall, one chair",
         ["公寓", "水渍", "椅子"]),
        ("base", "image", "a leaking ceiling, water gathering in a bowl below",
         ["漏水", "天花板", "水滴"]),
        ("base", "image", "a person sitting alone in a dim room, television off",
         ["独坐", "暗房间", "关掉的电视"]),
        ("facet", "image", "rain on a concrete balcony, a plastic chair tipped over",
         ["雨", "混凝土阳台", "塑料椅"]),
        ("video", "one take holds a room for an uncomfortably long time, the person eating",
         ["超长镜头", "固定机位", "真实时间"]),
        ("video", "a still frame of a leaking ceiling, water moving slowly",
         ["静止镜头", "漏水", "缓慢"]),
    ],
    "尼古拉斯·温丁·雷弗恩": [
        ("base", "image", "a figure in a leather jacket against magenta and cyan neon, still",
         ["皮革夹克", "品红", "霓虹", "静止"]),
        ("base", "image", "a perfectly symmetrical corridor washed in pink light",
         ["对称走廊", "粉色光"]),
        ("base", "image", "a night road with only the tail-lights of one car visible",
         ["夜路", "尾灯"]),
        ("facet", "image", "a room lit only by a television, colours bleeding at the edges",
         ["电视光", "溢出色彩"]),
        ("video", "a slow dolly forward on a still figure, holding the frame",
         ["缓慢推轨", "静止人物"]),
        ("video", "the camera holds a symmetrical frame, only neon flickering",
         ["对称构图", "霓虹闪烁", "静止"]),
    ],
    "威廉·弗里德金": [
        ("base", "image", "a crowded street under available light, hard shadows, no staging",
         ["街头", "自然光", "硬阴影", "人群"]),
        ("base", "image", "a car interior at night, streetlight sweeping across a face",
         ["车内", "路灯扫过", "夜景"]),
        ("base", "image", "a concrete underpass with graffiti, litter against a wall",
         ["地下通道", "涂鸦", "垃圾"]),
        ("facet", "image", "a doorway seen from a moving camera, motion blur at the edges",
         ["门口", "动态模糊", "跟拍"]),
        ("video", "the camera runs handheld through a crowd, losing and finding the subject",
         ["手持", "人群", "跟拍"]),
        ("video", "a hard handheld push into a doorway, the frame shaking",
         ["手持", "推进", "晃动"]),
    ],
    "浮世绘": [
        ("base", "image", "a flat blue wave curling over small boats, contour lines everywhere",
         ["波浪", "平涂", "轮廓线", "小船"]),
        ("base", "image", "a woman in a patterned kimono, flat colour, no shading",
         ["和服", "纹样", "平涂"]),
        ("base", "image", "a mountain seen through a frame of branches, flat planes",
         ["富士山", "树枝框景", "平层"]),
        ("facet", "image", "rain drawn as straight lines across a bridge and figures",
         ["雨线", "桥", "人影"]),
        ("video", "the frame holds a static tableau, only fabric and water moving",
         ["静止画面", "布动", "水动"]),
        ("video", "a slow lateral drift across a flat patterned surface",
         ["横移", "纹样", "平涂"]),
    ],
    "敦煌壁画": [
        ("base", "image", "flying figures with long ribbons on a weathered ochre wall",
         ["飞天", "飘带", "土红", "剥落"]),
        ("base", "image", "a wall of mineral pigment, malachite green beside oxidized red",
         ["矿物颜料", "石绿", "朱红"]),
        ("base", "image", "a buddha in a mandorla, plaster ground cracking around it",
         ["佛像", "背光", "壁面开裂"]),
        ("facet", "image", "a painted register of donors, small figures in rows",
         ["供养人", "成排", "壁画分层"]),
        ("video", "the camera holds a wall, pigment flaking, nothing else moving",
         ["静止镜头", "墙面", "剥落"]),
        ("video", "a slow vertical drift down a painted register",
         ["缓慢下移", "壁画", "分层"]),
    ],
    "藏传唐卡": [
        ("base", "image", "a centred mandala in lapis and vermilion on a gold ground",
         ["曼陀罗", "居中", "青金石", "金地"]),
        ("base", "image", "a deity with many arms inside a circular frame, fine line throughout",
         ["多臂神像", "圆框", "细线"]),
        ("base", "image", "a dense field of small figures arranged in a perfect grid",
         ["密集小像", "网格", "对称"]),
        ("facet", "image", "gold line over flat red, ornament filling every gap",
         ["金线", "平红", "满饰"]),
        ("video", "the camera holds a centred mandala, nothing moves",
         ["静止", "居中", "对称"]),
        ("video", "a slow push into the centre of a symmetric composition",
         ["缓慢推近", "对称", "居中"]),
    ],
    "波斯细密画": [
        ("base", "image", "a walled garden seen from above, stacked flat planes, no perspective",
         ["花园", "俯视", "平层", "无透视"]),
        ("base", "image", "a hunting scene with horsemen at the edge of a gold field",
         ["狩猎", "骑马", "金地"]),
        ("base", "image", "a dense ornamental border around a small centred scene",
         ["装饰边框", "居中", "细密"]),
        ("facet", "image", "lapis blue ground with gold leaves, every surface patterned",
         ["青金石蓝", "金叶", "满纹样"]),
        ("video", "the camera drifts across stacked planes of a garden",
         ["横移", "平层", "花园"]),
        ("video", "a still frame held on a dense ornamental field",
         ["静止", "纹样", "细部"]),
    ],
    "韩国民画": [
        ("base", "image", "a tiger with a comic face, bold flat shapes, unpainted paper around it",
         ["老虎", "滑稽脸", "平涂", "留白"]),
        ("base", "image", "a magpie on a branch, unmodulated colour, asymmetric placement",
         ["喜鹊", "树枝", "纯色", "不对称"]),
        ("base", "image", "a screen of books and objects, each shape outlined plainly",
         ["册架图", "物件", "白描"]),
        ("facet", "image", "a bold flower head filling a corner, huge empty paper beside it",
         ["大花", "边角", "大片空白"]),
        ("video", "a static frame holds a bold flat composition, only a bird moving",
         ["静止", "平涂", "鸟动"]),
        ("video", "a slow pan across unpainted paper with one bright figure",
         ["横移", "留白", "亮色人物"]),
    ],
    "新艺术运动": [
        ("base", "image", "a poster woman with flowing hair that turns into ornament",
         ["海报", "长卷发", "装饰线"]),
        ("base", "image", "a wrought iron stair rail curving in a sinuous plant line",
         ["铁艺", "曲线", "植物纹"]),
        ("base", "image", "stained glass panels in muted jewel tones, floral geometry",
         ["彩绘玻璃", "宝石色", "花卉几何"]),
        ("facet", "image", "a doorway framed by carved ornament, every edge softened into a curve",
         ["门口", "雕饰", "全曲线"]),
        ("video", "the camera holds a decorative frame while a motif curls slowly",
         ["静止", "装饰", "缓慢卷曲"]),
        ("video", "a slow vertical drift along a sinuous ornament",
         ["缓慢上移", "曲线", "装饰"]),
    ],
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)
    print(f"corpus_v19: {len(corpus)} 条")

    added = []
    for zh, en, country, era, tags, motion, dur, fails in ENTITIES:
        sc = SCENES[zh]
        for i, row in enumerate(sc):
            n += 1
            # 图像行是 4 元组 (facet, "image", desc, kw)；视频行写成 3 元组，补一个占位
            if len(row) == 3:
                row = ("video", "video", row[1], row[2])
            is_video = row[1] == "video"
            facet, _dom, desc, kw = row[0], row[1], row[2], row[3]
            doc = {
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video" if is_video else "prompt_image",
                "lang": "en", "director": en, "director_zh": zh,
                "country": country, "era": era,
                "facet": facet if facet in ("base", "facet") else "base",
                "style_tags": tags[:4] + ([motion[i % len(motion)][:34]] if is_video else []),
                "kw_zh": kw, "batch": "开源库补充",
                "description": desc,
                "text_semantic": (f"{desc}, {motion[i % len(motion)]}, one continuous shot, "
                                  f"in the style of {en}" if is_video
                                  else f"{desc}, in the style of {en}"),
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

    print(f"新增 {len(added)} 条（14 实体 x 6）")
    print(f"corpus_v19 -> v20 : {len(corpus)} -> {len(out)}")
    print()
    for zh, en, country, era, *_ in ENTITIES:
        cnt = sum(1 for a in added if a["director_zh"] == zh)
        vid = sum(1 for a in added if a["director_zh"] == zh and a["domain"] == "prompt_video")
        print(f"  {zh:<14} {en:<26} {cnt} 条（视频 {vid}）")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V20_DONE")


if __name__ == "__main__":
    main()
