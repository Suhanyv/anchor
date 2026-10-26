"""中文查询能不能直接打这些源？能的话，桥就不用先翻译"""
import json
import urllib.parse
import urllib.request

UA = "anchor-bridge/0.2"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


TERMS = ["骆驼", "维京长船", "摩洛哥", "唐卡", "敦煌"]

print("=== Wikimedia Commons（中文搜索）===")
for t in TERMS:
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
         "&list=search&srlimit=3&srsearch=" + urllib.parse.quote(t))
    try:
        d = get(u)
        hits = (d.get("query") or {}).get("search") or []
        print(f"  {t:<8} {len(hits)} 条 " +
              " | ".join(h.get("title", "")[:28] for h in hits[:2]))
    except Exception as e:  # noqa: BLE001
        print(f"  {t:<8} 失败 {type(e).__name__}")

print("\n=== Europeana（中文搜索，demo key）===")
for t in TERMS:
    u = ("https://api.europeana.eu/record/v2/search.json?wskey=api2demo"
         "&rows=3&query=" + urllib.parse.quote(t))
    try:
        d = get(u)
        items = d.get("items") or []
        print(f"  {t:<8} {d.get('totalResults')} 总 / {len(items)} 返回 " +
              " | ".join((i.get("title") or [""])[0][:26] for i in items[:2]))
    except Exception as e:  # noqa: BLE001
        print(f"  {t:<8} 失败 {type(e).__name__}: {str(e)[:40]}")

print("\n=== Smithsonian（中文搜索，DEMO_KEY）===")
for t in TERMS:
    u = ("https://api.si.edu/openaccess/api/v1.0/search?api_key=DEMO_KEY"
         "&rows=3&q=" + urllib.parse.quote(t))
    try:
        d = get(u)
        rows = ((d.get("response") or {}).get("rows") or [])
        print(f"  {t:<8} {len(rows)} 条 " +
              " | ".join((r.get("title") or "")[:26] for r in rows[:2]))
    except Exception as e:  # noqa: BLE001
        print(f"  {t:<8} 失败 {type(e).__name__}: {str(e)[:40]}")

print("\n### ZH_QUERY_PROBE_DONE")
