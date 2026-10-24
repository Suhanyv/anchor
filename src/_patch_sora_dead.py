"""把 Sora 2 标记为已停服（保留代码与文档作存档，但下拉里标清楚）"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old = '"Sora 2（中文，八模块·社区总结）",'
new = '"Sora 2（已停服 · 仅存档）",'
if old in s:
    s = s.replace(old, new, 1)
    print("  下拉选项已改为：Sora 2（已停服 · 仅存档）")
else:
    print("  已改过或找不到，跳过")

# 调试提示补一句
s = s.replace(
    '"【格式】Sora 2 八模块（注意：这个结构来自 CSDN 博客的社区总结，"\n'
    '                    "不是 OpenAI 官方；官方 cookbook 我们访问不到 403）\\n" + dbg)',
    '"【格式】Sora 2 八模块 · 该平台已停止服务，本格式仅作存档。"\n'
    '                    "结构来自 CSDN 博客的社区总结（CC BY-SA 4.0），非官方；"\n'
    '                    "官方 cookbook 亦不可达（403）。\\n" + dbg)')

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
fmts = N.LocalStyleHint.INPUT_TYPES()["required"]["输出格式"][0]
print(f"  格式数 {len(fmts)}")
for f in fmts:
    mark = "  <- 已停服" if "停服" in f else ""
    print("   -", f, mark)
