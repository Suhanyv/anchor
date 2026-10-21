"""
提示词参数/描述分离器。

依据：tokenizer 实测 —— 参数占 43% token（带参数 35 vs 不带 20），
      且 --ar 被切成 `▁--`+`ar`、16:9 被切成 `▁16`+`:`+`9`。
      参数是过滤条件，不是语义，绝不该进向量空间。

本脚本把
    "cinematic still, <description>, in the style of X, --ar 2.35:1 --v 6 --style raw"
拆成
    description: "cinematic still, <description>, in the style of X,"
    params:      {"ar": "2.35:1", "v": "6", "style": "raw"}

并量化：分离后 token 掉了多少（验证 43% 那组结论）。
"""
import json
import os
import re

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "corpus_v2.jsonl")
OUT = os.path.join(ROOT, "bench", "param_parse_report.json")

# --flag value  或  --flag（无值）
FLAG_RE = re.compile(r"--([a-zA-Z][\w-]*)(?:[ \t]+([^\s]+))?")
# (text:1.3)
WEIGHT_RE = re.compile(r"\(([^():]+):([0-9]*\.?[0-9]+)\)")

# 这些 flag 是布尔开关，不应吞掉后面的词
BOOLEAN_FLAGS = {"raw", "turbo", "niji", "stylize", "no"}


def parse(prompt):
    """返回 (clean_text, params, weights)"""
    params, weights = {}, {}
    s = prompt

    # 1. 权重 (word:1.3) -> 保留 word，记录权重
    for m in WEIGHT_RE.finditer(s):
        word, w = m.group(1).strip(), m.group(2)
        weights[word] = float(w)
    s = WEIGHT_RE.sub(lambda m: f" {m.group(1)} ", s)

    # 2. --flag value
    def sub_flag(m):
        key, val = m.group(1), m.group(2)
        params[key] = val if val is not None else True
        return " "

    s = FLAG_RE.sub(sub_flag, s)

    # 3. 清理多余标点/空格
    s = re.sub(r"[,;]+", ",", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" ,;:-")
    return s, params, weights


def main():
    with open(CORPUS, encoding="utf-8") as f:
        docs = [json.loads(l) for l in f if l.strip()]

    print(f"corpus: {len(docs)} docs\n")
    print("=" * 86)
    print(f"{'doc_id':<8} {'原长':>5} {'描述':>5} {'省%':>6}  params")
    print("=" * 86)

    tot_before = tot_after = 0
    flag_count = {}
    bad = []
    for d in docs[:8]:
        clean, params, weights = parse(d["prompt"])
        b, a2 = len(d["prompt"]), len(clean)
        tot_before += b
        tot_after += a2
        print(f"{d['doc_id']:<8} {b:>5} {a2:>5} {(b-a2)/b*100:>5.1f}%  {params}")

    for d in docs:
        clean, params, weights = parse(d["prompt"])
        b, a2 = len(d["prompt"]), len(clean)
        if len(docs[:8]) and d in docs[:8]:
            continue
        tot_before += 0  # 上面已计
        for k in params:
            flag_count[k] = flag_count.get(k, 0) + 1
        if not params:
            bad.append(d["doc_id"])

    # 全量统计（重算，避免上面重复）
    tot_before = tot_after = 0
    flag_count = {}
    weights_found = 0
    for d in docs:
        clean, params, weights = parse(d["prompt"])
        tot_before += len(d["prompt"])
        tot_after += len(clean)
        weights_found += len(weights)
        for k in params:
            flag_count[k] = flag_count.get(k, 0) + 1

    print("=" * 86)
    print(f"\n全量 {len(docs)} 条")
    print(f"  字符数   : {tot_before:,} -> {tot_after:,}   省 {(tot_before-tot_after)/tot_before*100:.1f}%")
    print(f"  抽取 flag: {flag_count}")
    print(f"  权重标记 : {weights_found} 个")
    if bad:
        print(f"  !! {len(bad)} 条未抽到任何参数（前 5: {bad[:5]}）")

    # 用真实 tokenizer 量化 token 节省（对照 43% 那组结论）
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
        tb = ta = 0
        for d in docs:
            clean, _, _ = parse(d["prompt"])
            tb += len(tok.encode(d["prompt"], add_special_tokens=False))
            ta += len(tok.encode(clean, add_special_tokens=False))
        print(f"\n  token（e5 分词器）: {tb:,} -> {ta:,}   省 {(tb-ta)/tb*100:.1f}%")
        print(f"  （此前实测：带参数 35 token vs 不带 20 token，即参数占 43%）")
    except Exception as e:  # noqa: BLE001
        print(f"\n  token 统计跳过: {e}")

    print("\n=== 分离效果样例 ===")
    for d in docs[:3]:
        clean, params, weights = parse(d["prompt"])
        print(f"\n[{d['doc_id']}]")
        print(f"  原文  : {d['prompt'][:120]}")
        print(f"  描述  : {clean[:120]}")
        print(f"  参数  : {params}   权重: {weights}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"docs": len(docs), "flags": flag_count,
                   "char_saving": (tot_before - tot_after) / tot_before}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nsaved -> {OUT}")
    print("\n### PARSE_DONE")


if __name__ == "__main__":
    main()
