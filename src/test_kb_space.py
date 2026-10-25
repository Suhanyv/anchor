"""天文批次验证：新条目 + 累计对照（含前三批与门槛标定用过的条目）"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import torch                                    # noqa: E402
import torch.nn.functional as F                 # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

MODEL = os.path.join(ROOT, "models/e5-director-c27")
RAW = os.path.join(ROOT, "data", "raw")

NEW_CASES = [
    ("subjects", "在太空中拍摄太阳的黑子", "太阳黑子"),
    ("subjects", "从卫星上看地球，云带和海洋", "地球"),
    ("subjects", "月面特写，环形山和很长的影子", "月面"),
    ("subjects", "土星环几乎是平视，很薄一条", "土星环"),
    ("subjects", "木星的条纹和一个大红斑", "木星"),
    ("subjects", "彗星，两条尾巴", "彗星"),
    ("subjects", "发射星云，中间有暗尘埃带", "星云"),
    ("subjects", "斜看过去的旋涡星系", "星系"),
    ("subjects", "黑洞，周围一圈被引力弯折的光", "黑洞"),
    ("subjects", "极光绿色帘幕挂在天上", "极光"),
    ("materials", "日全食时看到的日冕流束", "日冕"),
    ("materials", "球面上那条明暗交界线", "明暗交界线"),
    ("materials", "长曝光拍出来的星轨同心弧", "星轨"),
    ("materials", "光束里飘的微粒，别的都是黑的", "空间尘埃"),
    ("materials", "太阳耀斑，活动区上方一条亮带", "太阳耀斑"),
    ("materials", "真空里纯黑，星星是尖点不闪", "真空黑"),
]

CONTROL_CASES = [
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "下雪的庭院里只有一行脚印", "雪中庭院"),
    ("subjects", "墙上挂着一幅立轴", "立轴"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "汝窑那种天青色", "汝窑"),
    ("crafts", "景泰蓝，铜丝掐出格子", "掐丝珐琅"),
    ("crafts", "红纸剪成窗花", "剪纸"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "和田玉，油脂光泽", "玉"),
    ("materials", "霓虹灯管，光溢到墙上", "霓虹灯管"),
    ("materials", "雾大到看不见对岸", "雾"),
    ("materials", "天鹅绒，光吸进去", "天鹅绒"),
    ("materials", "青瓷釉积成浅绿，全身开片", "青瓷釉"),
]

SETS = {
    "old": {"subjects": "subjects_v8.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v8.jsonl"},
    "new": {"subjects": "subjects_v9.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v9.jsonl"},
}


def name_of(row):
    for k in row:
        if k.endswith("_zh"):
            return row[k]
    return "?"


def main():
    tok = AutoTokenizer.from_pretrained(MODEL)
    enc = AutoModel.from_pretrained(MODEL).eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    @torch.no_grad()
    def E(texts, prefix):
        out = []
        for i in range(0, len(texts), 32):
            b = tok([prefix + t for t in texts[i:i + 32]], padding=True,
                    truncation=True, max_length=128, return_tensors="pt")
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()

    def evaluate(tag):
        idx = {}
        for name, fn in SETS[tag].items():
            rows = [json.loads(l) for l in open(os.path.join(RAW, fn), encoding="utf-8") if l.strip()]
            idx[name] = (rows, E([r["text_semantic"] for r in rows], "passage: "))
        res = {"new": [0, 0], "ctrl": [0, 0]}
        detail = []
        for group, cases in (("new", NEW_CASES), ("ctrl", CONTROL_CASES)):
            for kind, q, want in cases:
                rows, emb = idx[kind]
                s = emb @ E([q], "query: ")[0]
                k = int(s.argmax())
                got = name_of(rows[k])
                ok = (got == want)
                res[group][0] += ok
                res[group][1] += 1
                detail.append((group, kind, q, want, got, ok, float(s[k])))
        return res, detail

    o, _ = evaluate("old")
    n, nd = evaluate("new")

    print(f"{'':<12} {'扩前':>8} {'扩后':>8}")
    print("-" * 30)
    for g, lab in (("new", "天文新条目"), ("ctrl", "累计对照")):
        print(f"{lab:<12} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    for group, lab in (("new", "新条目"), ("ctrl", "对照")):
        fails = [d for d in nd if d[0] == group and not d[5]]
        if fails:
            print(f"\n{lab}未命中 {len(fails)} 条：")
            for _, kind, q, want, got, _, sc in fails:
                print(f"  {q[:26]:<28} 期望 {want:<12} 实得 {got:<12} {sc:.3f}")
        elif group == "ctrl":
            print("\n对照组全部保持。")
    print("\n### KB_SPACE_VERIFY_DONE")


if __name__ == "__main__":
    main()
