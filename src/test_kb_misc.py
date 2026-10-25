"""四类补充验证：新条目 + 累计对照"""
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
    ("一只猫坐在窗台上", "窗台"),
    ("脚跨过门槛的那一下", "门槛"),
    ("一段很长的台阶", "台阶"),
    ("从阳台上往下看", "阳台"),
    ("手扶着栏杆", "栏杆"),
    ("公园里一张空长椅", "长椅"),
    ("桌上只放着一个杯子", "桌面"),
    ("鸟停在树杈上", "树杈"),
    ("从过街天桥上走过去", "天桥"),
    ("在公交站等车", "公交站"),
    ("一辆自行车靠在墙边", "自行车"),
    ("列车进站，车门打开", "列车"),
    ("飞机停在跑道上", "飞机"),
    ("一条小船浮在静水上", "船"),
    ("摩托车停在路边，引擎还在响", "摩托车"),
    ("公交车里面，人都站着", "公交车"),
    ("路口的红绿灯在变", "红绿灯"),
    ("自动售货机在夜里亮着", "自动售货机"),
    ("路灯只照出一小圈", "路灯"),
    ("穿白大褂的医生", "医生"),
    ("戴安全帽的工人，身上都是灰", "工人"),
    ("背着书包的学生", "学生"),
    ("老人手背上的筋", "老人"),
    ("穿婚纱的新娘，头纱掀起来", "新娘"),
]

CONTROL_CASES = [
    # 只放题材索引里的条目 —— 这个脚本只查 subjects，查不到工艺/材质
    ("一个男孩和一个鲸鱼女孩在卧室里相拥", "卧室"),
    ("我和妹妹在沙滩上奔跑", "沙滩"),
    ("下雪的庭院里只有一行脚印", "雪中庭院"),
    ("在太空中拍摄太阳的黑子", "太阳黑子"),
    ("从卫星上看地球", "地球"),
    ("一只猫", "猫"),
    ("一个人拿起桌上的竹简", "简牍"),
    ("两个剑客在竹林里对峙", "武侠竹林"),
]

SETS = {"old": "subjects_v10.jsonl", "new": "subjects_v11.jsonl"}


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
        rows = [json.loads(l) for l in open(os.path.join(RAW, SETS[tag]), encoding="utf-8") if l.strip()]
        emb = E([r["text_semantic"] for r in rows], "passage: ")
        res = {"new": [0, 0], "ctrl": [0, 0]}
        detail = []
        for group, cases in (("new", NEW_CASES), ("ctrl", CONTROL_CASES)):
            for q, want in cases:
                s = emb @ E([q], "query: ")[0]
                k = int(s.argmax())
                got = name_of(rows[k])
                ok = (got == want)
                res[group][0] += ok
                res[group][1] += 1
                detail.append((group, q, want, got, ok, float(s[k])))
        return res, detail

    o, _ = evaluate("old")
    n, nd = evaluate("new")

    print(f"{'':<12} {'扩前':>8} {'扩后':>8}")
    print("-" * 30)
    for g, lab in (("new", "本批新条目"), ("ctrl", "累计对照")):
        print(f"{lab:<12} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    for group, lab in (("new", "新条目"), ("ctrl", "对照")):
        fails = [d for d in nd if d[0] == group and not d[5]]
        if fails:
            print(f"\n{lab}未命中 {len(fails)} 条：")
            for _, q, want, got, _, sc in fails:
                print(f"  {q[:26]:<28} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")
        elif group == "ctrl":
            print("\n对照组全部保持。")
    print("\n### KB_MISC_VERIFY_DONE")


if __name__ == "__main__":
    main()
