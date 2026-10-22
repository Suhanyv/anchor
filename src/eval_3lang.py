"""
三语互通评测：中 / 日 / 英 三种说法，能否都找到同一批英文文档

背景（用户定的议程 ②）：提示词互通 = 中日英语言互通。

设计
----
不翻译任何文档，只在 **query 侧**加日文，就能测出三语对齐程度：
    中文 query ─┐
    日文 query ─┼→ 同一批英文文档 → hit@1 对比
    英文 query ─┘

重要声明
--------
英文 query 用的是 style_tags（如 "deep focus, low-angle shots"），
而这些短语**逐字出现在文档里**，所以英文那组有明显词面重叠优势，
它是**上限参考**，不能与中日两组直接比较。
中日两组都没有这个词面优势，两者之间才可直接比。

输出
----
bench/eval_3lang.json
"""
import json
import os
import random

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v7.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-v7")
OUT = os.path.join(ROOT, "bench", "eval_3lang.json")
MAXLEN = 128

# ------------------------------------------------------------------ 日文对照
# 中文关键词 -> 日文（覆盖出现频次 >= 6 的词，约 95 个 + 东方影像/机制补充）
JA = {
    "对称": "対称", "自然光": "自然光", "克制": "抑制の効いた", "群像": "群像",
    "手持": "手持ちカメラ", "巴洛克": "バロック", "朴素": "素朴", "黑白": "モノクロ",
    "几何": "幾何学的", "长镜": "長回し", "表现主义": "表現主義", "纪实": "ドキュメンタリー",
    "诡异": "不気味", "冷面": "無表情", "极简": "ミニマル", "烛光": "ろうそくの光",
    "日光": "日光", "镜像": "鏡像", "静默": "静寂", "空旷": "がらんとした",
    "烈日": "炎天下", "仪式": "儀式", "高饱和": "高彩度", "抒情": "叙情的",
    "情节剧": "メロドラマ", "写实": "写実的", "家庭": "家庭", "日常": "日常",
    "留白": "余白", "一角": "一角", "半边": "半辺", "贴着边角": "端に寄せた",
    "造作": "人工的な", "红绿": "赤と緑", "院体": "院体画", "工细": "細密",
    "绢本": "絹本", "工笔": "工筆", "重彩": "濃彩", "白描": "白描",
    "手卷": "巻物", "长卷": "長巻", "横向": "横長", "冷峻": "冷徹",
    "深焦": "ディープフォーカス", "窥视": "覗き見", "高对比": "高コントラスト",
    "逆光": "逆光", "暖光": "暖かい光", "梦境": "夢の中", "金调": "金色の調子",
    "秋色": "秋の色", "长镜头": "長回し", "雨夜": "雨の夜", "哑色": "くすんだ色",
    "宏大": "壮大", "冷蓝": "冷たい青", "孤独": "孤独", "尘土": "土埃",
    "冷灰": "冷たい灰色", "街景": "街の風景", "历史感": "歴史の重み",
    "黑白新写实": "モノクロのネオレアリズモ", "战后废墟": "戦後の廃墟",
    "疏离": "疎外感", "现代性": "現代性", "衰败": "衰退", "黄昏": "夕暮れ",
    "平凡": "平凡", "废墟": "廃墟", "拼贴": "コラージュ", "碎片": "断片",
    "中产": "中産階級", "冷光": "冷たい光", "自然": "自然", "冷峻村庄": "冷たい村",
    "精准构图": "正確な構図", "公路": "街道", "剪影": "シルエット", "灵性": "霊性",
    "象征": "象徴", "雾": "霧", "大红": "真っ赤", "超现实": "シュール",
    "荒诞": "不条理", "巨构": "巨大構造", "粗粝": "ざらついた", "雨": "雨",
    "末世": "終末", "考究": "凝った", "水": "水", "寓言": "寓話",
    "人文": "ヒューマン", "感官": "官能的", "沉思": "瞑想", "元素极少": "要素が極少",
    # 东方影像
    "水墨": "水墨", "青绿": "青緑", "矿物色": "鉱物顔料", "金线": "金線",
    "雾江": "霧の川", "孤舟": "一艘の小舟", "远山": "遠山", "年画": "年画",
    "木版": "木版", "民俗": "民俗", "皮影": "影絵", "透光": "透過光",
    "笔触": "筆致", "雾江远景": "霧の川の遠景", "极长镜头": "超長回し",
    "灰绿": "灰緑", "山雾": "山霧", "飘": "たなびく",
    # 机制
    "物件变凶器": "凶器になる日用品", "发光的牛奶": "光る牛乳",
    "日常物的威胁": "日常物の脅威", "画框嵌套": "額縁の入れ子",
    "远摄窥视": "望遠の覗き", "一格格窗户": "窓の桟", "客厅里的尸体": "居間の死体",
    "表面正常": "表面は正常", "把恐怖当家具": "恐怖を家具にする",
    "螺旋": "螺旋", "垂直恐惧": "垂直の恐怖", "往下掉的眩晕": "落ちるめまい",
    "普通人被误认": "一般人が誤認される", "官僚荧光灯": "蛍光灯の官僚主義",
    "错误的人": "間違えられた人",
    # 常用补充
    "暖金": "暖かい金色", "暖调": "暖色调", "饱和": "彩度高め", "湿润": "湿った",
    "都市": "都市", "乡野": "田園", "雪": "雪", "海": "海", "夜": "夜",
}

