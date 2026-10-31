"""
把「媒介式风格 → 画面材质」接进 _core

实测：提示词写「文人水墨：水墨、留白、笔触」，生成出来是写实电影感。
风格名对视频模型几乎无效——它看的是「画面是什么做的」。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_entry_medium" not in s:
    fn = '''def _entry_medium(item):
    """媒介式风格（水墨/皮影/浮世绘…）-> 一句「画面是什么做的」。

    实测：提示词写「文人水墨：水墨、留白、笔触」，生成出来是写实电影感。
    风格名像调色参考，不像画面材质；视频模型看的是后者。
    """
    rows = _load_ref("medium_ref.json")
    if not rows or not item:
        return "", ""
    names = [str(item.get("director_zh") or ""), str(item.get("director") or "")]
    names += [str(x) for x in (item.get("kw_zh") or [])]
    for name, row in rows.items():
        for nm in names:
            if nm and name in nm:
                return row.get("zh") or "", row.get("en") or ""
    return "", ""


'''
    anchor = "def _scene_risks(query, limit=3):"
    assert anchor in s, "插入点没找到"
    s = s.replace(anchor, fn + anchor, 1)

old = '        "risks": _scene_risks(query),'
new = ('        "risks": _scene_risks(query),\n'
       '        # 媒介式风格的「画面材质」：视频模型只吃这一句\n'
       '        "medium_zh": _entry_medium(item)[0],\n'
       '        "medium": _entry_medium(item)[1],')
if old in s and '"medium_zh"' not in s:
    s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _entry_medium:", hasattr(N, "_entry_medium"))
print("  表里", len(N._load_ref("medium_ref.json")), "条")
