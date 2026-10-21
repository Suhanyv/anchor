"""
风格提示服务（CPU only，零第三方依赖）

为什么要 CPU：
    这台机器只有 8GB 显存，SDXL/Flux 要吃 6-8GB。
    检索模型再占 1GB 必然打架。e5-small 在 CPU 上编码一个 query 约 50-150ms，
    语料 embedding 预计算并缓存，启动只加载 .npy。
    -> 显存 100% 留给扩散模型。

端点：
    GET  /health
    POST /style-hint   {"query": "...", "topk": 3}
         -> 返回最匹配的导演 + 可直接粘进 prompt 的英文风格串
    POST /search       {"query": "...", "topk": 5}
         -> 返回最匹配的提示词原文

启动：
    F:\\llm\\.venv\\Scripts\\python.exe F:\\llm\\src\\serve_style.py --port 8848
"""
import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = r"F:\llm"
DEFAULT_CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v3.jsonl")
DEFAULT_MODEL = os.path.join(ROOT, "models", "e5-director-v3")
CACHE_DIR = os.path.join(ROOT, "cache")
MAXLEN = 128

Q_PREFIX = "query: "
P_PREFIX = "passage: "

STATE = {"corpus": None, "doc_emb": None, "model": None, "tok": None, "enc": None}


def load_corpus(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def get_model(path):
    import torch
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(path)
    enc = AutoModel.from_pretrained(path).eval()
    for p in enc.parameters():
        p.requires_grad_(False)
    return tok, enc


def encode(texts, prefix, tok, enc, bs=32):
    import torch
    import torch.nn.functional as F
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            b = tok([prefix + t for t in texts[i:i + bs]], padding=True,
                    truncation=True, max_length=MAXLEN, return_tensors="pt")
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            v = ((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float()
            out.append(F.normalize(v, dim=-1))
    return torch.cat(out).numpy()


def init(corpus_path, model_path):
    import numpy as np
    os.makedirs(CACHE_DIR, exist_ok=True)
    corpus = load_corpus(corpus_path)
    print(f"corpus: {len(corpus)} doc  ({os.path.basename(corpus_path)})")

    tag = f"{os.path.basename(model_path)}__{os.path.basename(corpus_path)}.npy"
    cache = os.path.join(CACHE_DIR, tag)

    t0 = time.time()
    tok, enc = get_model(model_path)
    print(f"model loaded: {os.path.basename(model_path)}  ({time.time()-t0:.1f}s)")

    if os.path.exists(cache):
        doc_emb = np.load(cache)
        if doc_emb.shape[0] == len(corpus):
            print(f"doc embeddings: cache hit {doc_emb.shape}  ({time.time()-t0:.1f}s)")
        else:
            doc_emb = None
    else:
        doc_emb = None

    if doc_emb is None:
        t1 = time.time()
        doc_emb = encode([d["text_semantic"] for d in corpus], P_PREFIX, tok, enc)
        np.save(cache, doc_emb)
        print(f"doc embeddings: computed {doc_emb.shape} in {time.time()-t1:.1f}s -> {cache}")

    STATE.update(corpus=corpus, doc_emb=doc_emb, tok=tok, enc=enc)


def query_embed(q):
    return encode([q], Q_PREFIX, STATE["tok"], STATE["enc"])[0]


def style_hint(q, topk):
    import numpy as np
    corpus, doc_emb = STATE["corpus"], STATE["doc_emb"]
    qe = query_embed(q)
    sims = doc_emb @ qe

    # 按导演聚合（取该导演最高分文档）
    best = {}
    for i, d in enumerate(corpus):
        s = float(sims[i])
        cur = best.get(d["director"])
        if cur is None or s > cur["score"]:
            best[d["director"]] = {
                "score": s,
                "director": d["director"],
                "director_zh": d.get("director_zh", ""),
                "facet": d.get("facet", "base"),
                "style_tags": d.get("style_tags", []),
                "sample_prompt": d.get("prompt", ""),
            }
    ranked = sorted(best.values(), key=lambda x: -x["score"])[:topk]

    for r in ranked:
        tags = ", ".join(r["style_tags"][:4])
        r["style_string"] = f"in the style of {r['director']}" + (f", {tags}" if tags else "")
        r["score"] = round(r["score"], 4)
    return {"query": q, "results": ranked}


def search(q, topk):
    corpus, doc_emb = STATE["corpus"], STATE["doc_emb"]
    qe = query_embed(q)
    sims = doc_emb @ qe
    order = sims.argsort()[::-1][:topk]
    out = []
    for i in order:
        d = corpus[int(i)]
        out.append({
            "doc_id": d["doc_id"],
            "director": d["director"],
            "director_zh": d.get("director_zh", ""),
            "facet": d.get("facet", "base"),
            "score": round(float(sims[int(i)]), 4),
            "prompt": d.get("prompt", ""),
            "text_semantic": d.get("text_semantic", ""),
        })
    return {"query": q, "results": out}


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
            self._send({"ok": True, "docs": len(STATE["corpus"]),
                        "model": os.path.basename(DEFAULT_MODEL)})
        else:
            self._send({"error": "use POST /style-hint or /search"}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:  # noqa: BLE001
            self._send({"error": f"bad json: {e}"}, 400)
            return

        q = (payload.get("query") or "").strip()
        if not q:
            self._send({"error": "missing 'query'"}, 400)
            return
        topk = int(payload.get("topk") or 3)

        try:
            if self.path.startswith("/style-hint"):
                self._send(style_hint(q, topk))
            elif self.path.startswith("/search"):
                self._send(search(q, topk))
            else:
                self._send({"error": "unknown endpoint"}, 404)
        except Exception as e:  # noqa: BLE001
            self._send({"error": str(e)}, 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()

    init(a.corpus, a.model)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"\nserving on http://{a.host}:{a.port}")
    print("  GET  /health")
    print("  POST /style-hint  {\"query\": \"霓虹夜色，慢门，暧昧的感觉\"}")
    print("  POST /search      {\"query\": \"一个杯子就让人紧张\"}")
    print("\n### SERVER_READY\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
