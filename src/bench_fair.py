"""
公平基准：把「模型变差」和「题目变难」分开

为什么需要它
------------
今天做过一个决定性实验（v0.1.3 时）：

    同一批 826 条候选，只换模型
        c22（v19 训）：运镜 44/64，场景 60/80
        c24（v20 训）：运镜 44/64，场景 60/80     <- 一模一样
    同一模型换候选集
        c24 候选 826 ：运镜 44/64，场景 60/80
        c24 候选 910 ：运镜 40/60，场景 55/75     <- 只是候选多了 10%

结论：**模型完全没退步。** 之前的"加数据就稀释"里，有相当一部分
是候选池变大导致的 top-1 自然下降，被我误读成了模型退化。

从今往后，任何"语料变了"的对比都必须报两组数：

    绝对（当前候选池）   用户实际会遇到的水平
    受控（固定候选池）   同一题目下模型能力的真实变化

用法
----
    # 固定候选池 = 旧语料（自动取 doc_id 交集）
    python src/bench_fair.py \
        --model models/e5-director-c24 \
        --corpus data/raw/corpus_v20.jsonl \
        --snapshot data/raw/corpus_v19.jsonl

    # 也可以显式给一个 id 快照文件（每行一个 doc_id）
    python src/bench_fair.py --model X --corpus Y --ids snapshot.txt
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--snapshot", default=None, help="旧语料 jsonl，取 doc_id 交集")
    ap.add_argument("--ids", default=None, help="doc_id 快照文件，每行一个")
    ap.add_argument("--base-model", default=None, help="可选：对照组模型（跑同一受控池）")
    a = ap.parse_args()

    corpus = load_jsonl(a.corpus)

    if a.ids:
        keep = {l.strip() for l in open(a.ids, encoding="utf-8") if l.strip()}
    elif a.snapshot:
        keep = {d["doc_id"] for d in load_jsonl(a.snapshot)}
    else:
        raise SystemExit("需要 --snapshot 或 --ids 之一来定义固定候选池")

    subset = [d for d in corpus if d["doc_id"] in keep]
    if not subset:
        raise SystemExit("固定候选池为空：doc_id 一个都没对上")

    tmp = os.path.join(ROOT, "data", "raw", "_fair_subset.jsonl")
    with open(tmp, "w", encoding="utf-8") as f:
        for d in subset:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"当前语料 {len(corpus)} 条 / 固定候选池 {len(subset)} 条"
          f"（{len(subset)/len(corpus):.0%}）")
    print(f"模型：{a.model}\n")

    import subprocess

    def run(script, model, corpus_path, label):
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "src", script), model, corpus_path, "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=ROOT)
        out = r.stdout or ""
        lines = [l.strip() for l in out.splitlines() if "=" in l and ("导演@" in l or "top1" in l)]
        print(f"  [{label}]")
        for l in lines[:3]:
            print(f"    {l}")
        return lines

    model_abs = os.path.join(ROOT, a.model) if not os.path.isabs(a.model) else a.model
    if not os.path.isdir(model_abs):
        raise SystemExit(f"模型目录不存在：{model_abs}")

    print("=== 绝对：当前候选池（用户实际会遇到）===")
    run("eval_motion.py", model_abs, os.path.join(ROOT, a.corpus), "运镜 25 题")
    run("eval_scene.py", model_abs, os.path.join(ROOT, a.corpus), "场景 20 题")

    print("\n=== 受控：固定候选池（同一题目下比模型能力）===")
    run("eval_motion.py", model_abs, tmp, "运镜 25 题")
    run("eval_scene.py", model_abs, tmp, "场景 20 题")

    if a.base_model:
        bm = os.path.join(ROOT, a.base_model) if not os.path.isabs(a.base_model) else a.base_model
        print(f"\n=== 受控池 + 对照模型 {os.path.basename(bm)} ===")
        run("eval_motion.py", bm, tmp, "运镜 25 题")
        run("eval_scene.py", bm, tmp, "场景 20 题")

    os.remove(tmp)
    print("\n判读：绝对数下降但受控数不变 -> 是候选池变大，不是模型退化。")
    print("\n### BENCH_FAIR_DONE")


if __name__ == "__main__":
    main()
