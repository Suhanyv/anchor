"""查现有题材里有没有武士/剑客/芒草这类条目"""
import json
import os

ROOT = r"F:\llm"
rows = [json.loads(l) for l in
        open(os.path.join(ROOT, "data/raw/subjects_v14.jsonl"), encoding="utf-8")
        if l.strip()]
names = [r.get("subject_zh") or "" for r in rows]
print(f"  题材 {len(rows)} 行，实体 {len(set(names))} 个")
for w in ("武士", "剑客", "浪人", "武将", "侠客", "芒草", "狗尾巴草", "雪"):
    hit = sorted({n for n in names if w in n})
    print(f"  含「{w}」: {hit[:5] if hit else '无'}")

print("\n  全部人物/器物实体：")
uniq = [n for n in dict.fromkeys(names) if n]
for i in range(0, len(uniq), 6):
    print("    " + "、".join(uniq[i:i + 6]))

print("\n### CHECK_DONE")
