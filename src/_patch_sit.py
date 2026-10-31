"""
把「坐」拆成两种：坐在椅子上 / 坐在地上

实测：「一个道士坐在桌前写字」给了"重心换到另一侧，手放在膝上或撑住地面"——
那是坐草地上的动作，不是坐桌前写字。原来的"坐"是从"男孩坐草地上"学来的。
"""
import json
import sys

BEAT = r"F:\llm\data\raw\beat_ref.json"
d = json.load(open(BEAT, encoding="utf-8"))

# 坐在椅子上：桌前/桌边/椅子/伏案/写字这类语境
d["坐·桌椅"] = {
    "kw": ["桌前", "桌边", "椅子", "伏案", "写字", "办公", "书案"],
    "mid": "上身轻微前倾，手在桌面上或压着纸，肩放松一点",
    "end": "停在这个姿势上，只有手还在动",
}
# 坐在地上：原来那条，收窄成真的在地上
d["坐"] = {
    "kw": ["坐", "坐下", "坐着"],
    "mid": "重心换到另一侧，手放在膝上或撑住地面",
    "end": "画面停在这个姿势上，不再动",
}

# 更具体的排在前面
pri = [n for n in d.get("_priority", []) if n != "坐"]
i = pri.index("看") if "看" in pri else len(pri)
pri.insert(i, "坐·桌椅")
pri.append("坐")
d["_priority"] = pri

json.dump(d, open(BEAT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402
print("  优先级:", " > ".join(pri[:8]), "...")
for q in ("伦勃朗光，一个道士坐在桌前写字", "一个男孩坐在地上看星空",
          "一个人坐在椅子上"):
    mid, end = N._scene_beats(q)
    print(f"  {q[:20]:<22} {mid[:30]}")
