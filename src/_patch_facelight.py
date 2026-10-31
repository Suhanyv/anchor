"""接脸部光型表：点名就写一句「光位：…」"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

old1 = '        "comp_zh": ((_match_ref("composition_ref.json", query, kw) or {})\n                    .get("zh", "")),'
new1 = ('        "comp_zh": ((_match_ref("composition_ref.json", query, kw) or {})\n'
        '                    .get("zh", "")),\n'
        '        # 脸部光型：同一支蜡烛从侧面打和从底下打，是两场戏\n'
        '        "facelight_zh": ((_match_ref("face_light_ref.json", query, kw) or {})\n'
        '                         .get("zh", "")),')
assert old1 in s and '"facelight_zh"' not in s, "core 插入点异常"
s = s.replace(old1, new1, 1)

old2 = '''    _comp = c.get("comp_zh") or ""
    if _comp:
        seg.append(f"{_comp}。")'''
new2 = '''    _comp = c.get("comp_zh") or ""
    if _comp:
        seg.append(f"{_comp}。")
    _fl = c.get("facelight_zh") or ""
    if _fl:
        seg.append(f"{_fl}。")'''
assert old2 in s, "正文插入点没匹配"
s = s.replace(old2, new2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已接脸部光型", len(N._load_ref("face_light_ref.json")), "条")
for q in ("伦勃朗光，一个人坐在桌前", "分脸光，他把脸转过来", "一个女孩跑"):
    r = N._match_ref("face_light_ref.json", q, [])
    print(f"  {q[:16]:<18} -> {(r or {}).get('zh','(未命中)')[:34]}")
