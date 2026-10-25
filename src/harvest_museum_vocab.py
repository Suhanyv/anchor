"""
从开放博物馆 API 采集材质/流派词表（CC0 元数据）

为什么用博物馆数据
------------------
要"大面积扩充"，手写不现实。开放博物馆的元数据里有结构化字段：
    medium_display        "Oil on canvas" / "Watercolor on paper" / "Bronze" ...
    classification_title  器物类别
    style_title           流派
这些字段本身就是**材质与流派的真实词汇表**，数量大、有出处、许可清楚。

许可
----
芝加哥艺术博物馆（AIC）API：公开元数据，作品图像多为 CC0；
我们**只取字段词表，不取任何作品图像或描述文本**，与既有的
"只取词汇与结构，不抄原文"一致。

产物
----
    E:\\external\\research\\aic_raw_page<N>.json   原始分页（可复现）
    F:\\llm\\data\\raw\\harvest_vocab_v1.json       聚合后的词频表
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OUT_RAW = r"E:\external\research"
OUT_AGG = r"F:\llm\data\raw\harvest_vocab_v1.json"

API = "https://api.artic.edu/api/v1/artworks"
FIELDS = "id,title,medium_display,classification_title,style_title,technique_title,date_display,place_of_origin"
PAGE_SIZE = 100
PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def fetch_page(page):
    qs = urllib.parse.urlencode({
        "page": page, "limit": PAGE_SIZE, "fields": FIELDS,
    })
    url = f"{API}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "anchor-vocab-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    os.makedirs(OUT_RAW, exist_ok=True)
    rows = []
    ok_pages = 0
    for p in range(1, PAGES + 1):
        try:
            data = fetch_page(p)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  page {p:>3} 失败: {type(e).__name__}")
            continue
        items = data.get("data") or []
        rows.extend(items)
        ok_pages += 1
        with open(os.path.join(OUT_RAW, f"aic_raw_page{p}.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        if p % 5 == 0 or p == 1:
            print(f"  page {p:>3} 累计 {len(rows)} 条")
        time.sleep(0.25)

    print(f"\n采集完成：{ok_pages}/{PAGES} 页，{len(rows)} 件作品")
    if not rows:
        print("  一条都没拿到，网络不通")
        return

    # 聚合
    from collections import Counter
    med = Counter()
    cls = Counter()
    sty = Counter()
    for r in rows:
        m = (r.get("medium_display") or "").strip()
        if m:
            med[m] += 1
        c = (r.get("classification_title") or "").strip()
        if c:
            cls[c] += 1
        s = (r.get("style_title") or "").strip()
        if s:
            sty[s] += 1

    agg = {
        "source": "Art Institute of Chicago public API",
        "license": "public metadata; no artwork images or descriptions taken",
        "n_works": len(rows),
        "medium_display": med.most_common(300),
        "classification_title": cls.most_common(150),
        "style_title": sty.most_common(200),
    }
    with open(OUT_AGG, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)

    print(f"\n=== medium_display 前 25（共 {len(med)} 种）===")
    for k, v in med.most_common(25):
        print(f"  {v:>4}  {k}")

    print(f"\n=== classification_title 前 15（共 {len(cls)} 种）===")
    for k, v in cls.most_common(15):
        print(f"  {v:>4}  {k}")

    print(f"\n=== style_title 前 15（共 {len(sty)} 种）===")
    for k, v in sty.most_common(15):
        print(f"  {v:>4}  {k}")

    print(f"\n-> {OUT_AGG}")
    print("\n### HARVEST_DONE")


if __name__ == "__main__":
    main()
