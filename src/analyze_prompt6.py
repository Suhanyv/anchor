"""分析真实提示词 06（10 秒一镜到底），并跑一次兴趣评估。"""
import os
import re
import sys

sys.path.insert(0, os.path.join(ROOT, "comfyui"))
import local_style_hint as N  # noqa: E402

P = os.path.join(ROOT, "data/raw/prompt_real_06.txt")
M = os.path.join(ROOT, "models/e5-director-c10")
C = os.path.join(ROOT, "data/raw/corpus_v10.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v1.jsonl")

body = open(P, encoding="utf-8").read().split("---")[1].strip()


def zh(s):
    return len(re.findall(r"[\u4e00-\u9fff]", s))


total = zh(body)
print("=== 体量 ===")
print(f"  中文字符 {total}")

shots = re.findall("【(分镜0\\d)[｜|]([^】]+)】", body)
print()
print("=== 分镜与时长 ===")
print(f"  {len(shots)} 个分镜")
durs = re.findall("时间：(00:\\d\\d[–-]00:\\d\\d)，共(\\d)秒", body)
for i, (n, t) in enumerate(shots, 1):
    d = durs[i - 1] if i - 1 < len(durs) else ("?", "?")
    print(f"    {i}. {n}：{t.strip()}   {d[0]}  共 {d[1]} 秒")
tot = sum(int(d[1]) for d in durs if d[1].isdigit())
print(f"  合计 {tot} 秒（原文声明 6+2+2=10 秒）")

print()
print("=== 结构块字数 ===")
blocks = [("空间连续性硬约束", "【空间连续性硬约束】", "【分镜01"),
          ("分镜01 移动", "【分镜01", "【分镜02"),
          ("分镜02 电视穿入", "【分镜02", "【分镜03"),
          ("分镜03 教室小提琴", "【分镜03", "【全片摄影"),
          ("全片摄影剪辑声音★", "【全片摄影", None)]
for name, a, b in blocks:
    i = body.find(a)
    j = body.find(b) if b else len(body)
    if i < 0:
        continue
    c = zh(body[i:j])
    print(f"  {name:<20} {c:>5} 字 {c/total:>7.1%}")

print()
print("=== 体裁特征 ===")
feats = {
    "多镜（3 分镜）": len(shots) == 3,
    "时间轴逐段切分（共 8 个时间段）": len(re.findall("\\d\\d:\\d\\d[–-]\\d\\d:\\d\\d", body)) >= 8,
    "空间连续性硬约束（不硬切/不瞬移/不穿越墙体）": all(k in body for k in ("不硬切", "不瞬移", "不穿越墙体")),
    "三张参考图分工": "图一" in body and "图二" in body,
    "明确移动路线": "学校正门 → 左侧门柱" in body,
    "时长算术约束（6+2+2=10）": "6秒＋电视机推近并穿入2秒" in body,
    "逐段声音设计": "声音：" in body,
    "转场禁止项（无爆炸/玻璃破碎/黑洞）": "玻璃破碎" in body,
    "尺寸/画幅指定": "16:9" in body,
}
for k, v in feats.items():
    print(f"  {'有' if v else '无'}  {k}")

print()
print("=== 兴趣评估（三信号）===")
QS = [
    ("放假后空无一人的学校，黑色铁门敞开，地面斑驳阳光，夏日下午", "学校起始环境"),
    ("杂货铺门口的老式CRT电视机，屏幕上是纯黑白雪花点", "电视雪花点"),
    ("女生坐在窗边拉小提琴，柔白光，空气中有尘埃光束", "教室小提琴"),
]
node = N.LocalStyleHint()
print(f"{'场景':<14} {'top1':<24} {'分':>6}  {'题材通道':<20}")
print("-" * 84)
for q, tag in QS:
    out, dbg = node.run(q, M, C, S, "cpu", "视频", "导演/风格聚合", 1, "", False)
    lines = [l for l in dbg.split("\n") if l.strip()]
    subj = next((l for l in lines if l.startswith("题材")), "")
    rank = next((l for l in lines if l.strip()[:1].isdigit()), "")
    t1 = rank.split(". ")[1][:22] if rank else "?"
    sc = rank.split()[-1] if rank else "?"
    sub = subj.replace("题材: ", "").split("(")[0][:20]
    print(f"{tag:<14} {t1:<24} {sc:>6}  {sub:<20}")
print()
print("### P6_DONE")
