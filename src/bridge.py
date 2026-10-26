"""
联网学习桥：给一个中文词 + 英文查词，去公开馆藏里学一个条目回来

为什么是这个形状
----------------
不是"爬一堆东西然后猜它属于哪一类"——那样产出的条目没人敢用。
是**你告诉它要学什么**（中文词 / 英文查词 / 归到哪个渠道），
它去取**可核对的文本**（馆方写的 technique、materials、专有描述），
装成一条索引行，**带出处**。

来源
----
Cleveland Museum of Art Open Access（CC0，可商用，无需署名）
    https://openaccess-api.clevelandart.org/
已知断的源不再接：Wikidata SPARQL（429）、Met（410）、AIC（403）

出处写进每一行（`provenance`），因为"从哪学的"必须能查。

用法
----
    python src/bridge.py stage        # 按 TERMS 抓取，写入暂存
    python src/bridge.py show         # 看暂存
    python src/bridge.py apply        # 并入索引（版本号 +1）
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
UA = "anchor-bridge/0.1 (+https://github.com/Suhanyv/anchor)"
API = "https://openaccess-api.clevelandart.org/api/artworks/"

# 要学的东西：中文词、英文查词、归到哪个渠道、额外关键词
TERMS = [
    ("丝绸刺绣", "silk embroidery", "crafts", ["刺绣", "丝线", "绣"]),
    ("银丝掐丝", "silver wire filigree", "crafts", ["掐丝", "银丝", "花丝"]),
]

KIND_FILE = {"crafts": "crafts_v7.jsonl", "materials": "materials_v12.jsonl",
             "subjects": "subjects_v14.jsonl"}
KIND_PREFIX = {"crafts": "c", "materials": "m", "subjects": "s"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def search(en_query, limit=4):
    u = (API + f"?q={urllib.parse.quote(en_query)}&cc0=1&has_image=1"
         f"&limit={limit}")
    d = get(u)
    return d.get("data") or []


def mint(zh, en_query, kind, extra_kw):
    """把检索结果装成一条索引行。取不到就返回 None。"""
    try:
        arts = search(en_query)
    except Exception as e:  # noqa: BLE001
        print(f"    [{zh}] 抓取失败 {type(e).__name__}: {str(e)[:50]}")
        return None
    if not arts:
        print(f"    [{zh}] 没有结果")
        return None

    techs, mats, descs, ids = [], [], [], []
    for a in arts:
        t = (a.get("technique") or "").strip()
        if t:
            techs.append(t)
        for m in (a.get("materials") or []):
            s = (m.get("description") or m.get("name") or "").strip()
            if s:
                mats.append(s)
        w = (a.get("wall_description") or "").strip()
        if w:
            descs.append(w)
        ids.append(a.get("id"))

    if not (techs or mats):
        print(f"    [{zh}] 结果里没有 technique/materials，不装")
        return None

    tech = techs[0] if techs else ""
    mat = ", ".join(dict.fromkeys(mats))[:120]
    # 英文短语：馆方原文优先，不自己编
    phrase = tech or f"{mat}, museum object photograph"
    desc = (descs[0] if descs else f"{zh}，馆藏实例：{phrase}")[:200]
    kw = list(dict.fromkeys([zh] + extra_kw))
    row = {
        "doc_id": "", "kind": kind.rstrip("s"),
        f"{kind.rstrip('s')}_en": en_query,
        f"{kind.rstrip('s')}_zh": zh,
        "phrase": phrase,
        "kw_zh": kw,
        "description": desc,
        "text_semantic": f"{desc}，{zh}，{'、'.join(kw)}",
        "provenance": {
            "source": "Cleveland Museum of Art Open Access (CC0)",
            "query": en_query,
            "object_ids": ids,
            "fetched": time.strftime("%Y-%m-%d"),
        },
    }
    print(f"    [{zh}] 从 {len(arts)} 件馆藏装满：{phrase[:60]}")
    return row


def cmd_stage():
    rows = []
    for zh, en, kind, kw in TERMS:
        r = mint(zh, en, kind, kw)
        if r:
            rows.append(r)
        time.sleep(0.4)
    with open(STAGE, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  暂存 {len(rows)} 条 -> {os.path.basename(STAGE)}")


def cmd_show():
    if not os.path.exists(STAGE):
        print("  还没有暂存，先跑 stage")
        return
    for l in open(STAGE, encoding="utf-8"):
        r = json.loads(l)
        print(f"  {r.get('craft_zh') or r.get('mat_zh') or r.get('subject_zh')}"
              f"  <- {r['provenance']['source']}")
        print(f"     phrase: {r['phrase'][:90]}")
        print(f"     kw: {r['kw_zh']}")


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
            r["doc_id"] = f"B{KIND_PREFIX[kind]}{len(cur) + n:04d}"
            cur.append(r)
        # 版本号 +1
        base = KIND_FILE[kind]
        num = int("".join(ch for ch in base.split("_v")[1].split(".")[0]
                          if ch.isdigit()))
        nxt = base.split("_v")[0] + f"_v{num + 1}.jsonl"
        dst = os.path.join(RAW, nxt)
        with open(dst, "w", encoding="utf-8") as f:
            for r in cur:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"    {base} -> {nxt}  (+{n})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stage"
    print(f"=== bridge {cmd} ===")
    {"stage": cmd_stage, "show": cmd_show, "apply": cmd_apply}.get(
        cmd, cmd_stage)()
    print("\n### BRIDGE_DONE")
