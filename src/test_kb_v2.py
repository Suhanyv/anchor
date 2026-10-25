"""知识库 v2 验证：新条目命中 + 老条目不退（与 test_kb_v1 同一套判据）"""
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
    ("crafts", "汝窑那种天青色，满身细开片", "汝窑"),
    ("crafts", "建窑茶盏，釉往下流像兔毛", "建窑"),
    ("crafts", "唐三彩，琥珀绿和奶油色流在一起", "唐三彩"),
    ("crafts", "定窑白瓷，口沿包着铜", "定窑"),
    ("crafts", "钧窑，天蓝里泛紫", "钧窑"),
    ("crafts", "哥窑的冰裂纹，金丝铁线", "哥窑"),
    ("crafts", "粉彩，粉红和绿的釉上彩", "粉彩"),
    ("crafts", "青花勾线，里面填釉上彩", "斗彩"),
    ("crafts", "铜器上鎏金，凸起处磨掉了", "鎏金"),
    ("crafts", "景泰蓝，铜丝掐出格子填珐琅", "掐丝珐琅"),
    ("crafts", "青铜上错金银，银丝嵌进去", "错金银"),
    ("crafts", "银片从背面敲出来，正面錾花", "錾刻"),
    ("crafts", "乌银嵌在刻线里，银底发亮", "乌银"),
    ("subjects", "墙上挂着一幅立轴，上下有绫边", "立轴"),
    ("subjects", "册页摊开，裱边比画宽", "册页"),
    ("subjects", "画在扇面上的山水，弧形", "扇面"),
    ("subjects", "墙上的壁画，颜料是矿物色", "壁画"),
    ("materials", "灰色的片岩，有一层层片理", "片岩"),
    ("materials", "雪花石膏薄得能透光", "雪花石膏"),
    ("materials", "石灰岩，表面粉白哑光", "石灰岩"),
    ("materials", "红砂岩，颗粒很粗", "砂岩"),
    ("materials", "花岗岩，黑白斑点结晶", "花岗岩"),
    ("materials", "和田玉，油脂光泽", "玉"),
    ("materials", "青金石，蓝底上有金色小点", "青金石"),
    ("materials", "象牙，米黄色有细纹", "象牙"),
    ("materials", "椴木雕的，刀痕很清楚", "椴木"),
]

CONTROL_CASES = [
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("subjects", "下雪的庭院里只有一行脚印", "雪中庭院"),
    ("crafts", "想要蓝晒那种感觉", "蓝晒"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "红纸剪成窗花，镂空的图案", "剪纸"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "拉丝金属表面的反光", "拉丝金属"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "青瓷釉在底部积成浅绿，全身开片", "青瓷釉"),
]

SETS = {
    "old": {"subjects": "subjects_v6.jsonl", "crafts": "crafts_v4.jsonl", "materials": "materials_v5.jsonl"},
    "new": {"subjects": "subjects_v7.jsonl", "crafts": "crafts_v5.jsonl", "materials": "materials_v6.jsonl"},
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

    print(f"{'':<12} {'v1':>8} {'v2':>8}")
    print("-" * 32)
    for g, lab in (("new", "本批新条目"), ("ctrl", "老条目(对照)")):
        print(f"{lab:<12} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    fails = [d for d in nd if d[0] == "new" and not d[5]]
    if fails:
        print(f"\n新条目未命中 {len(fails)} 条：")
        for _, kind, q, want, got, _, sc in fails:
            print(f"  [{kind:<9}] {q[:24]:<26} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")
    ctrl_fail = [d for d in nd if d[0] == "ctrl" and not d[5]]
    if ctrl_fail:
        print(f"\n⚠️ 对照退步 {len(ctrl_fail)} 条：")
        for _, kind, q, want, got, _, sc in ctrl_fail:
            print(f"  [{kind:<9}] {q[:24]:<26} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")
    else:
        print("\n对照组全部保持。")
    print("\n### KB_V2_VERIFY_DONE")


if __name__ == "__main__":
    main()
