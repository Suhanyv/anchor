"""
Wikidata 采集中英双语词表 v2：合并成一个查询，只发一次请求

为什么改
--------
v1 分四类各发一次 -> 全部 429（"Aggressively rate-limiting to 1 req / min"）。
那就把四个根节点用 VALUES 合进一条 SPARQL，一次拿完。

限流应对
--------
请求之间至少等 70 秒；失败重试 3 次，间隔递增。
宁可慢，也不要把 IP 打到被封。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT_RAW = r"E:\external\research"
OUT_AGG = r"F:\llm\data\raw\harvest_wd_v1.json"
SPARQL = "https://query.wikidata.org/sparql"
UA = "anchor-vocab-harvest/1.0 (research; local use)"

ROOTS = {
    "Q214609": ("material", "材料"),
    "Q1114448": ("craft", "工艺"),
    "Q968159": ("art_movement", "艺术流派"),
    "Q380344": ("technique", "技法"),
}

QUERY = """
SELECT DISTINCT ?root ?item ?en ?zh WHERE {
  VALUES ?root { wd:Q214609 wd:Q1114448 wd:Q968159 wd:Q380344 }
  ?item wdt:P279{1,3} ?root .
  OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en) = "en") }
  OPTIONAL { ?item rdfs:label ?zh FILTER(lang(?zh) = "zh") }
}
LIMIT 6000
"""


def run_query(retries=3):
    qs = urllib.parse.urlencode({"query": QUERY, "format": "json"})
    url = f"{SPARQL}?{qs}"
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA,
                          "Accept": "application/sparql-results+json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            wait = 70 * attempt
            print(f"  第 {attempt} 次：HTTP {e.code}，等 {wait}s 再试")
            if attempt < retries:
                time.sleep(wait)
        except Exception as e:  # noqa: BLE001
            wait = 30 * attempt
            print(f"  第 {attempt} 次：{type(e).__name__}，等 {wait}s 再试")
            if attempt < retries:
                time.sleep(wait)
    return None


def main():
    os.makedirs(OUT_RAW, exist_ok=True)
    print("=== 一次查询拿四类 ===")
    data = run_query()
    if not data:
        print("  拿不到。Wikidata 在这台机器上被限流或不通。")
        print("\n### WD_HARVEST_V2_FAILED")
        return

    buckets = {k: [] for k in ROOTS}
    seen = {k: set() for k in ROOTS}
    for b in data["results"]["bindings"]:
        qid = b["root"]["value"].rsplit("/", 1)[-1]
        if qid not in ROOTS:
            continue
        key = ROOTS[qid][0]
        en = (b.get("en") or {}).get("value", "").strip()
        zh = (b.get("zh") or {}).get("value", "").strip()
        item = b["item"]["value"].rsplit("/", 1)[-1]
        if not (en or zh):
            continue
        dedup = (en.lower(), zh)
        if dedup in seen[key]:
            continue
        seen[key].add(dedup)
        buckets[key].append({"qid": item, "en": en, "zh": zh})

    total = 0
    for qid, (key, zh_name) in ROOTS.items():
        rows = buckets[key]
        total += len(rows)
        both = sum(1 for r in rows if r["en"] and r["zh"])
        print(f"  {zh_name:<6} {len(rows):>4} 条（中英都有 {both}）")
        with open(os.path.join(OUT_RAW, f"wikidata_{key}.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)

    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump({"source": "Wikidata SPARQL, CC0",
                   "roots": {k: v for k, v in ROOTS.items()},
                   "buckets": buckets}, f, ensure_ascii=False, indent=1)

    print(f"\n合计 {total} 条 -> {OUT_AGG}")
    print("\n=== 抽样：中英都有的前 10（每类）===")
    for key, rows in buckets.items():
        both = [r for r in rows if r["en"] and r["zh"]][:10]
        print(f"\n  [{key}] {len(rows)} 条")
        for r in both:
            print(f"    {r['zh']:<14} {r['en']}")
    print("\n### WD_HARVEST_V2_DONE")


if __name__ == "__main__":
    main()