# 完整对照表在 ja_lexicon.py（单一来源）。这里 update 一次，覆盖为全量 401 词。
from ja_lexicon import JA as _JA_FULL  # noqa: E402

JA.update(_JA_FULL)

T_ZH = ["{kw}，要那种感觉", "{kw} 这种怎么描述", "想找{kw}那种", "{kw} 相关的风格叫什么"]
T_JA = ["{kw} な感じがほしい", "{kw} ってどう表現する", "{kw} っぽい雰囲気",
        "{kw} のスタイルは何て言う"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class Enc:
    def __init__(self, path):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.enc = AutoModel.from_pretrained(path).eval()
        for p in self.enc.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def __call__(self, texts, prefix, bs=32):
        out = []
        for i in range(0, len(texts), bs):
            b = self.tok([prefix + t for t in texts[i:i + bs]], padding=True,
                         truncation=True, max_length=MAXLEN, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()


def build(corpus, seed=31):
    """为能覆盖到 >=2 个已翻译关键词的组，生成中/日/英三种 query"""
    rnd = random.Random(seed)
    groups = {}
    for d in corpus:
        if d.get("domain") not in (None, "prompt_image"):
            continue
        k = (d["director"], d.get("facet", "base"))
        g = groups.setdefault(k, {"zh": None, "tags": None})
        if g["zh"] is None:
            g["zh"] = list(d.get("kw_zh") or [])
            g["tags"] = list(d.get("style_tags") or [])

    out = []
    for (director, facet), g in groups.items():
        zh_kw = g["zh"] or []
        ja_kw = [JA[w] for w in zh_kw if w in JA]
        if len(ja_kw) < 2 or len(zh_kw) < 2:
            continue
        n = min(2, len(zh_kw), len(ja_kw))
        zh_sel = rnd.sample(zh_kw, n)
        ja_sel = [JA[w] for w in zh_sel if w in JA]
        if len(ja_sel) < 2:
            continue
        tags = [t for t in (g["tags"] or []) if t][:2]
        out.append({
            "director": director, "facet": facet,
            "zh": rnd.choice(T_ZH).format(kw="、".join(zh_sel)),
            "ja": rnd.choice(T_JA).format(kw="、".join(ja_sel)),
            "en": rnd.choice(T_ZH).format(kw=", ".join(tags)) if tags else None,
        })
    return out


def hit1(enc, corpus, items, lang):
    docs = [d["text_semantic"] for d in corpus]
    de = enc(docs, "passage: ")
    qs, keep = [], []
    for it in items:
        if it.get(lang):
            qs.append(it[lang])
            keep.append(it)
    qe = enc(qs, "query: ")
    S = de @ qe.T
    directors = [d["director"] for d in corpus]
    ok = 0
    miss = []
    for qi, it in enumerate(keep):
        best = {}
        for j, d in enumerate(directors):
            if d not in best or S[j][qi] > best[d]:
                best[d] = float(S[j][qi])
        top = max(best.items(), key=lambda kv: kv[1])[0]
        if top == it["director"]:
            ok += 1
        else:
            miss.append((it[lang], it["director"], top))
    return ok, len(keep), miss


def main():
    corpus = load(CORPUS)
    items = build(corpus)
    print(f"corpus {len(corpus)} doc")
    print(f"可评测组 {len(items)} 个（需要该组至少 2 个关键词有日文对照）\n")

    if not items:
        print("没有可评测的组，日文对照覆盖不足")
        return

    print("样例：")
    for it in items[:3]:
        print(f"  导演 {it['director']} / {it['facet']}")
        print(f"    中: {it['zh']}")
        print(f"    日: {it['ja']}")
        print(f"    英: {it['en']}")
    print()

    enc = Enc(MODEL)
    rows = {}
    print("=" * 74)
    print(f"{'语言':<8} {'命中@1':>10} {'分母':>8}")
    print("=" * 74)
    for lang, name in (("zh", "中文"), ("ja", "日文"), ("en", "英文*")):
        ok, n, miss = hit1(enc, corpus, items, lang)
        rows[lang] = {"hit1": ok / n if n else 0, "n": n, "miss": miss[:15]}
        print(f"{name:<8} {ok/n:>9.1%} {n:>8}")
    print("=" * 74)
    print("英文* 用 style_tags，逐字出现在文档里，有明显词面优势，仅作上限参考；")
    print("      中日两组都没有该优势，二者可直接比较。")

    # 中日对照：同一批组里，日文比中文差多少
    print("\n=== 日文 vs 中文：差在哪 ===")
    ok_zh, n_zh, miss_zh = hit1(enc, corpus, items, "zh")
    ok_ja, n_ja, miss_ja = hit1(enc, corpus, items, "ja")
    print(f"  中文 {ok_zh}/{n_zh}   日文 {ok_ja}/{n_ja}   差 {(ok_zh-ok_ja)/n_zh*100:+.1f}pp")
    if miss_ja:
        print("  日文失败样例（前 8）：")
        for q, want, got in miss_ja[:8]:
            print(f"    {q[:34]:<36} 期望 {want[:22]:<24} 实得 {got[:22]}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"items": len(items), "results": {
            k: {"hit1": v["hit1"], "n": v["n"]} for k, v in rows.items()},
            "ja_misses": rows["ja"]["miss"]}, f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### EVAL_3LANG_DONE")


if __name__ == "__main__":
    main()
