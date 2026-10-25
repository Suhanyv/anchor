"""
用 Wikidata 采集中英双语的「材质 / 工艺 / 流派」词表

为什么是 Wikidata
-----------------
前面试过的源：AIC 403、Met 410、Wikipedia 超时。
Wikidata 通了，而且它有两个别处没有的好处：

1. **自带中文标签** —— 不用我一条条翻译，避免译名混乱
2. **有类层级** —— 可以顺着 subclass-of 往下取，一次拿几百条

许可：Wikidata 是 CC0，可自由使用。

我们取什么：**只要词条标签（中英各一）**，不取任何描述正文。
和既有原则一致：只取词汇，不抄文本。

产物
----
    E:\\external\\research\\wikidata_<kind>.json
    F:\\llm\\data\\raw\\harvest_wd_v1.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT_RAW = r"E:\external\research"
OUT_AGG = r"F:\llm\data\raw\harvest_wd_v1.json"

SPARQL = "https://query.wikidata.org/sparql"
UA = "anchor-vocab-harvest/1.0 (research; contact: local)"

# 每类：根节点 QID、中文名、向下取的层数
ROOTS = [
    ("Q214609", "material", "材料"),          # material
    ("Q1114448", "craft", "工艺"),            # craft
    ("Q968159",  "art_movement", "艺术流派"),  # art movement
    ("Q380344",  "technique", "技法"),        # technique（艺术技法）
]


def sparql(query):
    qs = urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(f"{SPARQL}?{qs}",
                                 headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_class(root_qid, depth=3):
    """顺着 subclass-of 往下取 depth 层，要中英标签。"""
    q = f"""
SELECT DISTINCT ?item ?itemLabelEn ?itemLabelZh WHERE {{
  ?item wdt:P279{{1,{depth}}} wd:{root_qid} .
  OPTIONAL {{ ?item rdfs:label ?itemLabelEn FILTER(lang(?itemLabelEn) = "en") }}
  OPTIONAL {{ ?item rdfs:label ?itemLabelZh FILTER(lang(?itemLabelZh) = "zh") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
LIMIT 3000
"""
    data = sparql(q)
    rows = []
    for b in data["results"]["bindings"]:
        en = (b.get("itemLabelEn") or {}).get("value", "").strip()
        zh = (b.get("itemLabelZh") or {}).get("value", "").strip()
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        if en or zh:
            rows.append({"qid": qid, "en": en, "zh": zh})
    return rows


def main():
    os.makedirs(OUT_RAW, exist_ok=True)
    agg = {}
    for qid, key, zh in ROOTS:
        try:
            rows = fetch_class(qid, depth=3)
        except Exception as e:  # noqa: BLE001
            print(f"  {zh:<6} 失败: {type(e).__name__}: {str(e)[:60]}")
            continue
        # 去重
        seen, uniq = set(), []
        for r in rows:
            k = (r["en"].lower(), r["zh"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        agg[key] = uniq
        with open(os.path.join(OUT_RAW, f"wikidata_{key}.json"), "w", encoding="utf-8") as f:
            json.dump(uniq, f, ensure_ascii=False, indent=1)
        both = sum(1 for r in uniq if r["en"] and r["zh"])
        print(f"  {zh:<6} {len(uniq):>4} 条（中英都有 {both} 条）")
        time.sleep(1.0)

    if not agg:
        print("  一条都没拿到")
        return

    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump({"source": "Wikidata (CC0)", "roots": {k: v for k, v in ROOTS}},
                  f, ensure_ascii=False, indent=1)
        # 再存一份纯词表（方便下一步用）
    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)

    print("\n=== 抽样（每类前 12 条中英都有的）===")
    for key, rows in agg.items():
        both = [r for r in rows if r["en"] and r["zh"]][:12]
        print(f"\n  [{key}]")
        for r in both:
            print(f"    {r['zh']:<12} {r['en']}")

    total = sum(len(v) for v in agg.values())
    print(f"\n合计 {total} 条 -> {OUT_AGG}")
    print("\n### WD_HARVEST_DONE")


if __name__ == "__main__":
    main()
