"""
把 src/ 与 comfyui/ 里所有硬编码的 F:\\llm 改成自动推断的项目根目录。

为什么要做
----------
干净克隆测试挖出来的：62 个文件共 80 处写死了 `F:\\llm`。
新用户机器上没有这个路径，脚本会直接报错——**这个仓库此前只在作者机器上能跑。**

改法
----
1. `ROOT = r"F:\\llm"`  ->  从 __file__ 往上两级推断
2. `r"F:\\llm\\a\\b.txt"`  ->  `os.path.join(ROOT, "a/b.txt")`（正则批量替换）
3. 缺 `import os` 的补上

注意：一次性的分析脚本（analyze_prompt*、eval_real*、diag_* 等）改完后路径可移植，
但它们引用的输入文件（prompt_real_05.txt、corpus_v10.jsonl 等）已不在仓库里，
跑了仍会因缺文件而失败——这是数据问题，不是路径问题，在 LIMITATIONS 里已说明。
"""
import os
import re
import sys

TARGETS = [os.path.join(ROOT, "src"), os.path.join(ROOT, "comfyui")]

ROOT_LINE = re.compile(r'^(\s*)ROOT\s*=\s*r"F:\\llm"\s*$', re.M)

# 匹配 os.path.join(ROOT, "....") 整串（不跨越引号）
ABS_STR = re.compile(r'r"F:\\llm((?:\\[^"\\]*)*)"')

NEW_ROOT = ('ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))')

# ComfyUI 节点在 custom_nodes 下被单独拷走，不能用 __file__ 推项目根
NODE_ROOT = 'ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))'


def convert_abs(m):
    tail = m.group(1)
    parts = [p for p in tail.split("\\") if p]
    if not parts:
        return "ROOT"
    rel = "/".join(parts)
    return f'os.path.join(ROOT, "{rel}")'


def process(path):
    orig = open(path, encoding="utf-8").read()
    s = orig
    changed = []

    if ROOT_LINE.search(s):
        s = ROOT_LINE.sub(lambda m: f"{m.group(1)}{NEW_ROOT}", s, count=1)
        changed.append("ROOT")

    n_abs = len(ABS_STR.findall(s))
    if n_abs:
        s = ABS_STR.sub(convert_abs, s)
        changed.append(f"{n_abs}处绝对路径")

    if changed and not re.search(r'^\s*import os\s*$', s, re.M):
        # 插到第一个 import 之前
        m = re.search(r'^(import |from )', s, re.M)
        if m:
            s = s[:m.start()] + "import os\n" + s[m.start():]
        else:
            s = "import os\n" + s
        changed.append("补 import os")

    if s != orig:
        open(path, "w", encoding="utf-8").write(s)
        return changed
    return None


def main():
    total_files = 0
    total_changes = 0
    details = []
    for d in TARGETS:
        if not os.path.isdir(d):
            print(f"跳过不存在的目录: {d}")
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(d, fn)
            ch = process(p)
            if ch:
                total_files += 1
                total_changes += 1
                details.append((fn, ch))
    print(f"改了 {total_files} 个文件")
    for fn, ch in details:
        print(f"  {fn:<36} {', '.join(ch)}")

    # 语法自检
    import ast
    bad = []
    for d in TARGETS:
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(d, fn)
            try:
                ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError as e:
                bad.append((fn, e))
    if bad:
        print("\n语法错误：")
        for fn, e in bad:
            print(f"  {fn}: {e}")
    else:
        print("\n全部语法通过 ✅")

    # 复查残留
    left = 0
    for d in TARGETS:
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            t = open(os.path.join(d, fn), encoding="utf-8").read()
            if "F:\\llm" in t:
                left += 1
                print(f"  残留 {fn}")
    print(f"残留硬编码文件: {left}")
    print("\n### CODEMOD_DONE")


if __name__ == "__main__":
    main()
