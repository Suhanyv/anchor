"""
韩语 / 德语现状测评：先测，别先翻词表

背景
----
用户最初的需求是「中文 query → 日语、德语、韩语等多种语言」。
目前只做了中日英：日文从 49.1% 训练到 89.7%。
韩语、德语**完全没碰过**。

为什么不先做词表
----------------
日语那次的教训：先测发现 49.1%（语言-国籍混淆），才知道该补什么。
如果直接翻 401 个词做韩/德对照表，可能翻完发现根本不是词表问题。

本脚本
------
用同一批概念（10 个，取自场景基准），写成 中 / 日 / 韩 / 德 四种语言，
对 corpus_v14 + e5-director-c18 检索，看各自命中率。
不训练、不改数据，只观察。
"""
import json
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v16.jsonl")
MODEL = os.path.join(ROOT, "models", "e5-director-c18")
OUT = os.path.join(ROOT, "bench", "eval_kode.json")

# (概念, 中文, 日文, 韩文, 德文, [可接受答案])
CASES = [
    ("霓虹夜色", "霓虹夜色，慢门，暧昧的感觉",
     "ネオンの夜、スローシャッター、曖昧な感じ",
     "네온 불빛의 밤, 슬로 셔터, 아련한 느낌",
     "Neonnacht, Langzeitbelichtung, ein Gefühl von Ambiguität",
     ["Wong Kar-wai"]),

    ("雨夜街道", "雨夜的街道，霓虹倒映在积水里",
     "雨の夜の街、ネオンが水たまりに映る",
     "비 오는 밤 거리, 네온이 물웅덩이에 비친다",
     "Regennasse Straße bei Nacht, Neon spiegelt sich in Pfützen",
     ["Wong Kar-wai", "Ridley Scott", "Martin Scorsese"]),

    ("荒原骑士", "广阔荒原上只有一个孤独骑士，低地平线",
     "広大な荒野に一人だけの騎士、低い地平線",
     "광활한 황야에 홀로 있는 기사, 낮은 지평선",
     "Ein einsamer Ritter in einer weiten Ödnis, tiefer Horizont",
     ["Denis Villeneuve", "Christopher Nolan", "Terrence Malick"]),

    ("偷看被发现", "女骑士骑马慢慢走向镜头，有人蹲在草丛里偷看她，她突然发现了",
     "女騎士が馬でゆっくりカメラへ、草むらに隠れて覗いている、彼女が気づく",
     "여기사가 말을 타고 천천히 카메라로 온다, 풀숲에 숨어 훔쳐본다, 그녀가 눈치챈다",
     "Eine Ritterin reitet langsam auf die Kamera zu, jemand beobachtet sie aus dem Gras, sie bemerkt es",
     ["Alfred Hitchcock"]),

    ("枝叶遮挡", "从树枝后面看过去，前景有草叶遮挡",
     "木の枝の後ろから見る、手前に草が遮っている",
     "나뭇가지 뒤에서 바라본다, 앞쪽에 풀잎이 가린다",
     "Der Blick von hinter Zweigen, Grashalme verdecken den Vordergrund",
     ["Alfred Hitchcock"]),

    ("杯子威胁", "一个杯子放在桌上，光从下面打上来，让人紧张",
     "テーブルの上のコップ、下から光が当たる、緊張感",
     "테이블 위의 컵 하나, 빛이 아래에서 올라온다, 긴장감",
     "Ein Glas auf dem Tisch, das Licht kommt von unten, beunruhigend",
     ["Alfred Hitchcock"]),

    ("雾江孤舟", "云雾里的江面，一条小船，远山一层层没入雾中",
     "霧の川、小舟が一艘、遠山が幾重にも霧に沈む",
     "안개 낀 강, 작은 배 하나, 먼 산이 겹겹이 안개에 잠긴다",
     "Nebliger Fluss, ein kleines Boot, ferne Berge stufenweise im Nebel",
     ["Misty River Lone Boat"]),

    ("留白", "大片空白，中间只有一个很小的东西，四周什么都没有",
     "大きな余白、中央に非常に小さなもの、周りには何もない",
     "큰 여백, 가운데 아주 작은 것 하나, 주위에는 아무것도 없다",
     "Viel Leerraum, ein winziges Ding in der Mitte, sonst nichts",
     ["Liubai Negative Space"]),

    ("院体花鸟", "绢本上画的花鸟，笔很细，颜色很淡",
     "絹本に描かれた花鳥、筆が非常に細い、色が淡い",
     "비단에 그린 꽃과 새, 붓질이 매우 가늘다, 색이 옅다",
     "Blumen und Vögel auf Seide, sehr feiner Pinselstrich, blasse Farben",
     ["Song Academy Realism"]),

    ("对称对峙", "两个人隔着桌子面对面坐着，房间完全对称",
     "二人が机を挟んで向かい合う、部屋は完全な対称",
     "두 사람이 탁자를 사이에 두고 마주 앉아 있다, 방이 완전히 대칭",
     "Zwei Menschen sitzen sich am Tisch gegenüber, der Raum ist völlig symmetrisch",
     ["Park Chan-wook", "Stanley Kubrick", "Wes Anderson"]),
]

