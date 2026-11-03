"""
自动学习闭环：候选 → 量 → 变好才留，变差自动回滚

为什么要这个
------------
人补条目已经证明有天花板（见 HANDOFF「不要再试」那张表）。
但"自己学"必须先解决一件事：**它自己怎么知道学到了没有？**

答案：用**留出集**当裁判。
    · 开发集 60 条：允许被用来生成候选
    · 留出集 60 条：只用来判分，绝不允许进入候选

流程
----
    1. 量基线（留出集：风格空 / 节拍通用 / 声音通用 / 风险通用 + 硬错误）
    2. 把候选文档追加进语料（生成新版本文件）
    3. 再量一次
    4. 留出集指标变好（且硬错误不增加）→ 保留；否则把语料恢复原样

用法
----
    python src/auto_learn.py 候选.jsonl

候选格式：每行一个 JSON，字段同语料文档（director_zh / kw_zh / description）。
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = r"F:\llm"
RAW = os.path.join(ROOT, "data", "raw")
NODE = os.path.join(ROOT, "comfyui", "local_style_hint.py")
WF = os.path.join(ROOT, "comfyui", "workflow_style_hint.json")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")


def corpus_version():
    s = open(NODE, encoding="utf-8").read()
    m = re.search(r"corpus_v(\d+)\.jsonl", s)
    return int(m.group(1)) if m else None


def switch_corpus(ver):
    s = open(NODE, encoding="utf-8").read()
    s = re.sub(r"corpus_v\d+\.jsonl", f"corpus_v{ver}.jsonl", s)
    open(NODE, "w", encoding="utf-8").write(s)
    w = json.load(open(WF, encoding="utf-8"))
    wv = w["nodes"][0]["widgets_values"]
    for i, v in enumerate(wv):
        if isinstance(v, str):
            wv[i] = re.sub(r"corpus_v\d+\.jsonl", f"corpus_v{ver}.jsonl", v)
    json.dump(w, open(WF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def smoke_ok():
    """跑 smoke，返回通过条数（0-3）。这是第二道闸：
    只量 bulk 会漏掉"这个指标变好、那个指标变坏"的情况（实测踩过）。"""
    out = subprocess.run([PY, os.path.join(ROOT, "src", "smoke_test.py")],
                         capture_output=True, text=True, encoding="utf-8",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    txt = (out.stdout or "") + (out.stderr or "")
    m = re.search(r"===\s*(\d+)\s*/\s*(\d+)\s*通过", txt)
    return int(m.group(1)) if m else 0


def measure():
    """跑批量评测，只取数字"""
    out = subprocess.run([PY, os.path.join(ROOT, "src", "e2e_bulk.py")],
                         capture_output=True, text=True, encoding="utf-8",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    txt = (out.stdout or "") + (out.stderr or "")
    m = {}
    for key, pat in (("hard", r"硬错误\s+(\d+)"),
                     ("heldout_style", r"heldout\s+n=\s*\d+\s+硬错误\s+\d+\s+风格空\s+(\d+)%")):
        mm = re.search(pat, txt)
        if mm:
            m[key] = int(mm.group(1))
    if not m:
        # 量不出来要说出原因，否则"回滚"会掩盖真正的崩溃
        tail = "\n".join(txt.strip().splitlines()[-6:])
        print("     ✗ 量失败，尾部输出：")
        for line in tail.splitlines():
            print("       " + line[:96])
    return m


def main(cand_path):
    cur = corpus_version()
    print(f"  当前语料 corpus_v{cur}")

    print("  ① 量基线…")
    base = measure()
    base["smoke"] = smoke_ok()
    print(f"     {base}")
    if not base:
        print("  ✗ 量不出来，中止")
        return

    cands = [json.loads(l) for l in open(cand_path, encoding="utf-8") if l.strip()]
    print(f"  ② 追加 {len(cands)} 条候选 → corpus_v{cur + 1}")

    src = os.path.join(RAW, f"corpus_v{cur}.jsonl")
    dst = os.path.join(RAW, f"corpus_v{cur + 1}.jsonl")
    rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    for c in cands:
        c.setdefault("doc_id", f"a{len(rows)+1:04d}")
        c.setdefault("domain", "prompt_video")
        c.setdefault("lang", "zh")
        c.setdefault("facet", "风格")
        c.setdefault("params", {"aspect_ratio": "16:9", "duration": 6})
        c.setdefault("text_semantic", (c.get("description", "") + "、" +
                                       "、".join(c.get("kw_zh") or [])))
        rows.append(c)
    with open(dst, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    switch_corpus(cur + 1)

    print("  ③ 再量…")
    after = measure()
    after["smoke"] = smoke_ok()
    print(f"     {after}")

    ok = (after.get("hard", 99) <= base.get("hard", 99)
          and after.get("heldout_style", 999) < base.get("heldout_style", 0)
          # smoke 不许比基线差：一个指标变好、另一个变坏，不算变好
          and after.get("smoke", 0) >= base.get("smoke", 0))
    if ok:
        print("  ✅ 留出集变好，保留")
    else:
        print("  ↩ 没变好（或硬错误变多），回滚")
        switch_corpus(cur)
        os.remove(dst)
        print("     已恢复 corpus_v%d" % cur)


if __name__ == "__main__":
    main(sys.argv[1])
