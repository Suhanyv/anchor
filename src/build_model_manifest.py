"""
补「权重 ↔ 语料」的对应关系（按时间戳反推，不确定的标出来）

为什么
------
39 个 e5 模型版本，train_log 里只记了超参，没记喂的是哪一版语料。
后果：权重和语料对不上号，门槛（0.52 这些常数）不知道是在哪一版上标定的。

做法
----
每个模型目录的创建时间，对上「那一刻最新的语料文件」，就是它当时用的版本。
这是推断，不是记录——所以每条都带 confidence，时间接近的标 low。
"""
import json
import os
import time

ROOT = r"F:\llm"
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "raw", "model_manifest.json")

PREFIX = ("corpus_v", "subjects_v", "crafts_v", "materials_v")


def collect(kind):
    """收集某一类文件，返回 [(版本号, 路径, 修改时间)]"""
    out = []
    for fn in os.listdir(RAW):
        if not fn.startswith(kind) or not fn.endswith(".jsonl"):
            continue
        try:
            ver = int("".join(c for c in fn.split("_v")[1].split(".")[0] if c.isdigit()))
        except Exception:
            continue
        p = os.path.join(RAW, fn)
        out.append((ver, p, os.path.getmtime(p)))
    return sorted(out)


def newest_before(items, t):
    """在 t 之前最新的那一版"""
    cand = [x for x in items if x[2] <= t + 60]
    return cand[-1] if cand else (items[0] if items else None)


def main():
    kinds = {k: collect(k) for k in PREFIX}
    models = []
    mdir = os.path.join(ROOT, "models")
    for name in sorted(os.listdir(mdir)):
        d = os.path.join(mdir, name)
        if not os.path.isdir(d) or not name.startswith("e5-"):
            continue
        t = os.path.getctime(d)
        row = {"model": name,
               "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(t)),
               "assumed": {}, "confidence": "high"}
        close = False
        for k, items in kinds.items():
            hit = newest_before(items, t)
            if not hit:
                continue
            row["assumed"][k.replace("_v", "")] = os.path.basename(hit[1])
            # 语料改后 10 分钟内建的模型：可能是新旧交界，标 low
            if abs(t - hit[2]) < 600:
                close = True
        if close:
            row["confidence"] = "low"
        models.append(row)

    latest = {k: os.path.basename(v[-1][1]) if v else None
              for k, v in kinds.items()}
    doc = {
        "_about": "每个模型权重是拿哪一版语料训的。时间戳反推，不是原始记录。",
        "_why": "train_log 只记超参，没记数据版本；39 个版本无法精确复现。"
                "从今往后新建模型时请手写这一项。",
        "current_deployed": "e5-director-c27",
        "current_indexes": latest,
        "models": models,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print(f"  写了 {len(models)} 个模型的对应关系")
    print(f"  当前语料: {latest}")
    low = [m for m in models if m["confidence"] == "low"]
    print(f"  置信度 low 的 {len(low)} 个（时间贴近语料改动，可能是交界）")
    for m in models[-6:]:
        print(f"    {m['model']:<22} {m['created']}  "
              f"{m['assumed'].get('corpus','?')}  {m['confidence']}")
    print("\n### MANIFEST_DONE")


if __name__ == "__main__":
    main()
