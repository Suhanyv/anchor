"""
症状 → 手段：查询里说了毛病，就把"治它的手段"找出来，而不是把毛病本身写进提示词

为什么
------
用户指出：它不该想「打击感不够」，该想「什么能增加打击感」——比如蓄力挥出。
「打击感不够」是一句诊断，画面里写不进去；写进去的是
「剑停在最高点一瞬」「接触停两帧」「脚往后滑」。

做法
----
1. 读 data/raw/symptoms.json（症状 → means 的中文短语）
2. 查询里出现症状词，就把 means 里的短语收集起来
3. 整段格式在末尾加一行【技法】，只放这些手段，不放症状
4. 没有症状词就不加这一行
"""
import ast
import json
import os
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_symptom_means" not in s:
    fn = '''_SYMPTOMS = None


def _load_symptoms():
    global _SYMPTOMS
    if _SYMPTOMS is not None:
        return _SYMPTOMS
    try:
        p = os.path.join(ROOT, "data/raw/symptoms.json")
        with open(p, encoding="utf-8") as f:
            _SYMPTOMS = json.load(f).get("症状", {})
    except Exception:
        _SYMPTOMS = {}
    return _SYMPTOMS


def _symptom_means(q):
    """查询里说了哪些症状，对应要用的手段是什么。

    返回 (命中的症状列表, 手段短语列表)。
    只返回手段——症状是诊断，不进提示词。
    """
    t = q or ""
    syn = _load_symptoms()
    hit, means, seen = [], [], set()
    _, name_to_craft = (None, None)
    # 症状名长的优先匹配（"镜头不连贯" 先于 "不连贯"）
    for name in sorted(syn, key=len, reverse=True):
        if name and name in t:
            hit.append(name)
            for m in (syn[name].get("means") or []):
                zh = str(m.get("zh") or "").strip()
                if zh and zh not in seen:
                    seen.add(zh)
                    means.append(zh)
    return hit, means


'''
    anchor = "def _dur_from_query(query):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 在整段格式里追加技法行
old = '''    seg.append(cine)'''
new = '''    seg.append(cine)
    # 症状 -> 手段：把"怎么治"写进去，不写"有什么毛病"
    _hit, _means = _symptom_means(query)
    if _means:
        seg.append("技法：" + "；".join(_means[:4]) + "。")'''
if old in s:
    s = s.replace(old, new, 1)
else:
    raise SystemExit("整段格式里没找到 cine 那一行")

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _symptom_means:", hasattr(N, "_symptom_means"))
for q in ("打击感不够，一个骑士和一群人交战",
          "镜头不连贯",
          "一个骑士和一群人交战"):
    h, m = N._symptom_means(q)
    print(f"  {q[:18]:<20} 症状={h} 手段{len(m)}条")
