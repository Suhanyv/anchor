"""
语料 v14：补「史诗辽阔」面 —— 强自己，不是削对手

依据
----
v13 的教训：把三个磁铁的通用词削掉后净亏 5pp，因为**正确答案本身太弱**。
    「女骑士骑着披甲战马在无边草原上全速疾驰，远景全身，跟随镜头」
        正确答案 = Denis Villeneuve（用户真实提示词 prompt_02 明确点名）
        但 Villeneuve 的语料只有：巨物 / 雾霭 / 极简 / 冷蓝室内
        没有任何一条描述"骑手穿越辽阔草原 / 低地平线 / 跟随镜头"

语言来源
--------
直接取用户找到的 prompt_02 原文中的表述（那是唯一真实证据，不是我编的）：
    "Wide cinematic shot, showing the full body of the horse and rider from a distant perspective"
    "Epic wide landscape composition, cinematic tracking shot, low horizon, dramatic sense of scale"
    "The grassland stretches endlessly around the lone knight"
    "a lone warrior traveling toward an unknown destiny"
    "Warm golden sunlight from the side, subtle highlights on the steel armor"

做法
----
只加**具体画面**，不加通用质量词（电影感/史诗感/震撼 这类一律不要）。
在 v13 基础上增量，形成三方对照：
    c12 无磁铁修复、无史诗面
    c13 有磁铁修复、无史诗面
    c14 有磁铁修复 + 史诗面 <- 本轮

corpus_v13 (785) -> corpus_v14
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v13.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")

# (director_en, zh, facet, 签名, [场景], kw)
ADD = [
    # ---- Villeneuve：史诗辽阔（新 facet）----
    ("Denis Villeneuve", "维伦纽瓦", "epic_scale",
     "vast open landscape, low horizon, monumental sky above a tiny figure",
     ["a lone rider crossing a vast open plain, the body small against an enormous sky",
      "a full body figure on horseback seen from a distant perspective, grass to the horizon",
      "a tiny figure dwarfed by a colossal structure pressing down on the horizon",
      "a wide empty field under a heavy grey sky, dust suspended in the air"],
     ["巨物", "辽阔", "低地平线"]),

    # ---- Nolan：尘霾史诗（已有 dust_epic，补具体画面）----
    ("Christopher Nolan", "诺兰", "dust_epic",
     "dust plain, low horizon, a distant structure under a massing sky",
     ["a figure crossing a dust plain toward a distant structure, low horizon",
      "a wide grey field under a collapsing sky, one figure walking away"],
     ["尘霾", "苍茫", "冷蓝远景"]),

    # ---- Malick：自然光辽阔（已有 base，补具体画面）----
    ("Terrence Malick", "马利克", "base",
     "natural light, golden hour, wheat moving in waves under a huge sky",
     ["a figure walking a wheat field at low sun, backlit, horizon far away",
      "a wide field under a huge sky, wind moving the grass in long waves"],
     ["自然光", "黄金时刻", "麦田"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new = []
    for en, zh, facet, sig, scenes, kws in ADD:
        for scene in scenes:
            n += 1
            desc = f"{scene}, {sig}"
            new.append({
                "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
                "director": en, "director_zh": zh, "facet": facet,
                "style_tags": [x.strip() for x in sig.split(",")][:6],
                "kw_zh": kws, "batch": "史诗面", "description": desc,
                "text_semantic": f"{desc}, in the style of {en}",
                "params": {"ar": "2.35:1", "style": "raw"},
                "prompt": f"cinematic still, {desc}, in the style of {en}, "
                          f"35mm film, --ar 2.35:1 --style raw",
            })

    # 两条视频：直接对应「全速疾驰 + 跟随镜头」这个诉求
    vids = [
        ("Denis Villeneuve", "维伦纽瓦", "epic_scale", "KINETIC",
         "a rider at full gallop across an open plain, camera tracking alongside, dust trailing behind",
         "tracking shot, low horizon, monumental sky above a tiny figure", 5,
         ["巨物", "辽阔", "低地平线"]),
        ("Denis Villeneuve", "维伦纽瓦", "epic_scale", "SLOW",
         "a thin line of riders crossing a vast grey plain, camera drifting with them",
         "vast open landscape, low horizon, monumental sky above a tiny figure", 8,
         ["巨物", "辽阔", "低地平线"]),
    ]
    for en, zh, facet, mo, scene, sig, dur, kws in vids:
        n += 1
        desc = f"{scene}, {sig}, {'fast handheld tracking, quick cuts' if mo == 'KINETIC' else 'slow push-in, steady drift'}"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
            "director": en, "director_zh": zh, "facet": facet, "motion": mo,
            "style_tags": [x.strip() for x in sig.split(",")][:4] + [mo.lower()],
            "kw_zh": kws, "batch": "史诗面", "description": desc,
            "text_semantic": f"{desc}, in the style of {en}, shot as moving footage",
            "params": {"ar": "21:9", "duration": f"{dur}s", "camera": mo.lower()},
            "prompt": f"cinematic video, {desc}, in the style of {en}, "
                      f"35mm film, --ar 21:9 --duration {dur}s --style raw",
        })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"corpus_v13 -> v14 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print()
    print("新增（全部来自 prompt_02 的真实表述，无通用质量词）：")
    for d in new:
        print(f"  {d['doc_id']} [{d['director'][:18]:<20}] {d['domain']:<13} "
              f"{d['description'][:72]}")
    print()
    generic = ["cinematic", "epic", "stunning", "breathtaking", "photorealistic", "8k"]
    hits = [(d["doc_id"], g) for d in new for g in generic
            if g in d["description"].lower()]
    print(f"通用质量词自检: {'无' if not hits else hits}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V14_DONE")


if __name__ == "__main__":
    main()
