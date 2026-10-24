"""分析真实提示词 05（七镜分镜）的结构，并计算我们系统能贡献的比例。"""
import os
import re

P = os.path.join(ROOT, "data/raw/prompt_real_05.txt")

t = open(P, encoding="utf-8").read()
body = t.split("---")[1].strip()


def zh(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))


total = zh(body)
print("=== 体量 ===")
print(f"  中文字符 {total}")
print("  对比：04 分镜脚本 1516 字 / 02 英文场景 255 词")
print()

shots = re.findall("【(第[一二三四五六七]镜)[：:]([^】]+)】", body)
print("=== 镜头数 ===")
print(f"  {len(shots)} 个镜头")
for i, (n, title) in enumerate(shots, 1):
    print(f"    {i}. {n}：{title}")
print()

LQ, RQ = "\u201c", "\u201d"
lines = re.findall(LQ + "([^" + RQ + "]{6,})" + RQ, body)
print("=== 台词 ===")
print(f"  {len(lines)} 句")
for line in lines:
    print(f"    {LQ}{line}{RQ}")
print()

m = re.search("【整体风格】(.+)$", body, re.S)
style = m.group(1).strip() if m else ""
sz = zh(style)
print("=== 整体风格块（★我们能贡献的部分）===")
print(f"  {sz} 字 = 全篇 {sz/total:.1%}")
print(f"  内容开头：{style[:120]}...")
print()

print("=== 各镜字数分布 ===")
idx = [x.start() for x in re.finditer("【第[一二三四五六七]镜", body)]
idx.append(body.find("【整体风格】"))
print(f"{'镜头':<12} {'字数':>5} {'占比':>7}")
for i in range(len(idx) - 1):
    seg = body[idx[i]:idx[i + 1]]
    c = zh(seg)
    nm = re.match("【([^】]+)】", seg).group(1)
    if i == len(idx) - 2:
        nm = "整体风格"
    print(f"{nm:<12} {c:>5} {c/total:>6.1%}")
print()

print("=== 体裁特征 ===")
feats = {
    "多镜序列(7 镜)": len(shots) == 7,
    "角色台词 + 口型同步要求": "口型同步" in body,
    "参考图延续但该画面不入片": "这个画面不要出现在视频中" in body,
    "画外角色(玉帝从不出现)": "玉皇大帝所在的方向" in body,
    "跨作品混搭(混沌四神 x 中国神话)": all(k in body for k in ("恐虐", "奸奇", "纳垢")),
    "逐镜运镜指令": body.count("镜头") >= 15,
    "尺度对比(山岳→房屋→拳头→数厘米)": "拳头大小" in body and "数厘米" in body,
}
for k, v in feats.items():
    print(f"  {'有' if v else '无'}  {k}")
print(f"  「镜头」一词出现 {body.count('镜头')} 次")
print()

print("=== 结论 ===")
print(f"  我们能贡献的整体风格块 = {sz} / {total} = {sz/total:.1%}")
print("  其余：镜头序列、台词、口型、参考图延续、画外角色、尺度演变 —— 全不在我们范围")
print()
print("### P5_ANALYZE_DONE")
