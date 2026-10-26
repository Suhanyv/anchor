"""
门槛标定：用短句 + 自然句重新定四个通道的阈值

问题
----
现有门槛（题材 0.36 / 工艺 0.44 / 材质 0.40）是**用长模板句调出来的**。
实测短句过不了：

    "汝窑天青色"            -> 工艺没触发
    "青花瓷瓶，钴蓝在釉下"   -> 工艺没触发
    "竹篾编成的篮子"        -> 工艺没触发

而人说话就是短的。这正好对上那个 86%(模板句) vs 41%(自然句) 的落差。

方法
----
1. 正样本：短句，**明确该命中某个实体**
2. 负样本：纯风格/抽象描述，**不该命中任何内容通道**
3. 对每个通道，统计正/负样本的分数分布
4. 选使 (正样本触发率 − 负样本误触发率) 最大的阈值

关键约束
--------
**负样本不能少。** 门槛调低的代价是所有查询都变成磁铁，
所以必须同时看"该触发的触发了吗"和"不该触发的触发了吗"。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v8.jsonl")
K = os.path.join(ROOT, "data/raw/crafts_v6.jsonl")
MT = os.path.join(ROOT, "data/raw/materials_v8.jsonl")

# 正样本：(通道, 短句, 期望实体)
POS = [
    ("subject", "竹简", "简牍"),
    ("subject", "帛书", "帛书"),
    ("subject", "团扇", "团扇"),
    ("subject", "灯笼", "灯笼"),
    ("subject", "屏风", "屏风"),
    ("subject", "立轴", "立轴"),
    ("subject", "册页", "册页"),
    ("subject", "扇面", "扇面"),
    ("subject", "骑士", "中世纪骑士"),
    ("subject", "竹林", "武侠竹林"),
    ("craft", "汝窑", "汝窑"),
    ("craft", "青花", "青花瓷"),
    ("craft", "拓片", "拓片"),
    ("craft", "篆刻", "篆刻"),
    ("craft", "剪纸", "剪纸"),
    ("craft", "年画", "木版年画"),
    ("craft", "螺钿", "螺钿"),
    ("craft", "景泰蓝", "掐丝珐琅"),
    ("craft", "唐三彩", "唐三彩"),
    ("craft", "蓝晒", "蓝晒"),
    ("material", "宣纸", "宣纸"),
    ("material", "青瓷釉", "青瓷釉"),
    ("material", "和田玉", "玉"),
    ("material", "天鹅绒", "天鹅绒"),
    ("material", "霓虹灯管", "霓虹灯管"),
    ("material", "镜面", "镜面"),
    ("material", "雾", "雾"),
    ("material", "冰", "冰"),
    ("material", "雪", "雪"),
    ("material", "沥青", "沥青"),
    ("scene", "卧室", "卧室"),
    ("scene", "厨房", "厨房"),
    ("scene", "沙滩", "沙滩"),
    ("scene", "地铁站", "地铁站台"),
    ("scene", "天台", "天台"),
    ("scene", "巷子", "巷子"),
    ("scene", "病房", "病房"),
    ("scene", "教室", "教室"),
]

# 负样本：纯风格 / 抽象 / 情绪 —— 不该命中任何内容通道
NEG = [
    "霓虹夜色，慢门，暧昧的感觉",
    "像王家卫那样",
    "紧张一点，让人喘不过气",
    "孤独感，空旷",
    "复古，颗粒感很强",
    "高级，克制，冷淡",
    "温暖，午后",
    "干净，极简",
    "混乱，失序",
    "梦一样的质感",
    "压迫感",
    "安静，什么也没发生",
    "电影感，宽银幕",
    "柔光，浅景深",
    "低饱和，暗调",
    "旧照片的味道",
    "手写体，粗糙",
    "工业风",
    "潮湿",
    "刺眼",
]


# --- 统一路径：以节点默认值为准，避免脚本与部署漂移 ---
try:
    from paths import DEFAULTS as _PATHS
    M, C = _PATHS["model"], _PATHS["corpus"]
    S, K, MT = _PATHS["subjects"], _PATHS["crafts"], _PATHS["materials"]
except Exception:
    pass


def main():
    def probe(q):
        items, mode, subj, dom, craft, mat = N._rank(
            q, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
        return {
            "style": (items[0]["score"], items[0].get("director_zh") or items[0]["director"]),
            "subject": (subj["score"], subj["zh"], subj.get("type")) if subj else None,
            "scene": ((subj.get("scene_best") or {}).get("score"),
                      (subj.get("scene_best") or {}).get("zh")) if subj else None,
            "craft": (craft["score"], craft["zh"]) if craft else None,
            "material": (mat["score"], mat["zh"]) if mat else None,
        }

    print("=== 正样本：该触发的分数 ===")
    pos_scores = {k: [] for k in ("subject", "craft", "material", "scene")}
    for ch, q, want in POS:
        r = probe(q)
        key = "scene" if ch == "scene" else ch
        sc, got = (r[key][0], r[key][1]) if r[key] else (None, None)
        ok = "✅" if got == want else "❌"
        pos_scores[ch].append(sc or 0.0)
        print(f"  {ok} [{ch:<8}] {q:<8} 期望 {want:<10} 实得 {str(got):<10} {sc:.3f}"
              if sc is not None else f"  ❌ [{ch}] {q} 无")

    print("\n=== 负样本：不该触发的最高分 ===")
    neg_max = {"subject": 0.0, "craft": 0.0, "material": 0.0, "scene": 0.0}
    neg_rows = []
    for q in NEG:
        r = probe(q)
        row = {"q": q}
        for k in ("subject", "craft", "material", "scene"):
            v = r[k][0] if r[k] else 0.0
            row[k] = v or 0.0
            neg_max[k] = max(neg_max[k], v or 0.0)
        neg_rows.append(row)
    neg_rows.sort(key=lambda x: -max(x["subject"], x["craft"], x["material"], x["scene"]))
    for row in neg_rows[:10]:
        print(f"  {row['q']:<20} 题材 {row['subject']:.3f} 工艺 {row['craft']:.3f} "
              f"材质 {row['material']:.3f} 场景 {row['scene']:.3f}")

    print("\n=== 各通道分数分布 ===")
    print(f"{'通道':<10} {'正样本中位':>10} {'正样本最低':>10} {'负样本最高':>10} {'建议门槛':>10}")
    print("-" * 56)
    suggest = {}
    for k in ("subject", "craft", "material", "scene"):
        ps = sorted(pos_scores[k])
        med = ps[len(ps) // 2] if ps else 0
        lo = ps[0] if ps else 0
        nm = neg_max[k]
        # 建议门槛：负样本最高与正样本中位之间，偏保守（靠近负样本一侧 +0.02）
        cand = min(med, max(nm + 0.02, lo))
        suggest[k] = round(cand, 2)
        print(f"{k:<10} {med:>10.3f} {lo:>10.3f} {nm:>10.3f} {suggest[k]:>10.2f}")

    print("\n=== 建议 ===")
    cur = {"subject": N.SUBJECT_FLOOR, "craft": N.CRAFT_FLOOR,
           "material": N.MATERIAL_FLOOR, "scene": N.SCENE_FLOOR}
    for k in ("subject", "craft", "material", "scene"):
        print(f"  {k:<10} 现在 {cur[k]:.2f}  ->  建议 {suggest[k]:.2f}")

    out = os.path.join(ROOT, "bench", "floor_calibration.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"pos": POS, "neg": NEG, "neg_max": neg_max,
                   "suggest": suggest, "current": cur}, f, ensure_ascii=False, indent=1)
    print(f"\n-> {out}")
    print("\n### CALIBRATE_DONE")


if __name__ == "__main__":
    main()
