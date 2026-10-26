"""
源普查：一个镜头需要哪些要素，每样能从哪里合规地取

要素       需要什么
风格       导演/流派/影调词
主体       人物/器物/动物
场景       地点/场面
工艺       技法
材质       表面与材料
光线       布光方式
运镜       机位运动
声音       环境声/音效
色彩       调色倾向

这一轮只做**可达性**普查，不下载内容。
"""
import json
import urllib.parse
import urllib.request

UA = "anchor-source-audit/0.1"
PROBE = "armour"       # 统一用一个英文词探通不通


def probe(name, url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(1500).decode("utf-8", "replace")
            return "通", f"HTTP {r.status}", body[:90].replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        return "断", f"{type(e).__name__}", str(e)[:70]


Q = urllib.parse.quote(PROBE)
TESTS = [
    ("Cleveland", "museum", f"https://openaccess-api.clevelandart.org/api/artworks/?q={Q}&cc0=1&limit=1"),
    ("Smithsonian", "museum", f"https://api.si.edu/openaccess/api/v1.0/search?api_key=DEMO_KEY&rows=1&q={Q}"),
    ("Europeana", "museum", f"https://api.europeana.eu/record/v2/search.json?wskey=api2demo&rows=1&query={Q}"),
    ("Wikimedia", "encyclopedia", f"https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srlimit=1&srsearch={Q}"),
    ("Internet Archive", "text/video", f"https://archive.org/advancedsearch.php?q={Q}&fl[]=identifier&rows=1&output=json"),
    ("Wikipedia REST", "encyclopedia", f"https://en.wikipedia.org/api/rest_v1/page/summary/Armour"),
    ("Freesound", "sound", f"https://freesound.org/apiv2/search/text/?query={Q}&token=DEMO_KEY"),
    ("Pixabay", "photo", f"https://pixabay.com/api/?key=DEMO_KEY&q={Q}"),
    ("Rijksmuseum", "museum", f"https://www.rijksmuseum.nl/api/en/collection?key=0fiuZFh4&q={Q}&ps=1"),
    ("Harvard Art", "museum", f"https://api.harvardartmuseums.org/object?apikey=DEMO_KEY&q={Q}&size=1"),
    ("Art UK", "museum", f"https://api.artuk.org/artworks?search={Q}"),
    ("NYPL Digital", "library", f"https://digitalcollections.nypl.org/search/index?utf8=%E2%9C%93&keywords={Q}"),
    ("TMDB", "film", "https://api.themoviedb.org/3/search/movie?api_key=DEMO_KEY&query=armour"),
    ("Met（再试）", "museum", f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={Q}"),
]

rows = []
for name, kind, url in TESTS:
    st, code, note = probe(name, url)
    rows.append({"name": name, "kind": kind, "status": st, "code": code,
                 "note": note})
    print(f"  [{st}] {name:<18} {kind:<12} {code:<22} {note[:52]}")

ok = sum(1 for r in rows if r["status"] == "通")
print(f"\n  可达 {ok}/{len(rows)}")
print("\n### SOURCE_AUDIT_DONE")
