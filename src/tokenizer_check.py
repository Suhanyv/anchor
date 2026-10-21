"""
Tokenizer 切分质量检查 —— 决定「提示词参数是否该拆出语义空间」。

要回答的具体问题：
  1. `--ar`、`16:9`、`:1.3` 这类参数会不会被切碎？
  2. 中文/日文/韩文/德文的 token 效率（fertility）如何？
  3. 德语复合词会被切几刀？

用法: python tokenizer_check.py [--model NAME ...]
"""
import argparse
import json

from transformers import AutoTokenizer

MODELS = ["intfloat/multilingual-e5-small"]

CASES = {
    "EN prompt + params": 'masterpiece, best quality, (detailed eyes:1.3), cinematic lighting, neon rain, cyberpunk --ar 16:9 --v 6 --style raw',
    "EN prompt plain": 'masterpiece, best quality, detailed eyes, cinematic lighting, neon rain, cyberpunk',
    "ZH prompt": '杰作，最佳质量，精致的眼睛，电影级光照，霓虹雨夜，赛博朋克风格',
    "JA text": '手紙を書くためにペンを買いました',
    "KO text": '안녕하세요, 반갑습니다. 오늘 날씨가 좋네요.',
    "DE compound": 'Donaudampfschifffahrtsgesellschaft',
    "DE sentence": 'Die Donaudampfschifffahrtsgesellschaft hat ihren Sitz in Wien.',
    "Code": 'def debounce(fn, delay):\n    timer = None\n    def wrapper(*a, **kw): ...',
    "ZH query": 'React 里怎么做输入框防抖？',
}

# 关键词：这些应当尽量保持为独立 token，否则语义空间会被语法噪声污染
PARAM_TOKENS = ["--ar", "16:9", "--v", "--style", "1.3"]


def cjk_ratio(s):
    if not s:
        return 0.0
    cjk = sum(1 for c in s if "\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" or "\uac00" <= c <= "\ud7af")
    return cjk / len(s)


def analyze(tok_name):
    print("=" * 78)
    print(f"tokenizer: {tok_name}")
    print("=" * 78)
    tok = AutoTokenizer.from_pretrained(tok_name, trust_remote_code=True)
    print(f"vocab size: {tok.vocab_size:,}   model_max_length: {tok.model_max_length:,}\n")

    rows = []
    for label, text in CASES.items():
        ids = tok.encode(text, add_special_tokens=False)
        toks = tok.convert_ids_to_tokens(ids)
        chars = len(text.replace(" ", ""))
        fert = len(ids) / chars if chars else 0
        rows.append((label, len(ids), chars, fert))
        print(f"[{label}]  {len(ids)} tokens / {chars} chars  fertility={fert:.3f}")
        shown = toks[:40]
        print("   " + " | ".join(shown) + (" ..." if len(toks) > 40 else ""))
        print()

    # 参数 token 是否被切碎
    print("-" * 78)
    print("参数 token 完整性检查（提示词域最关键）")
    print("-" * 78)
    prompt_text = CASES["EN prompt + params"]
    ids = tok.encode(prompt_text, add_special_tokens=False)
    toks = tok.convert_ids_to_tokens(ids)
    for kw in PARAM_TOKENS:
        # 找包含该关键词的 token
        hit = [t for t in toks if kw.replace(" ", "") in t.replace(" ", "") or t.strip("Ġ▁") == kw]
        exact = kw in [t.replace("Ġ", "").replace("▁", "") for t in toks]
        status = "整块保留" if exact else ("被切碎/合并" if hit else "未找到")
        print(f"  {kw:<10} {status:<12} 命中 token: {hit[:6]}")

    print()
    print("-" * 78)
    print("多语 token 效率（越低越好；中文一般 1 token ≈ 1~1.5 汉字）")
    print("-" * 78)
    print(f"  {'case':<22} {'tokens':>7} {'chars':>7} {'fertility':>10}")
    for label, n, c, f in sorted(rows, key=lambda x: -x[3]):
        print(f"  {label:<22} {n:>7} {c:>7} {f:>10.3f}")
    print()

    return {"tokenizer": tok_name, "vocab": tok.vocab_size,
            "rows": [{"case": l, "tokens": n, "chars": c, "fertility": round(f, 4)} for l, n, c, f in rows]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", nargs="*", default=MODELS)
    ap.add_argument("--out", default=r"F:\llm\bench\tokenizer_report.json")
    a = ap.parse_args()

    report = []
    for m in a.model:
        try:
            report.append(analyze(m))
        except Exception as e:  # noqa: BLE001
            print(f"!! {m} failed: {e}\n")

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"saved -> {a.out}")
    print("\n### TOKENIZER_CHECK_DONE")
