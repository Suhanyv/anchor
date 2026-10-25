"""
知识库扩充验证：新条目查得到吗？老条目会被挤掉吗？

为什么要专门写这个
------------------
今天「磁铁」审计的教训：新加的实体可能抢走老查询（Street Photography 抢了 4 次）。
扩充知识库之后必须同时看两件事：

    新条目命中     补的东西真的能用
    老条目不退     补的东西没把原来的挤掉

任何一方退化，这次扩充就不算成功。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import numpy as np                                     # noqa: E402
import torch                                           # noqa: E402
import torch.nn.functional as F                        # noqa: E402
from transformers import AutoModel, AutoTokenizer       # noqa: E402

MODEL = os.path.join(ROOT, "models/e5-director-c27")
RAW = os.path.join(ROOT, "data", "raw")

# (索引, 中文查询, 期望名字)
NEW_CASES = [
    ("subjects", "一块碑上拓下来的拓片，字是白的", "拓片"),
    ("subjects", "一枚印章按在朱红印泥上", "篆刻"),
    ("subjects", "墙上挂着一面画了山水的团扇", "团扇"),
    ("subjects", "檐下挂着一排灯笼，纸糊的", "灯笼"),
    ("subjects", "屏风把房间隔开，绢面上画着人物", "屏风"),
    ("subjects", "下雪的庭院里只有一行脚印", "雪中庭院"),
    ("crafts", "螺钿嵌在黑漆里，颜色随角度变", "螺钿"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "红纸剪成窗花，镂空的图案", "剪纸"),
    ("crafts", "木版套色印的门神年画", "木版年画"),
    ("crafts", "竹篾编成的篮子", "竹编"),
    ("crafts", "漆器一层层罩上去，表面像湿的", "漆器"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "青瓷釉在底部积成浅绿，全身开片", "青瓷釉"),
    ("materials", "青铜锈成墨绿，凹处有绿锈", "铜"),
    ("materials", "亚麻粗布，褶皱很明显", "亚麻"),
]

CONTROL_CASES = [
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("crafts", "想要蓝晒那种感觉", "蓝晒"),
    ("crafts", "丝线绣出来的花，针脚很密", "丝绸刺绣"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "拉丝金属表面的反光", "拉丝金属"),
    ("materials", "湿混凝土地面，有积水", "湿混凝土"),
]

SETS = {
    "old": {"subjects": "subjects_v5.jsonl", "crafts": "crafts_v3.jsonl",
            "materials": "materials_v4.jsonl"},
    "new": {"subjects": "subjects_v6.jsonl", "crafts": "crafts_v4.jsonl",
            "materials": "materials_v5.jsonl"},
}


def name_of(row, key):
    for k in row:
        if k.endswith("_zh"):
            return row[k]
    return row.get("subject_zh") or row.get("craft_zh") or row.get("mat_zh") or "?"


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
            emb = E([r["text_semantic"] for r in rows], "passage: ")
            idx[name] = (rows, emb)
        res = {"new": [0, 0], "ctrl": [0, 0]}
        detail = []
        for group, cases in (("new", NEW_CASES), ("ctrl", CONTROL_CASES)):
            for kind, q, want in cases:
                rows, emb = idx[kind]
                qe = E([q], "query: ")[0]
                s = emb @ qe
                k = int(s.argmax())
                got = name_of(rows[k], kind)
                ok = (got == want)
                res[group][0] += ok
                res[group][1] += 1
                detail.append((group, kind, q, want, got, ok, float(s[k])))
        return res, detail

    old_res, old_detail = evaluate("old")
    new_res, new_detail = evaluate("new")

    print(f"{'':<10} {'扩前':>8} {'扩后':>8}")
    print("-" * 30)
    for g, label in (("new", "新条目"), ("ctrl", "老条目(对照)")):
        a, b = old_res[g], new_res[g]
        print(f"{label:<10} {a[0]}/{a[1]:<6} {b[0]}/{b[1]:<6}")

    print("\n=== 扩后逐条 ===")
    for g, kind, q, want, got, ok, sc in new_detail:
        mark = "✅" if ok else "❌"
        print(f"  {mark} [{kind:<9}] {q[:26]:<28} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")

    print("\n判读：新条目命中明显上升、且老条目不退，才算成功。")
    print("\n### KB_VERIFY_DONE")


if __name__ == "__main__":
    main()
