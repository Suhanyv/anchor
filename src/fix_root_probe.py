"""
修两条 codemod 遗留问题

1. ComfyUI 节点的 ROOT 不能用 dirname(dirname(__file__))
   ------------------------------------------------------
   节点被复制到 <ComfyUI>/custom_nodes/prompt_style_local/ 后，
   往上两级是 custom_nodes，不是项目根，默认路径会指向不存在的位置。

   改成主动探测：从 __file__ 和 CWD 分别向上找「包含 data/raw/corpus_v16.jsonl 的目录」。
   找到就用，找不到就回落，并让报错信息说清该怎么设。

2. 报错文案里残留的 F:\\llm 绝对路径 -> 改成通用说明
"""
import os
import re

FILES = [r"F:\llm\comfyui\local_style_hint.py",
         r"F:\llm\comfyui\comfyui_style_hint.py",
         r"F:\llm\src\serve_style.py"]

FIND_ROOT = '''
def _find_root():
    """找项目根：从本文件与 CWD 分别向上找含 data/raw 的目录。

    ComfyUI 节点会被复制到 <ComfyUI>/custom_nodes/ 下，此时 __file__ 的祖先里
    没有项目根，必须靠 CWD 或由用户显式设置路径。
    """
    seen = set()
    for start in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        p = start
        for _ in range(8):
            if p in seen:
                break
            seen.add(p)
            if os.path.isdir(os.path.join(p, "data", "raw")):
                return p
            nxt = os.path.dirname(p)
            if nxt == p:
                break
            p = nxt
    return os.path.dirname(os.path.abspath(__file__))


ROOT = _find_root()
'''

ROOT_LINE = re.compile(r'^ROOT = os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)\s*$', re.M)


def main():
    for p in FILES:
        if not os.path.exists(p):
            print(f"跳过（不存在）: {p}")
            continue
        s = open(p, encoding="utf-8").read()
        orig = s
        note = []

        # 1) 换 ROOT 推断
        if ROOT_LINE.search(s):
            s = ROOT_LINE.sub(FIND_ROOT.strip("\n"), s, count=1)
            note.append("ROOT->探测")

        # 2) 通用化报错文案里的 F:\llm
        before = s.count("F:\\llm")
        s = s.replace("F:\\\\llm\\\\models\\\\e5-director-c9", "<项目根>/models/e5-director-c18")
        s = s.replace("F:\\llm\\models\\e5-director-c9", "<项目根>/models/e5-director-c18")
        s = re.sub(r'F:\\\\llm\\\\[^\s"\'）)]*', '<项目根>/...', s)
        s = re.sub(r'F:\\llm\\[^\s"\'）)]*', '<项目根>/...', s)
        after = s.count("F:\\llm")
        if before != after:
            note.append(f"文案 {before}->{after}")

        if s != orig:
            open(p, "w", encoding="utf-8").write(s)
            print(f"  {os.path.basename(p):<28} {', '.join(note)}")
        else:
            print(f"  {os.path.basename(p):<28} 无需改动")

    # 语法自检
    import ast
    print()
    bad = 0
    for p in FILES:
        if not os.path.exists(p):
            continue
        try:
            ast.parse(open(p, encoding="utf-8").read())
        except SyntaxError as e:
            bad += 1
            print(f"  语法错 {os.path.basename(p)}: {e}")
    print(f"语法错误 {bad} 个")

    # 复查
    left = []
    for p in FILES:
        if os.path.exists(p) and "F:\\llm" in open(p, encoding="utf-8").read():
            left.append(os.path.basename(p))
    print(f"残留 F:\\llm: {left if left else '无 ✅'}")
    print("\n### FIX_ROOT_DONE")


if __name__ == "__main__":
    main()