LANGS = [("zh", 1, "中文"), ("ja", 2, "日文"), ("ko", 3, "韩文"), ("de", 4, "德文")]


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
                         truncation=True, max_length=128, return_tensors="pt")
            h = self.enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()


def main():
    corpus = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    dirs = [d["director"] for d in corpus]
    print(f"corpus {len(corpus)} doc / 概念 {len(CASES)} 个\n")

    enc = Enc(MODEL)
    de = enc([d["text_semantic"] for d in corpus], "passage: ")

    print(f"{'语言':<6} {'top1':>6} {'top3':>6} {'top5':>6}   top1 平均分")
    print("-" * 60)
    summary = {}
    detail = {}
    for code, idx, name in LANGS:
        qs = [c[idx] for c in CASES]
        qe = enc(qs, "query: ")
        ok1 = ok3 = ok5 = 0
        top1scores = []
        misses = []
        for qi, (case, q) in enumerate(zip(CASES, qs)):
            accept = case[5]
            s = de @ qe[qi]
            best = {}
            for j, d in enumerate(dirs):
                if d not in best or s[j] > best[d]:
                    best[d] = float(s[j])
            rk = sorted(best.items(), key=lambda kv: -kv[1])
            names = [k for k, _ in rk]
            ranks = [names.index(a) + 1 for a in accept if a in names]
            r = min(ranks) if ranks else 999
            if r == 1:
                ok1 += 1
            if r <= 3:
                ok3 += 1
            if r <= 5:
                ok5 += 1
            top1scores.append(rk[0][1])
            if r > 3:
                misses.append((case[0], accept[0], rk[0][0], r))
        n = len(CASES)
        print(f"{name:<6} {ok1/n:>5.0%} {ok3/n:>5.0%} {ok5/n:>5.0%}   {np.mean(top1scores):.3f}")
        summary[code] = {"top1": ok1 / n, "top3": ok3 / n, "top5": ok5 / n,
                         "mean_top1_score": float(np.mean(top1scores))}
        detail[code] = misses

    print("\n=== 各语言落空的概念（>3 名）===")
    for code, idx, name in LANGS:
        ms = detail[code]
        if not ms:
            print(f"  {name}: 无")
            continue
        print(f"  {name}:")
        for concept, want, got, r in ms:
            print(f"    {concept:<10} 期望 {want[:22]:<24} 实得 {got[:22]:<24} 第 {r}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"summary": summary,
                   "detail": {k: [{"concept": a, "want": b, "got": c, "rank": d}
                                  for a, b, c, d in v] for k, v in detail.items()}},
                  f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### KODE_EVAL_DONE")


if __name__ == "__main__":
    main()
