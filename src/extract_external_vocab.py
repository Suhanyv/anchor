"""
从开源提示词库提取「具体描述词」，对比我们语料的覆盖情况

数据来源
--------
水仙的AI提示词 https://github.com/BaYue-SYJ/shuixian-prompts
    5,430 条中文 AI 绘画提示词，JSON 开源
    许可：署名使用协议 —— 可自由学习/fork/非商业转载，
          **必须保留出处并链接回本仓库**；提示词原文版权归各自原作者。

使用方式（重要）
--------------
**只提取词表，不复制原文。** 理由：
  1. 原文版权归原作者，整体搬运不合适
  2. 我们要的是"物件/材质/光"的词汇，不是整段提示词
  3. 提取词频 + 归属统计，是分析行为不是复制

产出
----
bench/external_vocab.json   外部提示词里的高频具体词，以及我们语料缺哪些
"""
import json
import os
import re
from collections import Counter

SPILL = r"C:\Users\15758\AppData\Local\Temp\dsh-spill-I9prYm\session-aa279cebe1b5\ac8400eb81a1-web_fetch.txt"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "raw", "external")
OUT_RAW = os.path.join(OUT_DIR, "shuixian_part1_README.txt")
OUT_VOCAB = os.path.join(ROOT, "bench", "external_vocab.json")
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v11.jsonl")

# 按类别定义要提取的词元（外部分析用，非训练数据）
CATS = {
    "光": ["侧光", "逆光", "柔光", "硬光", "顶光", "底光", "漫射", "高光", "暗角",
           "轮廓光", "体积光", "光斑", "阴影", "泛光", "光束", "反光", "反射",
           "自然光", "日光", "月光", "烛光", "霓虹光", "冷光", "暖光", "背光",
           "低调照明", "高调照明", "布光", "打光", "光线", "光源"],
    "材质": ["漆皮", "羊皮纸", "金箔", "丝绸", "丝绒", "混凝土", "磨砂", "抛光",
             "拉丝", "哑光", "亮面", "绒面", "铸铁", "陶", "陶瓷", "玻璃", "亚克力",
             "金属", "不锈钢", "黄铜", "木纹", "皮革", "帆布", "蕾丝", "薄纱",
             "半透明", "透明", "纸艺", "手绘", "水彩", "铅笔", "油画", "版画"],
    "摄影": ["浅景深", "深景深", "广角", "微距", "移轴", "胶片颗粒", "长曝",
             "高对比", "低对比", "低饱和", "去饱和", "高饱和", "过曝", "欠曝",
             "传感器噪点", "镜头光晕", "色差", "暗部", "景深", "焦点"],
    "构图": ["居中构图", "三分法", "对角线", "对称构图", "俯视", "仰视", "平视",
             "等轴", "留白", "特写", "半身", "全身", "远景", "近景", "中景",
             "画幅", "竖版", "横版", "网格", "九宫格"],
    "质感": ["真实感", "写实", "照片级", "电影感", "质感", "颗粒感", "细节丰富",
             "高清", "超精细", "锐利", "柔和", "虚化", "模糊", "清晰"],
}


def load_corpus_text():
    """把语料里所有描述文本拼起来，用于覆盖对比"""
    parts = []
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            parts.append(d.get("description", ""))
            parts.append(d.get("text_semantic", ""))
            parts.append(" ".join(d.get("style_tags") or []))
            parts.append(" ".join(d.get("kw_zh") or []))
    return " ".join(parts)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(SPILL):
        print(f"源文件不存在: {SPILL}")
        return
    text = open(SPILL, encoding="utf-8", errors="ignore").read()
    print(f"源文本 {len(text)} 字符")

    # 存档（带许可标注）
    header = (
        "# 外部提示词库原文记录（分析用，不入训练集）\n"
        "# 来源：水仙的AI提示词 https://github.com/BaYue-SYJ/shuixian-prompts\n"
        "# 许可：署名使用协议（可学习/fork/非商业转载，须保留出处并链接回仓库）\n"
        "# 提示词原文版权归各自原作者；本文件仅作词频分析，不复制进我们语料。\n"
        "# 抓取时间：本次会话；内容为 data/prompts.part1.json 的公开数据\n\n"
    )
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        f.write(header + text)
    print(f"原文存档 -> {OUT_RAW}  ({os.path.getsize(OUT_RAW)/1024:.0f} KB)")

    corpus_text = load_corpus_text()
    print(f"我们语料文本 {len(corpus_text)} 字符\n")

    print("=" * 78)
    print(f"{'类别':<6} {'词':<10} {'外部频次':>8} {'我们语料':>8}  状态")
    print("=" * 78)
    report = {}
    for cat, words in CATS.items():
        report[cat] = []
        for w in words:
            n_ext = text.count(w)
            n_our = corpus_text.count(w)
            if n_ext == 0:
                continue
            status = "缺" if n_our == 0 else ("少" if n_our < n_ext / 20 else "有")
            report[cat].append({"word": w, "ext": n_ext, "our": n_our, "status": status})
            print(f"{cat:<6} {w:<10} {n_ext:>8} {n_our:>8}  {status}")
    print("=" * 78)

    total = sum(len(v) for v in report.values())
    missing = [(w["word"], w["ext"], w["our"], c) for c, v in report.items()
               for w in v if w["status"] == "缺"]
    thin = [(w["word"], w["ext"], w["our"], c) for c, v in report.items()
            for w in v if w["status"] == "少"]
    print(f"\n共检查 {total} 个具体词")
    print(f"  我们完全没有 : {len(missing)}")
    print(f"  我们明显偏少 : {len(thin)}")
    print()
    print("=== 我们完全没有的词（按外部频次降序）===")
    for w, e, o, c in sorted(missing, key=lambda x: -x[1]):
        print(f"  [{c}] {w:<10} 外部出现 {e} 次")
    print()
    print("=== 我们明显偏少的词 ===")
    for w, e, o, c in sorted(thin, key=lambda x: -x[1])[:20]:
        print(f"  [{c}] {w:<10} 外部 {e} / 我们 {o}")

    with open(OUT_VOCAB, "w", encoding="utf-8") as f:
        json.dump({"source": "shuixian-prompts part1",
                   "license": "署名使用协议，须保留出处",
                   "report": report, "missing": len(missing),
                   "thin": len(thin)}, f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT_VOCAB}")
    print("\n### EXT_VOCAB_DONE")


if __name__ == "__main__":
    main()
