"""
场景槽位改为「单独取最优」，不再只看题材 top1

问题
----
初版只检查题材通道 top1 是不是 scene。于是"下雪的庭院"这种查询里，
top1 是「雪中庭院」（object，该当主体用），而某个场景条目即使排第二也被忽略。

改法
----
在 `_rank` 里对 **scene 子集**单独做一次 argmax，把结果存进 `subj["scene_best"]`。
这样不改 `_rank` 的返回元组（6 元组），所有调用方都不受影响。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ---- 1) _rank 里加：场景子集单独取最优 ----
anchor = """    # ---- 分级去偏（必须在算风格分之前：需要先知道风格 top1 才能判题材是否命中）----"""
assert anchor in s, "去偏锚点变了"
add = '''    # ---- 场景子集单独取最优（不限于 top1，也不改返回元组）----
    if (subj is not None and st.get("subj_emb") is not None
            and len(st.get("subjects") or [])):
        try:
            _sidx = [(i, r) for i, r in enumerate(st["subjects"])
                     if r.get("type") == "scene"]
            if _sidx:
                _ii = [i for i, _ in _sidx]
                _sub = ssims[_ii]
                _kk = int(_sub.argmax())
                _row = st["subjects"][_ii[_kk]]
                subj["scene_best"] = {
                    "score": float(_sub[_kk]),
                    "phrase": _row["phrase"],
                    "zh": _row.get("subject_zh", ""),
                }
        except Exception:
            pass

'''
s = s.replace(anchor, add + anchor, 1)

# ---- 2) _core 里优先用 scene_best ----
old = '''    subj_is_scene = bool(subj and subj.get("type") == "scene"
                         and float(subj.get("score") or 0) >= SCENE_FLOOR)
    scene_phrase = subj["phrase"] if subj_is_scene else ""'''
new = '''    # 场景：优先用 scene_best（场景子集的最优），退而用 top1（若它本身就是场景）
    scene_phrase = ""
    subj_is_scene = False
    if subj:
        sb = subj.get("scene_best")
        if sb and float(sb.get("score") or 0) >= SCENE_FLOOR:
            scene_phrase = sb["phrase"]
        elif (subj.get("type") == "scene"
              and float(subj.get("score") or 0) >= SCENE_FLOOR):
            scene_phrase = subj["phrase"]
            subj_is_scene = True'''
assert old in s, "_core 场景判定段变了"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  语法 OK，参数", len(N.LocalStyleHint.INPUT_TYPES()["required"]))
print("  SCENE_FLOOR =", N.SCENE_FLOOR)
