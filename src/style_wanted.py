"""
列出"人真的这么说、而库没覆盖"的句子

用法
----
    python src/style_wanted.py           # 全部
    python src/style_wanted.py 20        # 只看最近 20 条

数据来自 `_record_style_gap`：风格不可信时自动记一条（去重），
所以这份清单会随着真实使用自己长出来。
"""
import json
import os
import sys

P = r"F:\llm\data\raw\style_wanted.jsonl"


def main(limit=None):
    if not os.path.exists(P):
        print("  还没有记录。用起来之后会自动出现。")
        return
    rows = []
    for line in open(P, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if limit:
        rows = rows[-int(limit):]
    print(f"\n  共 {len(rows)} 条（风格没匹配上的真实句子）\n")
    for r in rows:
        print("    " + r.get("query", "")[:40])
    print("\n  补法：给每一条写一份语料文档，关键词用**部件**（名词/动作），不是整句。")
    print("\n### STYLE_WANTED_DONE")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
