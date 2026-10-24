"""
外部提示词词表 vs 我们语料覆盖（修正版）

修正了什么
----------
第一版直接拿中文词去 count 我们语料 —— **结构性错误**：
我们的 doc 是英文（"a scratched steel pauldron catching a thin hard rim light"），
中文词当然 0 次。那不是"缺概念"，是"缺中文词面"。

正确做法：把每个中文词映射到英文对应词，再数我们的英文语料。
这才是"这个概念我们有没有"。

数据来源
--------
水仙的AI提示词 https://github.com/BaYue-SYJ/shuixian-prompts
许可：署名使用协议（须保留出处并链接回仓库）；原文版权归原作者。
本脚本只做词频对照，不复制原文。
"""
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "external", "shuixian_part1_README.txt")
OUT = os.path.join(ROOT, "bench", "external_vocab_v2.json")
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v11.jsonl")

# 中文词 -> [英文对应表达]（用于在我们的英文语料里查覆盖）
PAIRS = {
    # ---- 光 ----
    "侧光": ["side light", "side-lit", "rim light", "hard rim"],
    "柔光": ["soft light", "soft light source"],
    "漫射": ["diffuse", "diffused", "scattered light"],
    "高光": ["highlight", "highlights", "specular"],
    "暗角": ["vignette", "corner falloff"],
    "轮廓光": ["rim light", "backlight", "edge light", "backlit"],
    "光斑": ["bokeh", "light spots", "flare"],
    "反射": ["reflection", "reflecting", "reflected"],
    "反光": ["reflection", "glint", "sheen"],
    "背光": ["backlight", "backlit"],
    "光线": ["light", "shaft of light", "beam"],
    "光柱": ["shaft", "beam of light"],
    # ---- 材质 ----
    "漆皮": ["patent leather", "lacquered", "glossy leather"],
    "羊皮纸": ["parchment", "vellum"],
    "金箔": ["gold leaf", "gilt", "gold foil"],
    "丝绸": ["silk", "silken"],
    "丝绒": ["velvet"],
    "抛光": ["polished", "burnished"],
    "拉丝": ["brushed metal", "brushed steel"],
    "哑光": ["matte", "matt"],
    "亮面": ["glossy", "polished", "shiny"],
    "陶瓷": ["ceramic", "porcelain"],
    "玻璃": ["glass", "glazing"],
    "不锈钢": ["stainless steel", "steel"],
    "帆布": ["canvas", "duck cloth"],
    "蕾丝": ["lace"],
    "薄纱": ["gauze", "tulle", "sheer fabric"],
    "半透明": ["translucent", "semi-transparent"],
    "透明": ["transparent", "clear"],
    "纸艺": ["paper craft", "paper sculpture", "cut paper"],
    "水彩": ["watercolour", "watercolor", "wash"],
    "铅笔": ["pencil", "graphite"],
    "金属": ["metal", "metallic", "steel"],
    "混凝土": ["concrete", "brutalist"],
    "锈": ["rust", "rusted"],
    "划痕": ["scratched", "scratches", "scuff"],
    # ---- 摄影 ----
    "浅景深": ["shallow depth of field", "shallow focus", "shallow dof"],
    "景深": ["depth of field", "dof", "focus"],
    "微距": ["macro", "close focus"],
    "胶片颗粒": ["film grain", "grain"],
    "颗粒感": ["grain", "granular"],
    "低对比": ["low contrast", "flat light"],
    "高对比": ["high contrast", "hard contrast"],
    "低饱和": ["desaturated", "muted", "low saturation"],
    "去饱和": ["desaturated", "muted colour"],
    "过曝": ["overexposed", "blown highlights"],
    "镜头光晕": ["lens flare", "flare"],
    "传感器噪点": ["sensor noise", "noise"],
    "色差": ["chromatic aberration"],
    # ---- 构图 ----
    "居中构图": ["centred", "centered", "symmetrical composition", "dead centre"],
    "对角线": ["diagonal"],
    "对称构图": ["symmetrical", "symmetry"],
    "俯视": ["overhead", "top-down", "seen from above", "bird's eye"],
    "仰视": ["from below", "low angle", "worm's eye"],
    "平视": ["eye level", "at eye level"],
    "等轴": ["isometric"],
    "半身": ["half body", "waist up", "from the waist"],
    "全身": ["full body", "head to toe"],
    "近景": ["close shot", "close-up", "medium close"],
    "中景": ["medium shot", "mid shot"],
    "竖版": ["vertical", "portrait format"],
    "横版": ["horizontal", "landscape format"],
    "网格": ["grid"],
    "两分": ["split frame", "two panels"],
    # ---- 质感 ----
    "真实感": ["photoreal", "photorealistic", "lifelike"],
    "照片级": ["photorealistic", "photo-real"],
    "电影感": ["cinematic"],
    "质感": ["texture", "material quality", "tactile"],
    "细节丰富": ["fine detail", "detailed"],
    "虚化": ["blurred", "out of focus", "defocused"],
    "柔和": ["soft", "gentle"],
    "锐利": ["sharp", "crisp"],
}


def load_corpus_text():
    parts = []
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            parts.append(d.get("description", ""))
            parts.append(d.get("text_semantic", ""))
            parts.append(" ".join(d.get("style_tags") or []))
    return " ".join(parts).lower()


def main():
    if not os.path.exists(RAW):
        print(f"缺源文件 {RAW}")
        return
    ext = open(RAW, encoding="utf-8", errors="ignore").read()
    corpus = load_corpus_text()
    print(f"外部提示词 {len(ext)} 字符 / 我们语料 {len(corpus)} 字符\n")

    rows = []
    for zh, ens in PAIRS.items():
        n_ext = ext.count(zh)
        if n_ext == 0:
            continue
        n_our = sum(corpus.count(e.lower()) for e in ens)
        # 外部每 10 万字符里出现几次，折算成"我们该有多少"
        expect = n_ext / len(ext) * len(corpus)
        if n_our == 0:
            status = "缺"
        elif n_our < expect * 0.25:
            status = "少"
        else:
            status = "有"
        rows.append({"zh": zh, "en": ens, "ext": n_ext, "our": n_our,
                     "expect": round(expect, 2), "status": status})
        print(f"  {zh:<8} 外部{n_ext:>4}次  我们{n_our:>4}次  "
              f"按比例应有{expect:>6.1f}  {status}   ({ens[0]})")

    miss = [r for r in rows if r["status"] == "缺"]
    thin = [r for r in rows if r["status"] == "少"]
    print("\n" + "=" * 70)
    print(f"检查 {len(rows)} 个概念：缺 {len(miss)}  少 {len(thin)}  "
          f"有 {len(rows)-len(miss)-len(thin)}")
    print("=" * 70)
    if miss:
        print("\n=== 完全没有的概念（按外部频次）===")
        for r in sorted(miss, key=lambda x: -x["ext"]):
            print(f"  {r['zh']:<8} 外部{r['ext']:>3}次  我们的英文里查无  {r['en']}")
    if thin:
        print("\n=== 明显偏少的概念 ===")
        for r in sorted(thin, key=lambda x: -x["ext"])[:15]:
            print(f"  {r['zh']:<8} 外部{r['ext']:>3}次  我们{r['our']:>3}次（应约{r['expect']:.1f}）")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": "shuixian-prompts part1",
                   "license": "署名使用协议，须保留出处",
                   "rows": rows,
                   "missing": len(miss), "thin": len(thin)}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nreport -> {OUT}")
    print("\n### EXT_VOCAB_V2_DONE")


if __name__ == "__main__":
    main()
