"""
采集天文类词汇：NASA 图像库 API（公共领域）

为什么换源
----------
Cleveland 是美术馆，没有天体；Wikidata SPARQL 被限流。
NASA 的图像库 API 不需要 key，返回 title / description / keywords，
正好是"天体与天文现象"的词汇来源。

只取词汇（对象名、现象名），**不取任何图片**。

若全部失败，脚本会明确报告，由人决定是否凭知识手写。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

OUT_RAW = r"E:\external\research"
OUT_AGG = r"F:\llm\data\raw\harvest_space_v1.json"
UA = "anchor-vocab-harvest/1.0 (research; local)"

TERMS = [
    "sun", "sunspot", "corona", "solar flare", "prominence", "photosphere",
    "earth", "moon surface", "lunar", "terminator",
    "mars", "jupiter", "saturn rings", "asteroid", "comet",
    "nebula", "galaxy", "star cluster", "milky way", "black hole",
    "aurora", "star trail", "eclipse", "solar wind", "magnetosphere",
]


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"    拒 HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        print(f"    断 {type(e).__name__}: {str(e)[:46]}")
    return None


def main():
    os.makedirs(OUT_RAW, exist_ok=True)
    print("=== 探源 ===")
    test = probe("https://images-api.nasa.gov/search?q=nebula&media_type=image&page_size=2")
    if test is None:
        print("  NASA 图像库不通，放弃采词，改为人工编写")
        print("\n### SPACE_HARVEST_FAILED")
        return
    print("  NASA 图像库 OK")

    items = []
    kw = Counter()
    for t in TERMS:
        qs = urllib.parse.urlencode({"q": t, "media_type": "image", "page_size": 10})
        data = probe(f"https://images-api.nasa.gov/search?{qs}")
        if not data:
            continue
        hits = (data.get("collection") or {}).get("items") or []
        for h in hits:
            d = (h.get("data") or [{}])[0]
            title = (d.get("title") or "").strip()
            desc = (d.get("description") or "").strip()
            words = d.get("keywords") or []
            items.append({"term": t, "nasa_id": d.get("nasa_id", ""),
                          "title": title, "desc_len": len(desc),
                          "keywords": words})
            for w in words:
                kw[str(w).strip().lower()] += 1
        print(f"  {t:<16} 取 {len(hits)} 条")
        time.sleep(0.4)

    agg = {"source": "NASA Images API (public domain)", "n_items": len(items),
           "keywords": kw.most_common(300), "items": items}
    with open(os.path.join(OUT_RAW, "nasa_space_items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)

    print(f"\n采到 {len(items)} 条元数据，{len(kw)} 种关键词")
    print("\n=== 关键词前 30 ===")
    for k, v in kw.most_common(30):
        print(f"  {v:>3}  {k}")
    print(f"\n-> {OUT_AGG}")
    print("\n### SPACE_HARVEST_DONE")


if __name__ == "__main__":
    main()
