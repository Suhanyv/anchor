"""
HTTP 服务：和 ComfyUI 节点共用同一套实现

设计上的一处改动（重要）
------------------------
旧版自己实现了一遍检索逻辑，只有风格一个通道，逐步落后于节点
（节点有四通道 + 14 种输出格式，服务只有风格），写进了 LIMITATIONS。

现在改成**直接调用 comfyui/local_style_hint.py 的 run()**：
一份实现，两个前端（ComfyUI 节点 / HTTP 服务），不会再有漂移。

端点
----
    GET  /health          文档数、模型、可用格式
    POST /style-hint      {query, topk?, domain?, format?}  -> 提示词文本
    POST /search          {query, topk?, domain?}           -> 原始文档列表

domain: auto / image / video / any（也接受中文：自动/图片/视频/不限）
format: 见 /health 的 formats 列表，默认「片段（英文）」
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as NODE  # noqa: E402

DEFAULT_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v21.jsonl")
DEFAULT_MODEL = os.path.join(ROOT, "models", "e5-director-c27")
DEFAULT_SUBJECTS = os.path.join(ROOT, "data", "raw", "subjects_v4.jsonl")
DEFAULT_CRAFTS = os.path.join(ROOT, "data", "raw", "crafts_v3.jsonl")
DEFAULT_MATERIALS = os.path.join(ROOT, "data", "raw", "materials_v4.jsonl")

DOMAIN_ZH = {"auto": "自动", "image": "图片", "video": "视频", "any": "不限",
             "自动": "自动", "图片": "图片", "视频": "视频", "不限": "不限"}

STATE = {"corpus": DEFAULT_CORPUS, "model": DEFAULT_MODEL,
         "subjects": DEFAULT_SUBJECTS, "crafts": DEFAULT_CRAFTS,
         "materials": DEFAULT_MATERIALS, "use_material": True,
         "device": "cpu", "node": None}


def formats():
    return NODE.LocalStyleHint.INPUT_TYPES()["required"]["输出格式"][0]


def init(corpus, model, subjects, crafts, materials,
         use_material=True, device="cpu"):
    STATE.update({"corpus": corpus, "model": model, "subjects": subjects,
                  "crafts": crafts, "materials": materials,
                  "use_material": use_material, "device": device})
    STATE["node"] = NODE.LocalStyleHint()


def _run(q, topk, domain, fmt):
    """唯一的执行入口：和节点走同一条路。"""
    n = STATE["node"]
    out, dbg = n.run(
        q, STATE["model"], STATE["corpus"], STATE["subjects"],
        STATE["crafts"], STATE["materials"], STATE["use_material"],
        fmt, STATE["device"], DOMAIN_ZH.get(domain, "自动"),
        "导演/风格聚合", topk, "", False)
    return out, dbg


def style_hint(q, topk=3, domain="auto", fmt=None):
    fmt = fmt or "结构化（英文）"
    if fmt not in formats():
        raise ValueError(f"未知格式：{fmt}。可用：{formats()}")
    out, dbg = _run(q, topk, domain, fmt)
    dom_line = next((l for l in dbg.split("\n") if l.startswith("【")), "")
    return {
        "query": q,
        "domain_used": domain,
        "format": fmt,
        "prompt": out,
        "note": dom_line,
        "debug": dbg,
    }


def search(q, topk=5, domain="auto"):
    """原始文档列表（不套模板），用于排查与二开。"""
    n = STATE["node"]
    items, mode, subj, dused, craft, mat = NODE._rank(
        q, STATE["model"], STATE["corpus"], STATE["device"], topk,
        "导演/风格聚合", DOMAIN_ZH.get(domain, "自动"),
        STATE["subjects"], STATE["crafts"], STATE["materials"],
        STATE["use_material"])
    rows = []
    for it in items:
        rows.append({
            "director": it.get("director", ""),
            "director_zh": it.get("director_zh", ""),
            "facet": it.get("facet", ""),
            "domain": it.get("domain", ""),
            "motion": it.get("motion", ""),
            "score": round(float(it.get("score", 0)), 4),
            "doc_id": it.get("doc_id", ""),
            "description": it.get("description", ""),
            "style_string": it.get("style_string", ""),
        })
    return {"query": q, "mode": mode, "domain_used": dused, "results": rows}


def handle_post(path, payload):
    q = (payload.get("query") or "").strip()
    if not q:
        raise ValueError("missing 'query'")
    topk = int(payload.get("topk") or (3 if "style-hint" in path else 5))
    domain = (payload.get("domain") or "auto").lower()
    if path.startswith("/style-hint"):
        return style_hint(q, topk, domain, payload.get("format"))
    if path.startswith("/search"):
        return search(q, topk, domain)
    raise LookupError("unknown endpoint")


# --- 统一路径：以节点默认值为准，避免脚本与部署漂移 ---
try:
    from paths import DEFAULTS as _PATHS
    M, C = _PATHS["model"], _PATHS["corpus"]
    S, K, MT = _PATHS["subjects"], _PATHS["crafts"], _PATHS["materials"]
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--subjects", default=DEFAULT_SUBJECTS)
    ap.add_argument("--crafts", default=DEFAULT_CRAFTS)
    ap.add_argument("--materials", default=DEFAULT_MATERIALS)
    ap.add_argument("--no-material", action="store_true")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    a = ap.parse_args()

    init(a.corpus, a.model, a.subjects, a.crafts, a.materials,
         not a.no_material, a.device)

    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

        def _send(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/health"):
                n = sum(1 for _ in open(STATE["corpus"], encoding="utf-8"))
                self._send({"ok": True,
                            "docs": n,
                            "model": os.path.basename(STATE["model"]),
                            "corpus": os.path.basename(STATE["corpus"]),
                            "channels": ["风格", "题材", "工艺", "材质"],
                            "material_enabled": STATE["use_material"],
                            "formats": formats()})
            else:
                self._send({"error": "GET /health；写操作走 POST /style-hint 或 /search"}, 404)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(n) or b"{}")
            except Exception as e:  # noqa: BLE001
                self._send({"error": f"bad json: {e}"}, 400)
                return
            try:
                self._send(handle_post(self.path, payload))
            except LookupError as e:
                self._send({"error": str(e)}, 404)
            except ValueError as e:
                self._send({"error": str(e)}, 400)
            except Exception as e:  # noqa: BLE001
                self._send({"error": f"{type(e).__name__}: {e}"}, 500)

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"\nserving on http://{a.host}:{a.port}")
    print(f"  corpus {os.path.basename(a.corpus)}   model {os.path.basename(a.model)}")
    print(f"  通道 风格 / 题材 / 工艺 / 材质（材质 {'开' if not a.no_material else '关'}）")
    print(f"  格式 {len(formats())} 种（见 /health）")
    print("\n  GET  /health")
    print("  POST /style-hint  {\"query\": \"霓虹夜色，慢门\", \"format\": \"即梦 Seedance 2.5（中文）\"}")
    print("  POST /search      {\"query\": \"一个杯子就让人紧张\"}")
    print("\n### SERVER_READY\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
