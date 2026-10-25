"""知识库 v4 验证：现代材质 + 自然元素（24 项新条目 / 16 条累计对照）"""
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
    ("materials", "粉色霓虹灯管，光溢到旁边的墙上", "霓虹灯管"),
    ("materials", "厚亚克力的边缘透光", "亚克力"),
    ("materials", "一整面镜子，倒影没有纵深", "镜面"),
    ("materials", "墙缝里藏了灯带，光点一颗颗的", "LED 灯带"),
    ("materials", "清水混凝土，模板的板痕和对拉孔都在", "清水混凝土"),
    ("materials", "抛光不锈钢把房间反射成一团糊的", "不锈钢"),
    ("materials", "磨砂玻璃后面有个人影，只看得出明暗", "磨砂玻璃"),
    ("materials", "电镀铬，高光很硬，曲面上的反射拉变形了", "电镀铬"),
    ("materials", "树脂浇注，里面封着东西", "树脂"),
    ("materials", "哑光黑橡胶，完全不反光", "橡胶"),
    ("materials", "刚下过雨的沥青路面，天上映在里面", "沥青"),
    ("materials", "喷漆的钢板，边角掉漆露出灰底", "喷漆钢"),
    ("materials", "雾大到看不见对岸", "雾"),
    ("materials", "浪打碎了，后面那面还是绿的", "浪"),
    ("materials", "干沙被风吹成一片一片地移动", "沙"),
    ("materials", "火苗没有硬边，但打出来的光很硬", "火"),
    ("materials", "烟被侧光照到，只看得到亮的那一边", "烟"),
    ("materials", "雨只有在穿过光的时候才看得见", "雨"),
    ("materials", "冰里有气泡，裂纹停在某个面上", "冰"),
    ("materials", "雪下得很密，把所有边缘都soft掉了", "雪"),
    ("materials", "光柱里飘着灰尘", "尘"),
    ("materials", "水面碎成很多小硬光点", "水面"),
    ("materials", "云的层次，只有最近的一层被照亮", "云"),
    ("materials", "树叶的影子投在墙上，边缘很软", "树影"),
]

CONTROL_CASES = [
    ("subjects", "一个中世纪骑士骑着马", "中世纪骑士"),
    ("subjects", "两个剑客在竹林里对峙", "武侠竹林"),
    ("subjects", "一个人拿起桌上的竹简", "简牍"),
    ("subjects", "墙上挂着一幅立轴，上下有绫边", "立轴"),
    ("crafts", "想要蓝晒那种感觉", "蓝晒"),
    ("crafts", "青花瓷瓶，钴蓝在釉下", "青花瓷"),
    ("crafts", "汝窑那种天青色，满身细开片", "汝窑"),
    ("crafts", "景泰蓝，铜丝掐出格子填珐琅", "掐丝珐琅"),
    ("crafts", "挂毯，纬线织出来的，色块之间有缝", "缂织"),
    ("materials", "画面边缘压暗，四角发黑", "暗角"),
    ("materials", "拉丝金属表面的反光", "拉丝金属"),
    ("materials", "宣纸的纤维，墨洇开一点", "宣纸"),
    ("materials", "青瓷釉在底部积成浅绿，全身开片", "青瓷釉"),
    ("materials", "和田玉，油脂光泽", "玉"),
    ("materials", "绒面吸光，顺着一个方向摸会变深", "天鹅绒"),
    ("materials", "石灰灰泥还没干的时候塑出形", "灰泥"),
]

SETS = {
    "old": {"subjects": "subjects_v7.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v7.jsonl"},
    "new": {"subjects": "subjects_v7.jsonl", "crafts": "crafts_v6.jsonl", "materials": "materials_v8.jsonl"},
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

    print(f"{'':<14} {'v3':>8} {'v4':>8}")
    print("-" * 34)
    for g, lab in (("new", "本批新条目"), ("ctrl", "累计老条目")):
        print(f"{lab:<14} {o[g][0]}/{o[g][1]:<6} {n[g][0]}/{n[g][1]:<6}")

    for group, lab in (("new", "新条目"), ("ctrl", "对照")):
        fails = [d for d in nd if d[0] == group and not d[5]]
        if fails:
            print(f"\n{lab}未命中 {len(fails)} 条：")
            for _, kind, q, want, got, _, sc in fails:
                print(f"  {q[:26]:<28} 期望 {want:<12} 实得 {got:<12} {sc:.3f}")
    if not [d for d in nd if d[0] == "ctrl" and not d[5]]:
        print("\n对照组全部保持。")
    print("\n### KB_V4_VERIFY_DONE")


if __name__ == "__main__":
    main()
