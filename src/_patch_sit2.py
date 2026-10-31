"""
把节拍表按优先级重排，并删掉 _priority 字段

为什么：`_load_ref` 会把下划线开头的键当元数据过滤掉，
所以 `_priority` 从来没被读到过（实测打印出来是 None）。
表本身的键顺序就是匹配顺序，排好就行。
"""
import json
import sys

BEAT = r"F:\llm\data\raw\beat_ref.json"
d = json.load(open(BEAT, encoding="utf-8"))

ORDER = ["跑", "走", "打", "对峙", "空镜", "变", "看", "拿",
         "坐·桌椅", "坐", "拥抱", "开门", "等", "喊"]

meta = {k: v for k, v in d.items() if k.startswith("_") and k != "_priority"}
body = {k: v for k, v in d.items() if not k.startswith("_")}

# 先按 ORDER 排，剩下的（以后新加的）接在后面
ordered = {}
for k in ORDER:
    if k in body:
        ordered[k] = body.pop(k)
for k, v in body.items():
    ordered[k] = v

out = dict(meta)
out.update(ordered)
json.dump(out, open(BEAT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
rows = N._load_ref("beat_ref.json")
print("  表顺序:", " > ".join(rows.keys()))
for q in ("伦勃朗光，一个道士坐在桌前写字", "一个男孩坐在地上看星空",
          "一个人坐在椅子上", "雨里，一个女孩抱着纸箱跑"):
    mid, _end = N._scene_beats(q)
    print(f"  {q[:20]:<22} {mid[:32]}")
