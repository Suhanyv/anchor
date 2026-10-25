"""知识库 v3 验证：本批新条目 + 累计老条目（两套对照）"""
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
    ("crafts", "铜胎上錾出坑，珐琅填进去烧", "内填珐琅"),
    ("crafts", "教堂窗户，彩色玻璃用铅条拼的", "彩色玻璃"),
    ("crafts", "陶器表面有一层金属膜，虹彩", "光泽陶"),
    ("crafts", "石英胎薄壁，白化妆土，釉下彩", "熔块陶"),
    ("crafts", "日本瓷盘，蓝线勾边填釉上彩，中间留白", "锅岛烧"),
    ("crafts", "不同颜色的木片拼在一起，靠木纹作画", "细木镶嵌"),
    ("crafts", "竹筒刻字，留青", "竹刻"),
    ("crafts", "木雕上过彩，凸起处的颜料磨掉了", "彩绘木雕"),
    ("crafts", "挂毯，纬线织出来的，色块之间有缝", "缂织"),
    ("crafts", "丝绸底子上浮着金线", "妆花锦"),
    ("materials", "斜纹组织，图案织进去的不是画上去的", "萨米特锦"),
    ("materials", "绒面吸光，顺着一个方向摸会变深", "天鹅绒"),
    ("materials", "同色的暗花，只靠反光差看出图案", "花缎"),
    ("materials", "石灰灰泥还没干的时候塑出形", "灰泥"),
    ("materials", "木头上的白色粉底，颜料磨掉就露出来", "石膏底"),
    ("materials", "胡桃瘿木，纹理是乱的", "胡桃瘿木"),
    ("materials", "无花果木，纹细颜色浅", "无花果木"),
    ("materials", "骨头切成的薄片贴在木头上", "骨贴面"),
    ("materials", "蛤壳内壁画了画，还能看到珠光", "蛤壳"),
    ("materials", "龟甲半透明，底下垫了亮色", "龟甲"),
    ("materials", "琥珀，里面有小虫子那种内含物", "琥珀"),
    ("materials", "铅条玻璃，玻璃本身不平", "铅条玻璃"),
]

# 累计对照：v1 + v2 两批所有条目
CONTROL_CASES = [
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("subjects", "下雪的庭院里只有一行脚印", "雪中庭院"),
    ("subjects", "墙上挂着一幅立轴，上下有绫边", "立轴"),
    ("subjects", "画在扇面上的山水，弧形", "扇面"),
    ("crafts", "想要蓝晒那种感觉", "蓝晒"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "汝窑那种天青色，满身细开片", "汝窑"),
    ("crafts", "唐三彩，琥珀绿和奶油色流在一起", "唐三彩"),
    ("crafts", "景泰蓝，铜丝掐出格子填珐琅", "掐丝珐琅"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "拉丝金属表面的反光", "拉丝金属"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "青瓷釉在底部积成浅绿，全身开片", "青瓷釉"),
    ("materials", "和田玉，油脂光泽", "玉"),
]

SETS = {
    "old": {"subjects": "subjects_v7.jsonl", "crafts": "crafts_v5.jsonl", "materials": "materials_v6.jsonl"},
    "new": {"subjects": "subjects_v7.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v7.jsonl"},
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

    print(f"{'':<14} {'v2':>8} {'v3':>8}")
    print("-" * 34)
    for g, lab in (("new", "本批新条目"), ("ctrl", "累计老条目")):
        print(f"{lab:<14} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    for group, lab in (("new", "新条目"), ("ctrl", "对照")):
        fails = [d for d in nd if d[0] == group and not d[5]]
        if fails:
            print(f"\n{lab}未命中 {len(fails)} 条：")
            for _, kind, q, want, got, _, sc in fails:
                print(f"  [{kind:<9}] {q[:24]:<26} 期望 {want:<10} 实得 {got:<10} {sc:.3f}")
    if not [d for d in nd if d[0] == "ctrl" and not d[5]]:
        print("\n对照组全部保持。")
    print("\n### KB_V3_VERIFY_DONE")


if __name__ == "__main__":
    main()
