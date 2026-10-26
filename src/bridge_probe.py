"""
探源：哪些公开 API 现在还通，能按关键词搜、能拿到可用文本、授权清楚

已知断过的：Wikidata SPARQL（429 硬封）、Met（410）、AIC（403）、Wikipedia（超时）
已知通过过的：Cleveland（CC0）、NASA Images
"""
import json
import sys
import urllib.parse
import urllib.request

UA = "anchor-bridge/0.1 (knowledge bridge probe)"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def probe_cleveland(term):
    u = ("https://openaccess-api.clevelandart.org/api/artworks/"
         f"?q={urllib.parse.quote(term)}&cc0=1&has_image=1&limit=3")
    d = get(u)
    out = []
    for a in (d.get("data") or [])[:3]:
        out.append({
            "title": a.get("title"),
            "technique": a.get("technique"),
            "materials": ", ".join(
                [x.get("description") or x.get("name") or ""
                 for x in (a.get("materials") or [])])[:120],
            "desc": (a.get("wall_description") or "")[:180],
            "date": a.get("creation_date"),
        })
    return len(d.get("data") or []), out


def probe_nasa(term):
    u = ("https://images-api.nasa.gov/search?q="
         f"{urllib.parse.quote(term)}&media_type=image")
    d = get(u)
    items = ((d.get("collection") or {}).get("items") or [])[:3]
    out = [{"title": i.get("data", [{}])[0].get("title"),
            "desc": (i.get("data", [{}])[0].get("description") or "")[:180]}
           for i in items]
    return len(items), out


TERMS = sys.argv[1:] or ["lamellar armour", "silver wire filigree"]

for t in TERMS:
    print(f"=== {t} ===")
    for name, fn in (("Cleveland", probe_cleveland), ("NASA", probe_nasa)):
        try:
            n, rows = fn(t)
            print(f"  [{name}] {n} 条")
            for r in rows[:2]:
                print(f"    - {str(r.get('title'))[:44]}")
                if r.get("technique"):
                    print(f"      technique: {r['technique'][:70]}")
                if r.get("materials"):
                    print(f"      materials: {r['materials'][:70]}")
                if r.get("desc"):
                    print(f"      desc: {r['desc'][:90]}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{name}] 失败 {type(e).__name__}: {str(e)[:60]}")
    print()

print("### BRIDGE_PROBE_DONE")
