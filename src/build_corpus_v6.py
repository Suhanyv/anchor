"""
语料 v6：让图像和视频**真的分开**

现状问题（已核查）：v5 里 image 与 video 的 doc 文本完全相同，
只差 "still"/"video" 一个词，风格签名一模一样。
-> 检索端完全无法区分用户要图还是要视频。

设计
----
共享语义空间 + 域标签：
  * 风格签名（description 主体）**保持不变** -> 这样「互通」仍然成立
  * 视频 doc 追加**真正的运镜语言** + 时长参数（结构化，不进语义也可以，这里同时给文本）
  * 现有 doc 统一标为 prompt_image（原来有 1/3 错标成 video）

运镜按风格自动选（避免给侯孝贤加"快切"这种矛盾）：
  STATIC  签名含 static/locked/fixed/long take  -> 固定机位、不切、长镜头
  KINETIC 签名含 kinetic/rapid/cutting/fast     -> 甩镜、快切、跟拍
  SLOW    其余                                   -> 缓推、手持微漂、焦点缓变

corpus_v5 (547) -> corpus_v6 (~547 + 2*组数)
"""
import json
import os
import re

ROOT = r"F:\llm"
SRC = os.path.join(ROOT, "data", "raw", "corpus_v5.jsonl")
OUT = os.path.join(ROOT, "data", "raw", "corpus_v6.jsonl")

BUNDLES = {
    "STATIC": "locked-off camera, no cut, one extremely long take, patient stillness",
    "KINETIC": "whip pan, rapid cutting, tracking follow, restless handheld movement",
    "SLOW": "slow push-in, gentle handheld drift, focus pulling slowly",
}
VIDEO_KW = ["运镜", "镜头运动", "时长", "视频"]

PAT = {
    "STATIC": re.compile(r"static|locked|fixed|long take|stillness|patient|contemplat", re.I),
    "KINETIC": re.compile(r"kinetic|rapid|cutting|fast|restless|handheld energy|whip", re.I),
}


def pick_bundle(desc):
    if PAT["STATIC"].search(desc):
        return "STATIC"
    if PAT["KINETIC"].search(desc):
        return "KINETIC"
    return "SLOW"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    corpus = load(SRC)
    n = max(int(d["doc_id"][1:]) for d in corpus)

    # 1) 现有文档统一标为 image（原先 1/3 错标成 video）
    fixed_video_to_image = 0
    for d in corpus:
        if d.get("domain") == "prompt_video":
            d["domain"] = "prompt_image"
            fixed_video_to_image += 1
        d["params"] = {"ar": d.get("params", {}).get("ar", "2.35:1"), "style": "raw"}

    # 2) 每组（director, facet）生成 2 条视频 doc，追加运镜语言
    groups = {}
    for d in corpus:
        groups.setdefault((d["director"], d.get("facet", "base")), []).append(d)

    new = []
    bundle_count = {"STATIC": 0, "KINETIC": 0, "SLOW": 0}
    for (director, facet), docs in groups.items():
        # 取该组前 2 条作为视频化的模板（保留其风格签名与场景）
        for d in docs[:2]:
            n += 1
            b = pick_bundle(d["description"])
            bundle_count[b] += 1
            motion = BUNDLES[b]
            dur = "8s" if b == "STATIC" else ("4s" if b == "KINETIC" else "6s")
            desc = f"{d['description']}, {motion}"
            kws = list(d.get("kw_zh", []))
            for k in VIDEO_KW:
                if k not in kws:
                    kws.append(k)
            new.append({
                "doc_id": f"d{n:04d}",
                "domain": "prompt_video",
                "lang": "en",
                "director": director,
                "director_zh": d.get("director_zh", ""),
                "country": d.get("country", ""),
                "era": d.get("era", ""),
                "facet": facet,
                "motion": b,
                "style_tags": list(d.get("style_tags", []))[:4] + [b.lower()],
                "kw_zh": kws,
                "description": desc,
                "text_semantic": f"{desc}, in the style of {director}, shot as moving footage",
                "params": {"ar": "21:9", "duration": dur, "camera": b.lower()},
                "prompt": f"cinematic video, {desc}, in the style of {director}, "
                          f"35mm film, --ar 21:9 --duration {dur} --style raw",
            })

    out = corpus + new
    with open(OUT, "w", encoding="utf-8") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    from collections import Counter
    dom = Counter(d["domain"] for d in out)
    print(f"corpus_v5 -> v6 : {len(corpus)} -> {len(out)}  (+{len(new)} 条视频)")
    print(f"  原 video 错标改回 image : {fixed_video_to_image} 条")
    print(f"  域分布 : {dict(dom)}")
    print(f"  运镜分配 : {bundle_count}")
    print("\n=== 视频 doc 样例（同一风格，三种运镜）===")
    for b in ("STATIC", "KINETIC", "SLOW"):
        e = next((d for d in new if d["motion"] == b), None)
        if e:
            print(f"\n  [{b}] {e['director']} / {e['facet']}")
            print(f"    {e['text_semantic'][:120]}")
            print(f"    params: {e['params']}")
    print(f"\n-> {OUT}")
    print("\n### CORPUS_V6_DONE")


if __name__ == "__main__":
    main()
