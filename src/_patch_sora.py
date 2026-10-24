"""注册 Sora 2 格式到节点（补丁脚本，避免 shell 转义）"""
import ast
import re

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# 1) 格式列表加一项
old = '                    "Veo 3（英文，8 秒单镜）",'
new = old + '\n                    "Sora 2（中文，八模块·社区总结）",'
if "Sora 2（中文" not in s:
    assert old in s, "找不到 Veo 选项"
    s = s.replace(old, new, 1)
    print("  格式列表已加 Sora")
else:
    print("  格式列表已有 Sora，跳过")

# 2) 分发
anchor = '        if want.startswith("Veo"):'
block = (
    '        if want.startswith("Sora"):\n'
    '            if not is_video:\n'
    '                return (_structured(items[0], subj, craft, mat, domain_used),\n'
    '                        "【格式】Sora 是视频格式，当前是图片域 -> 回落到结构化\\n" + dbg)\n'
    '            return (_fmt_sora(items[0], subj, craft, mat, domain_used, 中文描述),\n'
    '                    "【格式】Sora 2 八模块（注意：这个结构来自 CSDN 博客的社区总结，"\n'
    '                    "不是 OpenAI 官方；官方 cookbook 我们访问不到 403）\\n" + dbg)\n'
)
if 'want.startswith("Sora")' not in s:
    assert anchor in s, "找不到 Veo 分发锚点"
    s = s.replace(anchor, block + anchor, 1)
    print("  分发已加 Sora")
else:
    print("  分发已有 Sora，跳过")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

# 校验
import sys
sys.path.insert(0, r"F:\llm\comfyui")
import importlib
import local_style_hint as N
importlib.reload(N)
fmts = N.LocalStyleHint.INPUT_TYPES()["required"]["输出格式"][0]
print(f"  格式数 {len(fmts)}")
for f in fmts:
    print("   -", f)
print("  _fmt_sora 存在:", hasattr(N, "_fmt_sora"), " _fmt_veo 存在:", hasattr(N, "_fmt_veo"))
