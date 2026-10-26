"""
联网学习桥（多源版）

输入是一对：**中文词 + 英文查词**。为什么必须成对——
中文直查这些源基本不得力（实测）：
    骆驼   -> Peganum harmala（一种植物）
    唐卡   -> Lila Downs / Dante Alighieri
    敦煌   -> 莫高窟、Gansu（这个对）
    敦煌 / 唐卡 在 Smithsonian 能查到，因为那是图书目录，带拼音著录

所以桥不假装懂中文，**把"怎么用英文问"这一步交给人**。

源（都在 2026-10-26 实测可达）
----------------------------
Cleveland     CC0，无需 key，亚洲藏品强
Smithsonian   DEMO_KEY 可用，图书馆目录，中文著录可命中
Wikimedia     Commons API，无需 key，中文能搜到分类名

每个进来的行都带 `provenance`：源、查词、对象 id、日期。

用法
----
    python src/bridge.py learn "中文词|english query|crafts|场景" ...
    python src/bridge.py stage / show / apply
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
STAGE = os.path.join(RAW, "bridge_staging.jsonl")
UA = "anchor-bridge/0.3 (+https://github.com/Suhanyv/anchor)"

KIND_FILE = {"crafts": "crafts_v8.jsonl", "materials": "materials_v12.jsonl",
             "subjects": "subjects_v14.jsonl"}
KIND_PREFIX = {"crafts": "C", "materials": "M", "subjects": "S"}


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------------- 三个源 ----------------
def src_cleveland(q):
    u = ("https://openaccess-api.clevelandart.org/api/artworks/"
         f"?q={urllib.parse.quote(q)}&cc0=1&has_image=1&limit=4")
    arts = _get(u).get("data") or []
    tech = [a.get("technique") or "" for a in arts]
    mats = [m.get("description") or m.get("name") or ""
            for a in arts for m in (a.get("materials") or [])]
    desc = [(a.get("wall_description") or "") for a in arts]
    return {
        "source": "Cleveland Museum of Art Open Access (CC0)",
        "ids": [a.get("id") for a in arts],
        "phrases": [t for t in tech if t],
        "materials": [m for m in mats if m],
        "descs": [d for d in desc if d],
    }


def src_smithsonian(q):
    u = ("https://api.si.edu/openaccess/api/v1.0/search?api_key=DEMO_KEY"
         f"&rows=4&q={urllib.parse.quote(q)}")
    rows = ((_get(u).get("response") or {}).get("rows") or [])
    out = []
    for r in rows:
        c = (r.get("content") or {})
        d = (c.get("descriptiveNonRepeating") or {})
        out.append({
            "title": d.get("title", {}).get("content") if isinstance(
                d.get("title"), dict) else d.get("title"),
            "notes": " ".join(
                str(n.get("content", ""))[:120]
                for n in ((c.get("freetext") or {}).get("notes") or [])[:1]),
        })
    return {
        "source": "Smithsonian Open Access (DEMO_KEY)",
        "ids": [r.get("id") for r in rows],
        "phrases": [str(o.get("title") or "") for o in out if o.get("title")],
        "materials": [],
        "descs": [o["notes"] for o in out if o.get("notes")],
    }


def src_wikimedia(q):
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
         f"&list=search&srlimit=4&srsearch={urllib.parse.quote(q)}")
    hits = ((_get(u).get("query") or {}).get("search") or [])
    return {
        "source": "Wikimedia Commons (CC)", 
        "ids": [h.get("pageid") for h in hits],
        "phrases": [h.get("title", "") for h in hits if h.get("title")],
        "materials": [],
        "descs": [],
    }


SOURCES = [src_cleveland, src_smithsonian, src_wikimedia]


def fetch_all(q):
    """依次问三个源，返回第一个有内容的；都空则 None。"""
    tried = []
    for fn in SOURCES:
        try:
            r = fn(q)
        except Exception as e:  # noqa: BLE001
            tried.append(f"{fn.__name__}: {type(e).__name__}")
            continue
        if r["phrases"] or r["descs"]:
            r["tried"] = tried
            return r
        tried.append(f"{fn.__name__}: 0 条")
    return {"source": "none", "phrases": [], "descs": [], "materials": [],
            "ids": [], "tried": tried}


def _looks_like_object_record(phrase, desc):
    """挡住"书名 / 论文集 / 期刊"这类记录。

    实测（2026-10-26）：Smithsonian 对场景类查询返回的是图书馆目录，
    取第一条会得到
        "Men, ships, and the sea, by Alan Villiers and other adventurers"
        "Arid lands : today and tomorrow : proceedings of an international..."
    这些不是画面，是书目。宁可少学，不要学错。
    """
    t = f"{phrase} {desc}".lower()
    bad = ("proceedings", "edited by", " by ", "journal", "thesis", "dissertation",
           "symposium", "catalogue raisonné", "press,", "university press")
    if any(b in t for b in bad):
        return False
    if len(phrase) > 110:          # 技法名不会这么长
        return False
    return True


def _shares_query_words(en_query, phrase, desc, need=2):
    """查词里的实词，至少在馆方原文里出现 need 个。

    为什么不用语义阈值：实测（6 条样本）
        雕漆 0.832 / 错金银 0.826 / 银丝掐丝 0.825 / 蜡染 0.800 / 扎染 0.742
    错的"扎染<-棕榈纤维"只比对的低 0.06，拿它当阈值就是在 6 条上过拟合。
    词面规则虽然笨，但能解释：查 "tie dye resist" 得到
    "Raffia palm fiber and dye"，只中了 dye 一个词，就该拒。
    """
    stops = {"the", "and", "with", "for", "on", "of", "in", "or", "a", "an"}
    words = [w for w in en_query.lower().replace("-", " ").split()
             if len(w) >= 3 and w not in stops]
    if not words:
        return True
    t = f"{phrase} {desc}".lower()
    hit = sum(1 for w in words if w in t)
    return hit >= min(need, len(words))


def mint(zh, en, kind, extra_kw, scene=False):
    # 场景/主体不接：馆藏记录描述的是"一件东西"，不是"一个场面"。
    # 实测对场景查询只会返回书画作品或书目，装进去就是污染。
    if kind.rstrip("s") == "subject":
        print(f"    [{zh}] 跳过：桥只学技法与材质，场景要靠人工")
        return None
    r = fetch_all(en)
    if not (r["phrases"] or r["descs"]):
        print(f"    [{zh}] 三个源都没有：{r.get('tried')}")
        return None
    phrase = (r["phrases"][0] if r["phrases"] else "")[:150]
    desc = (r["descs"][0] if r["descs"] else "")[:200]
    if not _looks_like_object_record(phrase, desc):
        print(f"    [{zh}] 跳过：取到的是书目不是画面 —— {phrase[:44]}")
        return None
    if not _shares_query_words(en, phrase, desc):
        print(f"    [{zh}] 跳过：查词对不上原文 —— 问「{en}」得到「{phrase[:40]}」")
        return None
    if not desc:
        desc = f"{zh}（{en}），来源：{r['source']}"
    kw = list(dict.fromkeys([zh] + extra_kw))
    single = kind.rstrip("s")
    row = {
        "doc_id": "", "kind": single,
        f"{single}_en": en, f"{single}_zh": zh,
        "phrase": phrase or en,
        "kw_zh": kw,
        "description": desc,
        "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
        "provenance": {"source": r["source"], "query": en,
                       "ids": r["ids"][:4],
                       "fetched": time.strftime("%Y-%m-%d")},
    }
    if single == "subject":
        row["type"] = "scene" if scene else "object"
    print(f"    [{zh}] <- {r['source'].split('(')[0].strip()}"
          f"  {phrase[:46]}")
    return row


def cmd_learn(args):
    rows = []
    for a in args:
        parts = [x.strip() for x in a.split("|")]
        if len(parts) < 3:
            print(f"    跳过（格式不对）{a}")
            continue
        zh, en, kind = parts[0], parts[1], parts[2]
        extra = [x.strip() for x in (parts[3].split(",") if len(parts) > 3 else [])
                 if x.strip()]
        scene = "scene" in extra or "场景" in extra
        extra = [x for x in extra if x not in ("scene", "场景")]
        r = mint(zh, en, kind, extra, scene)
        if r:
            rows.append(r)
        time.sleep(0.5)
    with open(STAGE, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  暂存 {len(rows)} 条")


def cmd_show():
    if not os.path.exists(STAGE):
        print("  没有暂存")
        return
    for l in open(STAGE, encoding="utf-8"):
        r = json.loads(l)
        name = r.get("craft_zh") or r.get("mat_zh") or r.get("subject_zh")
        print(f"  {name}  <- {r['provenance']['source']}")
        print(f"     phrase: {r['phrase'][:84]}")


def cmd_apply():
    if not os.path.exists(STAGE):
        print("  没有暂存")
        return
    staged = [json.loads(l) for l in open(STAGE, encoding="utf-8") if l.strip()]
    by_kind = {}
    for r in staged:
        by_kind.setdefault(r["kind"] + "s", []).append(r)
    for kind, rows in by_kind.items():
        src = os.path.join(RAW, KIND_FILE[kind])
        cur = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
        have = {(r.get("craft_zh") or r.get("mat_zh") or r.get("subject_zh"))
                for r in cur}
        n = 0
        for r in rows:
            name = r.get("craft_zh") or r.get("mat_zh") or r.get("subject_zh")
            if name in have:
                print(f"    跳过（已存在）{name}")
                continue
            n += 1
            r["doc_id"] = f"{KIND_PREFIX[kind]}{9000 + len(cur) + n}"
            cur.append(r)
        base = KIND_FILE[kind]
        num = int("".join(c for c in base.split("_v")[1].split(".")[0]
                          if c.isdigit()))
        nxt = base.split("_v")[0] + f"_v{num + 1}.jsonl"
        with open(os.path.join(RAW, nxt), "w", encoding="utf-8") as f:
            for r in cur:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"    {base} -> {nxt}  (+{n})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    print(f"=== bridge {cmd} ===")
    if cmd == "learn":
        cmd_learn(sys.argv[2:])
    else:
        {"stage": cmd_show, "show": cmd_show, "apply": cmd_apply}.get(
            cmd, cmd_show)()
    print("\n### BRIDGE_DONE")
