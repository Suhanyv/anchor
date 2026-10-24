"""
从外部提示词库 part3 提取「工艺/材质」风格词，对照我们语料的缺口

part3 与 part1 体裁完全不同
--------------------------
part1：场景/海报/人物类（"一张写实风格的竖版街头时尚照片…"）
part3：**工艺/媒介类**，结构高度统一：
        风格：<工艺名> + <材质细节> + <底层质感>（不是<容易混淆的同类工艺>）
        主题：<作品>女角色<工艺>肖像
即 part3 的"风格"槽里装的全是**材料与工艺**。

这正好是我们最弱的一环（材质/光文档级评测 47%）。
而且它揭示了一个我们完全没有的轴：
    风格 = 导演（谁拍的） + 工艺/媒介（用什么做出来的）
我们只有前者。

数据来源：水仙的AI提示词 https://github.com/BaYue-SYJ/shuixian-prompts
许可：署名使用协议（须保留出处并链接回仓库）；原文版权归原作者。
本脚本只提取**工艺名词**并统计，不复制整段提示词。
"""
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPILL = r"C:\Users\15758\AppData\Local\Temp\dsh-spill-I9prYm\session-aa279cebe1b5\4212129d7139-web_fetch.txt"
OUT_DIR = os.path.join(ROOT, "data", "raw", "external")
OUT_RAW = os.path.join(OUT_DIR, "shuixian_part3_README.txt")
OUT = os.path.join(ROOT, "bench", "external_craft_vocab.json")
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v14.jsonl")

# 已知工艺/材质词表（用于在 style 槽里识别）
CRAFT = [
    "玻璃内画", "双重曝光", "VHS", "CRT", "磁迹", "时间码", "PCB", "蚀刻", "覆铜",
    "拜占庭马赛克", "马赛克", "金箔", "青版蓝晒", "氰版", "普鲁士蓝", "X光",
    "日晒", "solarization", "孔特", "粉笔", "速写", "火柴盒贴画", "平版套色",
    "等高线", "水拓", "ebru", "大理石纹", "哥白林", "挂毯", "蓝染", "絞り",
    "shibori", "糖画", "干刻", "铜版画", "刮刻", "美柔汀", "mezzotint", "蛋彩",
    "湿壁画", "fresco", "蜡彩", "encaustic", "激光切割", "木皮", "窗花", "剪纸",
    "气象雷达", "沙坛城", "金缮", "莳绘", "丝绸刺绣", "刺绣", "全息", "镭射",
    "彩绘玻璃", "绘马", "孔版印刷", "Risograph", "赛璐璐", "泼墨", "琳派",
    "轴测图", "axonometric", "图纸网格", "胶片颗粒", "红外", "假彩色",
    "顶光", "侧光", "高光", "暗角", "体积光", "焦外", "景深",
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(SPILL):
        print(f"缺源文件 {SPILL}")
        return
    text = open(SPILL, encoding="utf-8", errors="ignore").read()
    print(f"part3 源文本 {len(text)} 字符")

    header = (
        "# 外部提示词库 part3 原文记录（分析用，不入训练集）\n"
        "# 来源：水仙的AI提示词 https://github.com/BaYue-SYJ/shuixian-prompts\n"
        "# 许可：署名使用协议（可学习/fork/非商业转载，须保留出处并链接回仓库）\n"
        "# 提示词原文版权归各自原作者；本文件仅作词频分析。\n"
        "# 特征：part3 以「工艺/材质」风格为主（玻璃内画/马赛克/蓝晒/铜版/莳绘…）\n\n"
    )
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        f.write(header + text)
    print(f"原文存档 -> {OUT_RAW}  ({os.path.getsize(OUT_RAW)/1024:.0f} KB)")

    # 抽取「风格：...」槽
    styles = re.findall(r"风格：([^\n]{4,220})", text)
    print(f"\n抽到「风格：」槽 {len(styles)} 条")
    print("样例：")
    for s in styles[:5]:
        print(f"  {s[:100]}")

    # 工艺词频
    cnt = Counter()
    for s in styles:
        for c in CRAFT:
            if c in s:
                cnt[c] += 1
    print(f"\n=== 识别出的工艺/材质词（按频次）===")
    for c, n in cnt.most_common(40):
        print(f"  {c:<14} {n}")

    # 对照我们语料
    corpus_text = []
    for line in open(CORPUS, encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        corpus_text.append(d.get("description", ""))
        corpus_text.append(d.get("text_semantic", ""))
        corpus_text.append(" ".join(d.get("style_tags") or []))
    ct = " ".join(corpus_text).lower()
    # 中文工艺词在我们的英文语料里查不到，故用英文对应词判断
    EN = {
        "玻璃内画": ["reverse glass painting", "painted inside glass"],
        "马赛克": ["mosaic", "tesserae"],
        "金箔": ["gold leaf", "gilt"], "氰版": ["cyanotype", "prussian blue"],
        "X光": ["x-ray", "radiograph"], "日晒": ["solarisation", "solarization"],
        "粉笔": ["chalk", "conté", "conte"], "火柴盒贴画": ["matchbox", "lithograph"],
        "等高线": ["contour"], "水拓": ["marbled", "ebru"],
        "挂毯": ["tapestry", "gobelin"], "蓝染": ["indigo", "shibori"],
        "糖画": ["sugar"], "铜版画": ["etching", "copper plate"],
        "刮刻": ["scratchboard"], "美柔汀": ["mezzotint"], "蛋彩": ["tempera"],
        "湿壁画": ["fresco"], "蜡彩": ["encaustic", "wax"],
        "剪纸": ["papercut", "paper cut"], "金缮": ["kintsugi"],
        "莳绘": ["maki-e", "lacquer"], "刺绣": ["embroidery", "stitched"],
        "全息": ["holographic", "hologram"], "彩绘玻璃": ["stained glass"],
        "孔版印刷": ["risograph", "screen print"], "赛璐璐": ["cel", "cel animation"],
        "泼墨": ["splashed ink", "ink splash"], "轴测图": ["axonometric", "isometric"],
        "红外": ["infrared"], "胶片颗粒": ["film grain", "grain"],
    }
    print(f"\n=== 我们语料里有对应英文吗 ===")
    missing = []
    for c, ens in EN.items():
        got = sum(ct.count(e) for e in ens)
        ext = cnt.get(c, 0)
        if ext == 0:
            continue
        mark = "有" if got else "缺"
        if not got:
            missing.append((c, ext))
        print(f"  {c:<12} 外部{ext:>3}次  我们{got:>4}次  {mark}  ({ens[0]})")

    print(f"\n=== 我们完全没有的工艺 ===  {len(missing)} 个")
    for c, n in sorted(missing, key=lambda x: -x[1]):
        print(f"  {c}（外部 {n} 次）")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": "shuixian-prompts part3",
                   "license": "署名使用协议，须保留出处",
                   "style_slots": len(styles),
                   "craft_freq": dict(cnt.most_common()),
                   "missing": [{"craft": c, "ext": n} for c, n in missing]},
                  f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### CRAFT_VOCAB_DONE")


if __name__ == "__main__":
    main()
