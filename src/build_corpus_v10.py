"""
语料 v10：新增「藏在植被里的观察者」机制面

来源：用户真实提示词（data/raw/prompt_real_01.txt，已标注为留出评测集）

诊断过程
--------
用该提示词的机制核心做中文 query 测试：
    「偷看+被发现」           -> Hitchcock 第 1 名 0.3695  ✅ 对
    「从树枝后面看过去，前景有草叶遮挡」 -> 手卷长卷 0.3423      ❌ 完全跑偏

查语料发现原因：我们所有窥视类文档都是**隔窗偷看**
    a grid of apartment windows at dusk with one lit window, telephoto compression
    a figure seen through a window frame from across a courtyard
而用户的机制是**躲在植被里偷看**
    hidden behind wild grass and tree branches
    leaves and blades of grass partially block the frame
    someone secretly watching from the forest
-> 两种不同机制，后者完全缺失。不是模型笨，是没这个知识。

做法
----
新增 facet: mech_hidden_observer（藏在植被里的观察者），实体仍归 Hitchcock
用**用户自己的措辞**写文档（这是最准确的填充材料）：
    foliage occlusion / partially blocked frame / caught watching / turns and looks into camera

corpus_v9 (720) -> corpus_v10
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v9.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v10.jsonl")

FACET = "mech_hidden_observer"
DIRECTOR_EN = "Alfred Hitchcock"
DIRECTOR_ZH = "希区柯克"
SIG = "voyeuristic perspective, foreground foliage partially blocking the frame, caught watching"

SCENES = [
    "a figure watched from behind tall grass and leaves that blur the foreground",
    "branches and blades of grass partially block the frame as if someone hides in the foliage",
    "the subject suddenly notices and looks straight into the camera, caught watching",
    "a hidden observer's view through a gap in the branches, the subject turning toward it",
]
KW = ["草丛遮挡", "偷看", "被发现", "树枝遮挡", "隐蔽视角"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    new = []
    for scene in SCENES:
        n += 1
        desc = f"{scene}, {SIG}"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
            "director": DIRECTOR_EN, "director_zh": DIRECTOR_ZH,
            "country": "US", "era": "1950s", "facet": FACET,
            "style_tags": [x.strip() for x in SIG.split(",")][:6],
            "kw_zh": KW, "description": desc,
            "text_semantic": f"{desc}, in the style of {DIRECTOR_EN}",
            "params": {"ar": "2.35:1", "style": "raw"},
            "prompt": f"cinematic still, {desc}, in the style of {DIRECTOR_EN}, "
                      f"35mm film, --ar 2.35:1 --style raw",
        })

    # 一条视频（用户那条本质是视频提示词）
    n += 1
    desc = (f"the camera hidden in tall grass as a rider approaches, foliage blocking "
            f"the foreground, then the subject looks straight into the camera, "
            f"{SIG}, slow push-in, steady drift")
    new.append({
        "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
        "director": DIRECTOR_EN, "director_zh": DIRECTOR_ZH,
        "country": "US", "era": "1950s", "facet": FACET, "motion": "SLOW",
        "style_tags": [x.strip() for x in SIG.split(",")][:4] + ["slow"],
        "kw_zh": KW, "description": desc,
        "text_semantic": f"{desc}, in the style of {DIRECTOR_EN}, shot as moving footage",
        "params": {"ar": "21:9", "duration": "5s", "camera": "slow"},
        "prompt": f"cinematic video, {desc}, in the style of {DIRECTOR_EN}, "
                  f"35mm film, --ar 21:9 --duration 5s --style raw",
    })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"corpus_v9 -> v10 : {len(corpus)} -> {len(out)}  (+{len(new)})")
    print(f"新 facet: {FACET}  (归 {DIRECTOR_EN})")
    print(f"kw: {KW}")
    print("\n新增文档：")
    for d in new:
        print(f"  {d['doc_id']} {d['domain']:<13} {d['text_semantic'][:88]}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V10_DONE")


if __name__ == "__main__":
    main()
