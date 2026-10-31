"""补角度表的同义词：鸟瞰/俯瞰/顶拍"""
import json

P = r"F:\llm\data\raw\camera_angle_ref.json"
d = json.load(open(P, encoding="utf-8"))

ADD = {
    "俯拍": ["高机位", "从上往下"],
    "垂直俯拍": ["鸟瞰", "俯瞰", "顶拍", "航拍俯视"],
    "低角度": ["仰视", "从下往上"],
    "地面视角": ["贴地视角", "地面机位"],
}
for name, words in ADD.items():
    if name not in d:
        continue
    kw = list(d[name].get("kw") or [])
    for w in words:
        if w not in kw:
            kw.append(w)
    d[name]["kw"] = kw

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

import sys
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
for q in ("鸟瞰，雪原上一个人", "俯瞰一座城", "仰视他"):
    r = N._match_ref("camera_angle_ref.json", q, [])
    print(f"  {q[:14]:<16} -> {(r or {}).get('zh','(未命中)')[:26]}")
