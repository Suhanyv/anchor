"""把待挑的候选完整打出来（不截断）"""
import json
import os

ROOT = r"F:\llm"
P = os.path.join(ROOT, "data/raw/taste_pending.json")
d = json.load(open(P, encoding="utf-8"))

cur = None
for c in d["cands"]:
    if c.get("req") != cur:
        cur = c.get("req")
        print(f"\n{'='*66}\n【{c['key'][0]}】{cur}\n{'='*66}")
    k = c["knobs"]
    print(f"\n---- {c['key']} · {c['name']} ----")
    print(f"风格 {k['style']} {k['score']}   光 {k['light'] or '（无）'}   "
          f"运镜 {k['motion'] or '（无）'}   维 {c['m']['dims']}/6  洞 {c['m']['holes']}")
    print()
    print(c["out"])
print("\n### PENDING_DUMP_DONE")
