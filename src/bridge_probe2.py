"""多源探测：哪些公开馆藏 API 现在通、要不要 key、有没有非西方藏品"""
import json
import urllib.parse
import urllib.request

UA = "anchor-bridge/0.2 (multi-source probe)"


def try_get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(4000).decode("utf-8", "replace")
            return r.status, body
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {str(e)[:52]}"


TESTS = [
    ("Met 搜索", "https://collectionapi.metmuseum.org/public/collection/v1/search?q=armor"),
    ("AIC 搜索", "https://api.artic.edu/api/v1/artworks/search?q=armor&limit=2"),
    ("NGA 搜索", "https://api.nga.gov/search?q=armor"),
    ("Openverse", "https://api.openverse.org/v1/images/?q=lamellar%20armour&page_size=2"),
    ("Wikimedia Commons", "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=lamellar%20armour&srlimit=2"),
    ("Cleveland（参照）", "https://openaccess-api.clevelandart.org/api/artworks/?q=armor&cc0=1&limit=2"),
    ("Smithsonian（需key?）", "https://api.si.edu/openaccess/api/v1.0/search?q=armor&api_key=DEMO_KEY"),
    ("Europeana（需key?）", "https://api.europeana.eu/record/v2/search.json?query=armor&wskey=api2demo"),
]

for name, url in TESTS:
    st, body = try_get(url)
    if st is None:
        print(f"  [断] {name:<20} {body}")
    else:
        prev = body[:150].replace("\n", " ")
        print(f"  [通] {name:<20} HTTP {st}  {prev}")

print("\n### MULTI_SOURCE_PROBE_DONE")
