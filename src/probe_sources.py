"""探测几个开放数据源在本机是否可达（只发 HEAD/小请求）"""
import json
import ssl
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) anchor-vocab-harvest/1.0"

TARGETS = [
    ("AIC 作品列表", "https://api.artic.edu/api/v1/artworks?limit=2&fields=id,medium_display"),
    ("AIC 文档根", "https://api.artic.edu/api/v1/"),
    ("Met 搜索", "https://collectionapi.metmuseum.org/public/collection/v1/search?q=bronze"),
    ("Cleveland 搜索", "https://openaccess-api.clevelandart.org/api/artworks/?q=bronze&limit=2"),
    ("Wikipedia API", "https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Art_media&cmlimit=5&format=json"),
    ("Wikidata API", "https://www.wikidata.org/w/api.php?action=wbsearchentities&search=lacquer&language=en&limit=3&format=json"),
    ("Wikimedia Commons", "https://commons.wikimedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Crafts&cmlimit=5&format=json"),
    ("GitHub API", "https://api.github.com/repos/YanKaFei/art-aesthetic-vault"),
    ("raw.githubusercontent", "https://raw.githubusercontent.com/YanKaFei/art-aesthetic-vault/main/README.md"),
]


def probe(name, url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(4000)
            print(f"  OK   {name:<22} HTTP {r.status}  {len(body):>6} B")
            return True
    except urllib.error.HTTPError as e:
        print(f"  拒   {name:<22} HTTP {e.code}  {e.reason}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"  断   {name:<22} {type(e).__name__}: {str(e)[:52]}")
        return False


print("=== 数据源可达性 ===")
for n, u in TARGETS:
    probe(n, u)

print("\n判读：只有 OK 的源能用。全都断的话，就只能靠离线材料与手写。")
print("\n### PROBE_DONE")
