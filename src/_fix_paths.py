"""把五个脚本的路径改成从 paths.DEFAULTS 取（唯一真相）"""
import os
import re

SRC = r"F:\llm\src"
TARGETS = ["serve_style.py", "gen_format_samples.py", "audit_prompt_fill.py",
           "calibrate_floors.py", "test_real_queries.py", "test_kb_v3.py"]

BLOCK = '''
# --- 统一路径：以节点默认值为准，避免脚本与部署漂移 ---
try:
    from paths import DEFAULTS as _PATHS
    M, C = _PATHS["model"], _PATHS["corpus"]
    S, K, MT = _PATHS["subjects"], _PATHS["crafts"], _PATHS["materials"]
except Exception:
    pass
'''

for name in TARGETS:
    p = os.path.join(SRC, name)
    if not os.path.exists(p):
        print(f"  跳过（不存在）{name}")
        continue
    s = open(p, encoding="utf-8").read()
    if "_PATHS" in s:
        print(f"  已有 {name}")
        continue
    # 插在最后一个顶层赋值之后、`def main` 之前（模块级变量都已定义）
    m = re.search(r"(?m)^def main\(", s)
    if not m:
        m = re.search(r'(?m)^if __name__ == "__main__":', s)
    if not m:
        print(f"  ⚠️ 找不到插入点 {name}")
        continue
    s = s[:m.start()] + BLOCK.strip() + "\n\n\n" + s[m.start():]
    open(p, "w", encoding="utf-8").write(s)
    print(f"  已改 {name}")

# smoke_test 用 DATA 字典 + args.model，单独处理
p = os.path.join(SRC, "smoke_test.py")
if os.path.exists(p):
    s = open(p, encoding="utf-8").read()
    if "_PATHS" not in s:
        m = re.search(r"(?m)^def main\(", s)
        blk = '''
# --- 统一路径：以节点默认值为准（原先指向 v4/v3/v4 和 c18，与部署不符）---
try:
    from paths import DEFAULTS as _PATHS
    DATA.update({"corpus": _PATHS["corpus"], "subjects": _PATHS["subjects"],
                 "crafts": _PATHS["crafts"], "materials": _PATHS["materials"]})
    _DEFAULT_MODEL = _PATHS["model"]
except Exception:
    _DEFAULT_MODEL = None
'''
        if m:
            s = s[:m.start()] + blk.strip() + "\n\n\n" + s[m.start():]
            # a.model 的默认值也换成节点的
            s = re.sub(r'(add_argument\("-?-?model[^\n]*default=)[^,)]+',
                       r'\1_DEFAULT_MODEL', s)
            open(p, "w", encoding="utf-8").write(s)
            print("  已改 smoke_test.py")
        else:
            print("  ⚠️ smoke_test 找不到插入点")
    else:
        print("  已有 smoke_test.py")
