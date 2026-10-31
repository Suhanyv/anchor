"""
接镜头类型表：查询点名就用，提案分镜按拍次挑

来源：实测那条水墨雨天视频里，真正成立的是「背面跟拍」和「脚下特写」两个镜头，
而提示词里根本没写它们。既然有效，就该由我们主动指定，而不是碰运气。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_match_shot" not in s:
    fn = '''def _match_shot(query):
    """查询点名的镜头类型 -> 词条 dict 或 None。"""
    rows = _load_ref("shot_ref.json")
    q = query or ""
    for name, row in rows.items():
        for k in (row.get("kw") or [name]):
            if k and k in q:
                return row
    return None


def _shot_for_beat(name, used=None):
    """按拍次挑一个镜头类型：建立 / 推进 / 交手 / 收。"""
    rows = _load_ref("shot_ref.json")
    used = used or set()
    for nm, row in rows.items():
        if name in (row.get("beats") or []) and nm not in used:
            return nm, row
    return "", None


'''
    anchor = "def _entry_medium(item):"
    assert anchor in s, "插入点没找到"
    s = s.replace(anchor, fn + anchor, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  _match_shot:", hasattr(N, "_match_shot"), " _shot_for_beat:", hasattr(N, "_shot_for_beat"))
print("  表里", len(N._load_ref("shot_ref.json")), "种镜头")
for q in ("背面跟拍她跑", "只拍脚下的水花", "一个女孩跑"):
    r = N._match_shot(q)
    print(f"  {q[:12]:<14} -> {(r or {}).get('zh','(未命中)')[:40]}")
