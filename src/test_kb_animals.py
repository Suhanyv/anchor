"""动物批次验证：新条目 + 累计对照"""
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
    ("subjects", "一只猫坐在窗台上，尾巴在动", "猫"),
    ("subjects", "狗站着，耳朵先转过去", "狗"),
    ("subjects", "一只小鸟停在枝上，头一顿一顿地转", "鸟"),
    ("subjects", "鱼群一起转身", "鱼"),
    ("subjects", "马站着，一条后腿歇着", "马"),
    ("subjects", "鹿停在半路，抬头，两耳朝前", "鹿"),
    ("subjects", "一条蛇穿过干地", "蛇"),
    ("subjects", "熊四脚着地，肩膀比头高", "熊"),
    ("subjects", "兔子蹲着，耳朵往后贴，一动不动", "兔"),
    ("subjects", "鲸的背露出水面，水从身上淌下去", "鲸"),
    ("subjects", "章鱼的触手在卷曲，皮肤在变纹理", "章鱼"),
    ("subjects", "蝴蝶停在花上，翅膀慢慢开合", "蝴蝶"),
    ("materials", "毛皮，逆光里一根根毛都亮着", "毛皮"),
    ("materials", "羽毛一层层叠着，羽轴有一条亮线", "羽毛"),
    ("materials", "鳞片一片压一片，边缘都在反光", "鳞片"),
    ("materials", "兽眼，硬的湿高光", "兽眼"),
]

CONTROL_CASES = [
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "下雪的庭院里只有一行脚印", "雪中庭院"),
    ("subjects", "在太空中拍摄太阳的黑子", "太阳黑子"),
    ("subjects", "从卫星上看地球", "地球"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "汝窑那种天青色", "汝窑"),
    ("crafts", "景泰蓝，铜丝掐出格子", "掐丝珐琅"),
    ("crafts", "红纸剪成窗花", "剪纸"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "和田玉，油脂光泽", "玉"),
    ("materials", "霓虹灯管，光溢到墙上", "霓虹灯管"),
    ("materials", "雾大到看不见对岸", "雾"),
    ("materials", "日全食时看到的日冕", "日冕"),
]

SETS = {
    "old": {"subjects": "subjects_v9.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v9.jsonl"},
    "new": {"subjects": "subjects_v10.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v10.jsonl"},
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
    for g, lab in (("new", "动物新条目"), ("ctrl", "累计对照")):
        print(f"{lab:<12} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    for group, lab in (("new", "新条目"), ("ctrl", "对照")):
        fails = [d for d in nd if d[0] == group and not d[5]]
        if fails:
            print(f"\n{lab}未命中 {len(fails)} 条：")
            for _, kind, q, want, got, _, sc in fails:
                print(f"  {q[:28]:<30} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")
        elif group == "ctrl":
            print("\n对照组全部保持。")
    print("\n### KB_ANIMALS_VERIFY_DONE")


if __name__ == "__main__":
    main()
