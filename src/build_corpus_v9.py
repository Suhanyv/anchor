"""
语料 v9：把张艺谋的 rural_realism 重定义为「红高粱」

依据（直接实测，非推测）
------------------------
rural_realism 的 12 条 query 全部失败，流向：
    Satyajit Ray    0.5277（张艺谋 0.3814，第 3）
    Clint Eastwood  0.4301（张艺谋 0.3738，第 3）
    Roberto Rossellini

关键词归属核查：
    「乡土写实」「尘土地光」-> 只有张艺谋用（无冲突）
    「朴素」              -> 费里尼 / 陈凯歌 / 张艺谋 共用
    雷伊的关键词          -> 人文 / 乡村 / 自然光

结论
----
不是词归属错，是**词太泛**：「乡土写实 / 朴素」译成英文就是
earthy rural naturalism / plain，而雷伊的文档里写着 village / natural light
-> 语义上确实更像雷伊。
张艺谋真正的标识是**大红**（base 面的 kw 就是 大红/对称/群像），
而我偏偏在乡村这个面里把红丢了。

做法
----
facet 由 rural_realism 改为 **red_sorghum（红高粱）**：
    kw      : 红高粱 / 乡野 / 尘土金光   （红高粱是张艺谋独有词）
    签名    : dusty golden light, bold red cloth and sorghum across an open field
    场景    : 红轿子过土路、高粱地与红布条、农夫与牛与红布、砖院里挂红辣椒
并删除旧的 rural_realism 文档。

注意：这是**修我写错的规格**，不是改测试迁就模型。
「朴素乡村」这类查询本来就该给雷伊，删掉泛词后不再把它们算作张艺谋的目标。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v8.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v9.jsonl")

OLD_FACET = "rural_realism"
NEW_FACET = "red_sorghum"
DIRECTOR_EN = "Zhang Yimou"
DIRECTOR_ZH = "张艺谋"

SIG = "dusty golden light, bold red cloth and sorghum across an open field"
SCENES = [
    "a red bridal sedan carried along a dusty dirt road by four men",
    "a sorghum field rippling in dusty golden light, red ribbons on the stalks",
    "a farmer and an ox on a dirt track, red cloth flapping at his waist",
    "a plain brick courtyard with laundry and strings of red chilli hanging",
]
KW = ["红高粱", "乡野", "尘土金光"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n0 = len(corpus)

    kept = [d for d in corpus if d.get("facet") != OLD_FACET]
    dropped = [d for d in corpus if d.get("facet") == OLD_FACET]

    n = max(int(d["doc_id"][1:]) for d in corpus)
    new = []
    for si, scene in enumerate(SCENES):
        n += 1
        desc = f"{scene}, {SIG}"
        new.append({
            "doc_id": f"d{n:04d}", "domain": "prompt_image", "lang": "en",
            "director": DIRECTOR_EN, "director_zh": DIRECTOR_ZH,
            "country": "CN", "era": "1980s", "facet": NEW_FACET,
            "style_tags": [x.strip() for x in SIG.split(",")][:6],
            "kw_zh": KW, "description": desc,
            "text_semantic": f"{desc}, in the style of {DIRECTOR_EN}",
            "params": {"ar": "2.35:1", "style": "raw"},
            "prompt": f"cinematic still, {desc}, in the style of {DIRECTOR_EN}, "
                      f"35mm film, --ar 2.35:1 --style raw",
        })

    # 一条视频
    n += 1
    scene = SCENES[0]
    desc = f"{scene}, {SIG}, slow push-in, dust drifting across the frame"
    new.append({
        "doc_id": f"d{n:04d}", "domain": "prompt_video", "lang": "en",
        "director": DIRECTOR_EN, "director_zh": DIRECTOR_ZH,
        "country": "CN", "era": "1980s", "facet": NEW_FACET, "motion": "SLOW",
        "style_tags": [x.strip() for x in SIG.split(",")][:4] + ["slow"],
        "kw_zh": KW, "description": desc,
        "text_semantic": f"{desc}, in the style of {DIRECTOR_EN}, shot as moving footage",
        "params": {"ar": "21:9", "duration": "6s", "camera": "slow"},
        "prompt": f"cinematic video, {desc}, in the style of {DIRECTOR_EN}, "
                  f"35mm film, --ar 21:9 --duration 6s --style raw",
    })

    out = kept + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"corpus_v8 -> v9 : {n0} -> {len(out)}")
    print(f"  删除 {OLD_FACET} 旧文档 : {len(dropped)} 条")
    for d in dropped:
        print(f"     {d['doc_id']} {d['domain']:<13} {d['text_semantic'][:64]}")
    print(f"\n  facet 改名 : {OLD_FACET} -> {NEW_FACET}")
    print(f"  kw        : ['乡土写实','尘土地光','朴素'] -> {KW}")
    print(f"  签名      : {SIG}")
    print(f"\n新增：")
    for d in new:
        print(f"  {d['doc_id']} [{d['facet']}] {d['domain']:<13} {d['text_semantic'][:70]}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V9_DONE")


if __name__ == "__main__":
    main()
