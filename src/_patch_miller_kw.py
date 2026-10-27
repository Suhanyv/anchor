"""
给乔治·米勒补关键词：赛车 / 竞速 / 沙地

为什么
------
实测「两辆拉力赛车在沙地赛场上竞速」：他 0.2804，差 0.02 到弱匹配线，
于是工具说"库中没有可靠匹配"。可他的文档写的正是
"a vehicle chase through an orange desert wasteland"——**车辆追逐**。

问题在关键词：他的 kw 是 橙青/追逐/沙漠，**没有一个字能对上"赛车""竞速"**。
补的是他真实拍过的东西，不是硬凑。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SRC = os.path.join(RAW, "corpus_v21.jsonl")
OUT = os.path.join(RAW, "corpus_v25.jsonl")

ADD = ["赛车", "拉力", "竞速", "车", "沙地", "扬尘"]

rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
n = 0
for r in rows:
    if r.get("director_zh") != "乔治·米勒":
        continue
    # 只给"橙青/追逐/沙漠"那一组（车辆追逐）加；粉彩漫画那组不动
    if "追逐" not in (r.get("kw_zh") or []):
        continue
    kw = list(r.get("kw_zh") or [])
    for w in ADD:
        if w not in kw:
            kw.append(w)
    r["kw_zh"] = kw
    r["text_semantic"] = f"{r.get('description', '')}，{r.get('director_zh')}，{'、'.join(kw)}"
    n += 1

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"  乔治·米勒 车辆追逐那一组：改了 {n} 条")
print("\n### MILLER_KW_DONE")
