"""
语料 v19 + 运镜训练 query

问题
----
v18 给 199 条视频文档加了英文运镜语言，重训后视频查询的导演命中仍是 1/8，毫无变化。

根因（想清楚了）
----------------
queries_v4 的 kw_zh 全部是**风格词**（对称 / 霓虹 / 冷白…），
没有任何一条是运镜描述。所以模型从未学过「中文运镜词 -> 英文运镜短语」这个映射。
文档侧加了英文运镜词，但查询侧没覆盖 -> 学不到 -> 白做。

这与「中文锚点」是同一件事的两面：
    那次：零样本索引的**文档侧**必须说用户的语言
    这次：**查询侧**必须覆盖文档里的新维度

做法
----
1. 给 30 个实体的视频文档加 motion_zh（中文运镜词，每位 4~6 个）
2. 生成运镜训练 query："{中文运镜词}，{该实体的一个中文风格词}"
   模板与评测句式隔离
3. 输出 corpus_v19.jsonl + queries_motion_v19.jsonl

corpus_v18 (826) -> corpus_v19（加字段，不改 id）
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "raw", "corpus_v18.jsonl")
OUT_C = os.path.join(ROOT, "data", "raw", "corpus_v19.jsonl")
OUT_Q = os.path.join(ROOT, "data", "raw", "queries_motion_v19.jsonl")

# 实体的中文运镜词（用户会怎么描述"这个导演怎么运动镜头"）
MOTION_ZH = {
    "Hou Hsiao-hsien": ["长镜头", "固定机位", "横移", "不剪辑", "缓慢"],
    "Denis Villeneuve": ["缓慢推近", "远景不动", "跟拍车辆", "极慢"],
    "Alfred Hitchcock": ["推近特写", "升降镜头", "主观视角", "从上往下看"],
    "Stanley Kubrick": ["对称横移", "匀速前推", "单点透视"],
    "Paul Greengrass": ["手持跟拍", "晃动", "急停", "贴身跟拍"],
    "Kathryn Bigelow": ["低角度手持", "快速移动", "突然停下"],
    "Terrence Malick": ["缓慢横移", "穿过草丛", "仰拍树枝", "漂移"],
    "Alfonso Cuarón": ["一镜到底", "环绕", "不切换", "连续跟拍"],
    "Park Chan-wook": ["缓慢环绕", "对称横移", "转圈"],
    "Wong Kar-wai": ["手持", "抽帧", "慢动作", "突然移动"],
    "Ridley Scott": ["缓慢推进", "穿过烟雾", "静止远景"],
    "Akira Kurosawa": ["静止远景", "突然横移", "风起"],
    "Jia Zhangke": ["固定长镜头", "人物进出画面", "一动不动"],
    "Martin Scorsese": ["快速推镜", "甩镜", "跟拍走动"],
    "Steven Spielberg": ["缓慢推近", "揭开遮挡", "镜头升起"],
    "David Lynch": ["静静停住", "缓慢变焦", "突然动作"],
    "Francis Ford Coppola": ["缓慢推轨", "走廊跟拍"],
    "Guillermo del Toro": ["推进怪物", "升降下移", "环绕静物"],
    "Wes Anderson": ["对称横移", "正面推轨", "甩镜切换"],
    "Nicolas Roeg": ["跳切", "突然变焦", "硬切"],
    "Andrei Tarkovsky": ["超长镜头", "缓慢横移", "不剪辑", "时间流逝"],
    "Robert Bresson": ["完全固定", "不移动", "静止"],
    "Michelangelo Antonioni": ["极慢横移", "空镜停留", "缓慢漂移"],
    "Ingmar Bergman": ["静止特写", "缓慢推近", "长镜头"],
    "Sergio Leone": ["极远景静止", "缓慢推到特写", "升降"],
    "Wuershan": ["缓慢升起", "环绕巨兽", "横移掠过军阵"],
    "Frant Gwo": ["缓慢仰拍", "跟拍车队", "极缓推近"],
    "King Hu": ["静止远景", "突然爆发", "横移庭院"],
    "Ching Siu-tung": ["跟拍上升", "垂直下落", "掠过树冠"],
    "Jiaozi": ["快速环绕", "甩镜", "穿过火焰"],
}

GENERIC_MOTION = ["缓慢移动", "一个长镜头", "不剪辑"]

# 训练句式（与评测句式严格隔离，不复用 lang_templates 里的任何一条）
TRAIN_TPL = [
    "{m}，{s}那种感觉",
    "{m}的镜头，像{s}",
    "我要{m}，同时{s}",
    "镜头不要动{s}，但要{m}",
    "{s}，而且{m}",
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    rnd = random.Random(20261024)
    corpus = load(SRC)

    # 每个实体 -> 它的视频文档 id
    vid = {}
    for d in corpus:
        if d["domain"] == "prompt_video":
            vid.setdefault(d["director"], []).append(d["doc_id"])

    n_tagged = 0
    for d in corpus:
        if d["domain"] != "prompt_video":
            continue
        who = d["director"]
        d["motion_zh"] = MOTION_ZH.get(who, GENERIC_MOTION)
        if who in MOTION_ZH:
            n_tagged += 1

    with open(OUT_C, "w", encoding="utf-8") as f:
        for d in corpus:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    # 生成运镜训练 query
    qs = []
    for who, ids in vid.items():
        mlist = MOTION_ZH.get(who, GENERIC_MOTION)
        # 该实体的中文风格词：从视频文档的 kw_zh 里取
        kws = []
        for d in corpus:
            if d["doc_id"] in ids:
                kws.extend(d.get("kw_zh") or [])
        kws = list(dict.fromkeys(kws))
        if not kws:
            continue
        for ti, tpl in enumerate(TRAIN_TPL):
            for rep in range(2):
                m = rnd.choice(mlist)
                s = rnd.choice(kws)
                qs.append({
                    "query_id": f"qm{len(qs):05d}",
                    "query": tpl.format(m=m, s=s),
                    "lang": "zh",
                    "domain": "prompt_video",
                    "relevant": ids,
                    "target_director": who,
                    "facet": "video",
                    "query_kind": "style",
                    "template_id": f"motion:{ti}",
                    "template": tpl,
                })

    with open(OUT_Q, "w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"corpus_v18 -> v19 : {len(corpus)} 条（加了 motion_zh 字段）")
    print(f"  有中文运镜词的视频文档: {n_tagged} 条；其余用通用词")
    print(f"运镜训练 query: {len(qs)} 条 -> {OUT_Q}")
    print(f"  覆盖实体 {len(set(q['target_director'] for q in qs))} 个")
    print()
    print("样例：")
    for q in qs[:5]:
        print(f"  {q['query'][:44]:<46} -> {q['target_director']}")
    print("\n### CORPUS_V19_DONE")


if __name__ == "__main__":
    main()
