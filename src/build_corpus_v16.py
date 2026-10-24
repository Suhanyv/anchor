"""
语料 v16：改写「藏在植被里偷看」的 5 条文档 —— 合规清理

为什么必须改
------------
这 5 条文档（mech_hidden_observer）的措辞逐字来自 prompt_real_01，
而那条提示词是用户「在网上找到的」，**作者不明**。
署名无法完成，只能改写。

外来措辞（已查证命中）
    voyeuristic perspective            5 条
    foreground foliage                 5 条
    caught watching                    5 条
    hidden observer                    1 条
    tall grass and leaves              1 条

改写原则
--------
1. 机制必须保留：观察者藏在植被里 → 主体发现 → 看向镜头
   （这是从真实提示词里学到的知识点，属于"事实/机制"，不是文字表达）
2. **一个字都不沿用**上述外来词组
3. 换意象表达同一件事：weeds / stems / thicket / gap between branches / low in undergrowth
4. 保留 Hitchcock 归属（偷窥机制是他的标志，这是公共知识不是抄袭）

corpus_v14 (795) -> corpus_v16
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")

FACET = "mech_hidden_observer"
DIRECTOR = "Alfred Hitchcock"
DIRECTOR_ZH = "希区柯克"
SIG = "a viewer concealed in vegetation, the person in shot noticing and turning to the lens"

SCENES = [
    "a viewer lying low in roadside weeds, stems cutting across the near field of view",
    "shrubs and stalks breaking the picture into slivers, someone hidden behind them",
    "the camera tucked inside a thicket, the figure inside suddenly lifting their eyes to meet it",
    "a narrow gap between branches framing the scene, the person framed noticing the attention",
    "a watcher half buried in low scrub, the subject turning their head toward that direction",
]

# 禁止出现的词组（外来措辞）
BANNED = ["voyeuristic perspective", "foreground foliage", "caught watching",
          "hidden observer", "tall grass and leaves", "secretly watching",
          "leaves and blades of grass"]

KW = ["草丛遮挡", "偷看", "被发现", "树枝遮挡", "隐蔽视角"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    old = [d for d in corpus if d.get("facet") == FACET]
    kept = [d for d in corpus if d.get("facet") != FACET]

    print(f"corpus_v14: {len(corpus)} 条")
    print(f"  待改写 {FACET}: {len(old)} 条")
    for d in old:
        print(f"    {d['doc_id']} {d['domain']:<13} {d['text_semantic'][:86]}")

    n = max(int(d["doc_id"][1:]) for d in corpus)
    new = []
    for i, scene in enumerate(SCENES):
        n += 1
        desc = f"{scene}, {SIG}"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
            "director": DIRECTOR, "director_zh": DIRECTOR_ZH,
            "country": "US", "era": "1950s", "facet": FACET,
            "style_tags": [x.strip() for x in SIG.split(",")][:6],
            "kw_zh": KW, "batch": "合规改写", "description": desc,
            "text_semantic": f"{desc}, in the style of {DIRECTOR}",
            "params": {"ar": "2.35:1", "style": "raw"},
            "prompt": f"cinematic still, {desc}, in the style of {DIRECTOR}, "
                      f"35mm film, --ar 2.35:1 --style raw",
        })

    # 一条视频
    n += 1
    desc = (f"the camera low in dense undergrowth as someone walks past, stems sweeping "
            f"the near plane, then the subject lifts their head toward the lens, "
            f"{SIG}, slow push-in, steady drift")
    new.append({
        "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
        "director": DIRECTOR, "director_zh": DIRECTOR_ZH,
        "country": "US", "era": "1950s", "facet": FACET, "motion": "SLOW",
        "style_tags": [x.strip() for x in SIG.split(",")][:4] + ["slow"],
        "kw_zh": KW, "batch": "合规改写", "description": desc,
        "text_semantic": f"{desc}, in the style of {DIRECTOR}, shot as moving footage",
        "params": {"ar": "21:9", "duration": "5s", "camera": "slow"},
        "prompt": f"cinematic video, {desc}, in the style of {DIRECTOR}, "
                  f"35mm film, --ar 21:9 --duration 5s --style raw",
    })

    out = kept + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\n新增（改写版）：")
    for d in new:
        print(f"  {d['doc_id']} {d['domain']:<13} {d['text_semantic'][:92]}")

    print(f"\n=== 合规自检：外来词组是否已清零 ===")
    blob = " ".join(d["text_semantic"].lower() for d in out)
    ok = True
    for b in BANNED:
        c = blob.count(b)
        if c:
            ok = False
        print(f"  {b:<28} {c} 处 {'✅' if c == 0 else '❌ 仍存在'}")
    print(f"  结论：{'全部清零 ✅' if ok else '仍有残留 ❌'}")

    print(f"\ncorpus_v14 -> v16 : {len(corpus)} -> {len(out)}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V16_DONE")


if __name__ == "__main__":
    main()
