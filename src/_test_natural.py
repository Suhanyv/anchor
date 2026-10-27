"""原样测试：用户新写的一句话（自然中文，未提导演）"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

Q = "两辆拉力赛车在沙地赛场上竞速，五个镜头"

node = N.LocalStyleHint()
d = N.LocalStyleHint.INPUT_TYPES()["required"]
M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
            d["材质文件"][1]["default"])

items, _m, subj, _d, craft, mat = N._rank(
    Q, M, C, "cpu", 3, "导演/风格聚合", "视频", S, K, MT, True)
print("=== 检索到的风格 top3 ===")
for it in items:
    print(f"  {it.get('director_zh') or it.get('director')} "
          f"{float(it.get('score') or 0):.4f}  "
          f"kw={'、'.join((it.get('kw_zh') or [])[:4])}")
print(f"=== 内容通道 ===\n  主体 {(subj or {}).get('zh', '（无）')} "
      f"{(subj or {}).get('score', 0)}\n  工艺 {(craft or {}).get('zh', '（无）')} "
      f"{(craft or {}).get('score', 0)}\n  材质 {(mat or {}).get('zh', '（无）')} "
      f"{(mat or {}).get('score', 0)}")

for fmt, prop, tag in (("自动（识别平台）", False, "默认：多镜头，提案关"),
                       ("即梦 Seedance 2.5 · 整段（中文）", True, "即梦整段 + 提案开")):
    out, dbg = node.run(Q, M, C, S, K, MT, True, "文生视频", prop, fmt,
                        "cpu", "视频", "导演/风格聚合", 1, "", False)
    print(f"\n########## {tag} ##########")
    print(out)
    print("\n--- 调试 ---")
    for l in dbg.split("\n"):
        if l.strip() and not l.startswith(("Loading", "Redirects")):
            print("  " + l[:120])

print("\n### NATURAL_TEST_DONE")
