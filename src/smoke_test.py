"""
冒烟测试：重建/下载模型后，确认整条链路通。

用法：
    python src/smoke_test.py                    # 用默认模型与语料
    python src/smoke_test.py --url "http://127.0.0.1:8848/style-hint"   # 顺带测服务

检查项
------
1. 数据文件齐不齐
2. 模型目录在不在
3. 两条 query 是否命中预期实体
4. 输出是否是"可直接粘进提示词"的英文片段（不是中文、不是空）

设计原则：只用相对路径（相对仓库根），保证在干净克隆里能跑。
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

DATA = {
    "corpus":    "data/raw/corpus_v16.jsonl",
    "subjects":  "data/raw/subjects_v4.jsonl",
    "crafts":    "data/raw/crafts_v3.jsonl",
    "materials": "data/raw/materials_v4.jsonl",
}

# (query, 期望出现在输出里的字符串, 说明)
CASES = [
    ("霓虹夜色，慢门，暧昧的感觉", "Wong Kar-wai", "风格通道：王家卫"),
    ("从树枝后面看过去，前景有草叶遮挡", "Hitchcock", "机制：希区柯克式窥视"),
    ("想要蓝晒那种感觉", "cyanotype", "工艺通道：蓝晒"),
]


# --- 统一路径：以节点默认值为准（原先指向 v4/v3/v4 和 c18，与部署不符）---
try:
    from paths import DEFAULTS as _PATHS
    DATA.update({"corpus": _PATHS["corpus"], "subjects": _PATHS["subjects"],
                 "crafts": _PATHS["crafts"], "materials": _PATHS["materials"]})
    _DEFAULT_MODEL = _PATHS["model"]
except Exception:
    _DEFAULT_MODEL = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_DEFAULT_MODEL)
    ap.add_argument("--url", default=None, help="额外测一次 HTTP 服务")
    a = ap.parse_args()

    print("=== 1. 数据 ===")
    for k, rel in DATA.items():
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            print(f"  缺  {rel}")
            return 1
        n = sum(1 for _ in open(p, encoding="utf-8"))
        print(f"  有  {rel}  ({n} 行)")

    # 一致性检查：节点默认值 与 工作流里存的 必须指向同一批文件。
    # 这两个地方曾经各自漂移（节点 v7 / 工作流 v12），而冒烟照样通过——
    # 因为没人检查它们是否一致。这类"不报错的错"必须让它在冒烟阶段就叫。
    print("\n=== 1b. 节点默认值 vs 工作流 ===")
    try:
        import json as _json
        import sys as _sys
        _sys.path.insert(0, os.path.join(ROOT, "comfyui"))
        from local_style_hint import LocalStyleHint as _L
        _d = _L.INPUT_TYPES()["required"]
        _node = {os.path.basename(_d[k][1]["default"])
                 for k in ("语料文件", "题材文件", "工艺文件", "材质文件")}
        _wf = _json.load(open(os.path.join(ROOT, "comfyui/workflow_style_hint.json"),
                             encoding="utf-8"))
        _wl = {os.path.basename(v) for v in _wf["nodes"][0]["widgets_values"]
               if isinstance(v, str) and v.endswith(".jsonl")}
        if _node == _wl:
            print(f"  一致  {sorted(_node)}")
        else:
            print(f"  FAIL  节点 {sorted(_node)}")
            print(f"        工作流 {sorted(_wl)}")
            ok -= 1
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {type(e).__name__}: {e}")
        ok -= 1

    print("\n=== 2. 模型 ===")
    mp = os.path.join(ROOT, a.model)
    if not os.path.isdir(mp):
        print(f"  缺  {a.model}")
        print("  重建：python src/train_embed.py --epochs 6 --dev-ratio 0.01 "
              "--select-mode final --corpus data/raw/corpus_v16.jsonl "
              "--queries data/raw/queries_v4_fixed16.jsonl "
              f"--out-dir {a.model}")
        return 1
    print(f"  有  {a.model}")

    print("\n=== 3. 检索 ===")
    import local_style_hint as N
    node = N.LocalStyleHint()
    ok = 0
    for q, want, desc in CASES:
        try:
            out, dbg = node.run(q, a.model, DATA["corpus"], DATA["subjects"],
                                DATA["crafts"], DATA["materials"], True,
                                "文生视频", False, "片段（英文）",
                                "cpu", "不限", "导演/风格聚合", 1, "", False)
        except Exception as e:  # noqa: BLE001
            print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
            continue
        hit = want.lower() in out.lower()
        ascii_ratio = sum(1 for c in out if ord(c) < 128) / max(len(out), 1)
        good = hit and out.strip() != "" and ascii_ratio > 0.9
        ok += good
        why = "" if good else ("（未命中）" if not hit else "（输出不像英文片段）")
        print(f"  [{'OK' if good else 'FAIL'}] {desc}{why}")
        head = out[:100]
        if hit and want.lower() not in head.lower():
            i = out.lower().find(want.lower())
            head = out[:70] + " … " + out[max(0, i - 12):i + len(want) + 45]
        print(f"         {head}")

    if a.url:
        print("\n=== 4. HTTP 服务 ===")
        try:
            import json
            import urllib.request
            body = json.dumps({"query": CASES[0][0], "topk": 1}).encode("utf-8")
            req = urllib.request.Request(
                a.url, data=body,
                headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            print(f"  OK  {str(data)[:120]}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {type(e).__name__}: {e}")
            ok -= 1

    total = len(CASES)
    print(f"\n=== {ok}/{total} 通过 ===")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
