"""把 output/shots.md 解析成 shots.json（给脚本用）"""
import json
import re

MD = r"F:\llm\output\shots.md"
JS = r"F:\llm\output\shots.json"

t = open(MD, encoding="utf-8").read()
# 用三反引号围栏切块，避免在 shell 里转义
fence = chr(96) * 3
blocks = re.findall(r"## (.+?)\n\n" + fence + r"\n(.*?)\n" + fence, t, re.S)

rows = []
for title, text in blocks:
    m = re.search(r"(\d+)\s*秒", title)
    sec = int(m.group(1)) if m else 0
    style = text.split("：")[0].split("。")[0].strip()
    rows.append({
        "title": title.strip(),
        "seconds": sec,
        "style": style,
        "prompt": text.strip(),
    })

out = {
    "platform": "即梦 Seedance 2.5",
    "platform_limits": {"min": 4, "max": 30},
    "total_shots": len(rows),
    "total_seconds": sum(r["seconds"] for r in rows),
    "shots": rows,
}
with open(JS, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"  读出 {len(rows)} 镜，合计 {out['total_seconds']} 秒")
for r in rows:
    over = "" if 4 <= r["seconds"] <= 30 else "  ⚠️ 超出平台范围"
    print(f"    {r['title'][:24]:<26} {r['seconds']:>2}s  {r['style']}{over}")
print("\n### SHOTS_JSON_DONE")
