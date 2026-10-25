"""
从采集到的 966 条 technique 里筛出「值得进索引」的候选

筛选逻辑
--------
1. **去掉已有覆盖**：我们的材质/工艺索引里已经有的英文词（bronze/marble/oil on canvas…）
2. **按材料家族分组**：金属 / 石材 / 陶瓷 / 纸与颜料 / 纺织 / 木 / 玻璃 / 复合
3. **优先中频**：极低频（只出现 1 次）多半是单件作品的特殊描述，噪声大；
   极高频（oil on canvas）已被覆盖
4. **优先视觉独特**：带工艺性词汇的（cloisonné, maiolica, marquetry, damascening）
   比"某材料上画某材料"更值得进库

产物
----
    打印分组候选，供人过一遍再写条目
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARVEST = os.path.join(ROOT, "data", "raw", "harvest_cle_v1.json")
RAW = os.path.join(ROOT, "data", "raw")


def load_existing_words():
    """把已有索引里出现过的英文材料词收集起来，用于去重。"""
    words = set()
    for fn, key in (("materials_v5.jsonl", "phrase"),
                    ("crafts_v4.jsonl", "phrase"),
                    ("subjects_v6.jsonl", "phrase")):
        p = os.path.join(RAW, fn)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            for w in re.findall(r"[a-zA-Z][a-zA-Z\-]+", (r.get(key) or "").lower()):
                if len(w) > 3:
                    words.add(w)
    return words


FAMILIES = {
    "金属": ["bronze", "gold", "silver", "iron", "steel", "copper", "brass",
             "tin", "lead", "gilt", "niello", "damascen", "damask"],
    "石材": ["marble", "limestone", "sandstone", "schist", "alabaster", "granite",
             "jasper", "onyx", "steatite", "slate", "quartz", "jade", "lapis"],
    "陶瓷": ["porcelain", "earthenware", "stoneware", "ceramic", "maiolica",
             "faience", "terracotta", "glaze", "celadon", "raku"],
    "纸与颜料": ["ink", "tempera", "watercolor", "gouache", "chalk", "charcoal",
                 "graphite", "pastel", "vellum", "parchment", "paper", "pigment"],
    "纺织": ["silk", "wool", "cotton", "linen", "velvet", "brocade", "tapestry",
             "embroidery", "damask", "lace", "felt", "carpet"],
    "木与漆": ["wood", "oak", "walnut", "lindenwood", "ebony", "lacquer", "bamboo",
               "boxwood", "pine", "cedar", "marquetry", "inlay"],
    "玻璃与珐琅": ["glass", "enamel", "cloisonn", "stained glass", "cameo",
                   "millefiori", "vitreous"],
    "复合与其它": ["ivory", "bone", "horn", "shell", "mother-of-pearl", "amber",
                   "coral", "wax", "plaster", "stucco", "resin", "tortoise"],
}


def family_of(term):
    t = term.lower()
    for fam, keys in FAMILIES.items():
        if any(k in t for k in keys):
            return fam
    return None


def main():
    h = json.load(open(HARVEST, encoding="utf-8"))
    tech = h["technique"]                      # [(term, count), ...]
    existing = load_existing_words()
    print(f"采集 technique {len(tech)} 种；已有索引英文词 {len(existing)} 个")

    buckets = {f: [] for f in FAMILIES}
    seen_norm = set()
    for term, cnt in tech:
        norm = re.sub(r"\s+", " ", term.strip().lower())
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        # 过滤：太短/太长/纯材料组合
        if len(term) < 4 or len(term) > 70:
            continue
        # 已经出现的词（能对上两个以上已有词）视为已覆盖
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]+", norm) if len(w) > 3]
        if words and sum(1 for w in words if w in existing) >= max(1, len(words) - 1):
            continue
        fam = family_of(term)
        if not fam:
            continue
        buckets[fam].append((term, cnt))

    print("\n=== 各家族候选（按频次，去重后）===")
    total = 0
    for fam, rows in buckets.items():
        rows.sort(key=lambda x: -x[1])
        # 取中频：频次 >= 2 的优先，再补 1 次的
        pick = [r for r in rows if r[1] >= 2][:14] + [r for r in rows if r[1] == 1][:6]
        total += len(pick)
        print(f"\n[{fam}]  候选 {len(rows)} 条，展示 {len(pick)} 条")
        for term, cnt in pick:
            print(f"   {cnt:>3}  {term}")

    print(f"\n合计展示 {total} 条")
    print("\n下一步：人工过一遍，把真正有视觉辨识度的挑出来写条目（含中文名）。")
    print("\n### CURATE_DONE")


if __name__ == "__main__":
    main()
