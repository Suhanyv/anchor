"""
从克利夫兰美术馆开放 API 采集材质/工艺词表（CC0）

为什么换到这个源
----------------
- Wikidata SPARQL：429 硬限流，等 7 分钟仍不通
- AIC：403 / Met：410 / Wikipedia：超时
- **Cleveland openaccess API：200，稳定**

它的每条作品带这几个字段，正好是我们要的**词汇**（不是文本）：
    technique     "oil on canvas" / "ink on paper" / "bronze, silver inlay" ...
    type          "Painting" / "Ceramics" / "Textile" ...
    culture       "China" / "Japan" / "France" ...
    department    "Chinese Art" / "Textiles" ...

我们只取这些字段做词频统计，**不取标题、描述、图像**。
许可：Cleveland 的开放数据是 CC0 / 公共领域。

产物
----
    E:\\external\\research\\cleveland_page<N>.json
    F:\\llm\\data\\raw\\harvest_cle_v1.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

OUT_RAW = r"E:\external\research"
OUT_AGG = r"F:\llm\data\raw\harvest_cle_v1.json"
API = "https://openaccess-api.clevelandart.org/api/artworks/"
UA = "anchor-vocab-harvest/1.0 (research; local use)"
PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
LIMIT = 100


def fetch(skip):
    qs = urllib.parse.urlencode({"limit": LIMIT, "skip": skip, "has_image": 1})
    req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    os.makedirs(OUT_RAW, exist_ok=True)
    works = []
    for p in range(PAGES):
        skip = p * LIMIT
        try:
            data = fetch(skip)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  skip {skip:>5} 失败: {type(e).__name__}")
            continue
        items = data.get("data") or []
        if not items:
            print(f"  skip {skip:>5} 空，停止")
            break
        works.extend(items)
        with open(os.path.join(OUT_RAW, f"cleveland_page{p+1}.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        if p % 5 == 0:
            print(f"  skip {skip:>5} 累计 {len(works)} 件")
        time.sleep(0.3)

    print(f"\n采集 {len(works)} 件作品")
    if not works:
        print("  一条都没拿到")
        print("\n### CLE_FAILED")
        return

    tech = Counter()
    typ = Counter()
    cult = Counter()
    dept = Counter()
    for w in works:
        for field, counter in (("technique", tech), ("type", typ),
                               ("culture", cult), ("department", dept)):
            v = w.get(field) or ""
            # 有些字段是列表（例如 technique 可能给多个），统一成字符串
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v if x)
            v = str(v).strip()
            if v:
                counter[v] += 1

    agg = {
        "source": "Cleveland Museum of Art open access API",
        "license": "CC0 / public domain metadata; only vocabulary fields taken",
        "n_works": len(works),
        "technique": tech.most_common(400),
        "type": typ.most_common(200),
        "culture": cult.most_common(150),
        "department": dept.most_common(100),
    }
    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)

    print(f"\n=== technique 前 30（共 {len(tech)} 种）===")
    for k, v in tech.most_common(30):
        print(f"  {v:>4}  {k}")

    print(f"\n=== type 前 15（共 {len(typ)} 种）===")
    for k, v in typ.most_common(15):
        print(f"  {v:>4}  {k}")

    print(f"\n=== department 前 10 ===")
    for k, v in dept.most_common(10):
        print(f"  {v:>4}  {k}")

    print(f"\n-> {OUT_AGG}")
    print("\n### CLE_HARVEST_DONE")


if __name__ == "__main__":
    main()
