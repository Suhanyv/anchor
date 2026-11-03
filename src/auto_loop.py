"""
自动学习循环：造候选 → 判 → 留/弃，跑 N 轮

每轮的结论都记进 data/eval/auto_loop.log，被拒的也记——
"什么没用"和"什么有用"一样是知识。
"""
import os
import re
import subprocess
import sys

ROOT = r"F:\llm"
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
LOG = os.path.join(ROOT, "data", "eval", "auto_loop.log")


def run(script, env, args=()):
    cmd = [PY, os.path.join(ROOT, "src", script), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    return (p.stdout or "") + (p.stderr or "")


def main(rounds=5):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
           "HF_HOME": r"F:\llm\cache\hf", "HF_HUB_OFFLINE": "1",
           "TOKENIZERS_PARALLELISM": "false"}
    lines = []
    for i in range(1, rounds + 1):
        print(f"\n===== 第 {i} 轮 =====")
        gen = run("auto_gen.py", env)
        m = re.search(r"生成候选 (\d+) 条", gen)
        n = int(m.group(1)) if m else 0
        print(f"  造出候选 {n} 条")
        if n == 0:
            lines.append(f"round {i}: 无候选（开发集已经没有可补的）")
            print("  没有可补的了，停")
            break
        cand = os.path.join(ROOT, "data", "eval", "cand_auto.jsonl")
        learn = run("auto_learn.py", env, (cand,))
        kept = "保留" in learn and "回滚" not in learn
        nums = re.findall(r"'heldout_style': (\d+)", learn)
        b = nums[0] if nums else "?"
        a = nums[1] if len(nums) > 1 else "?"
        print(f"  {b}% -> {a}%   {'保留' if kept else '回滚'}")
        lines.append(f"round {i}: 候选 {n} 条  {b}% -> {a}%  {'保留' if kept else '回滚'}")

    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n日志 -> " + LOG)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
