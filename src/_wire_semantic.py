"""
升级第二步：三条通道接上语义兜底

顺序：关键词命中优先（准、可解释）→ 不中则语义 top1，且必须过下限。
下限从数据来（下面注释里是实测分数）。

为什么带下限：语义相似度永远会给出一个"最近的"，不过下限就等于每句都命中，
那和以前"关键词乱撞"是同一类错。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ① _load 里记住 st，供语义匹配用
old = '''    _IDX_CACHE[filekey] = (st, idx)'''
if old in s:
    pass
# 在 _load 返回前记全局：找一个稳妥插入点
if "_SEM_ST" not in s:
    s = s.replace("_SEM_CACHE = {}", "_SEM_CACHE = {}\n_SEM_ST = [None]", 1)

# ② 让 _sem_top 支持 st=None
s = s.replace('''def _sem_top(st, filename, query, k=1):
    """语义检索一张表，返回 [(score, name)] 降序。"""
    idx = _sem_index(st, filename)''',
'''def _sem_top(st, filename, query, k=1):
    """语义检索一张表，返回 [(score, name)] 降序。st 为 None 时用最近一次加载的。"""
    st = st or _SEM_ST[0]
    if st is None:
        return []
    idx = _sem_index(st, filename)''')

# ③ 声音
old_s = '''def _scene_sound(query):
    """场景 → 环境声。命中返回 (zh, en)，否则 ("", "")。'''
new_s = '''SOUND_SEM_FLOOR = 0.42   # 实测：颠锅→厨房 0.481（对）；数钱→数钱 0.609（对）


def _scene_sound(query):
    """场景 → 环境声。关键词优先，不中走语义（带下限）。'''
assert old_s in s, "声音函数没匹配"
s = s.replace(old_s, new_s, 1)

old_s2 = '''    row = _match_ref("sound_ref.json", query, [])
    if not row:
        return "", ""'''
new_s2 = '''    row = _match_ref("sound_ref.json", query, [])
    if not row:
        top = _sem_top(None, "sound_ref.json", query, 1)
        if top and top[0][0] >= SOUND_SEM_FLOOR:
            row = _sem_row("sound_ref.json", top[0][1])
    if not row:
        return "", ""'''
assert old_s2 in s, "声音匹配处没匹配"
s = s.replace(old_s2, new_s2, 1)

# ④ 风险
old_r = '''def _scene_risks(query, limit=3):'''
new_r = '''RISK_SEM_FLOOR = 0.45   # 实测：数钱→手部小物件 0.632（对）；颠锅→火窑 0.257（错，被挡）


def _scene_risks(query, limit=3):'''
assert old_r in s
s = s.replace(old_r, new_r, 1)

old_r2 = '''        if any(k in q for k in (row.get("kw") or [name])):
            rs = [r for r in (row.get("risk") or []) if r not in
                  [x for p in pools for x in p]]
            if rs:
                pools.append(rs)'''
new_r2 = '''        if any(k in q for k in (row.get("kw") or [name])):
            rs = [r for r in (row.get("risk") or []) if r not in
                  [x for p in pools for x in p]]
            if rs:
                pools.append(rs)
    if not pools:
        # 关键词一条都没中：走语义，过下限才用
        top = _sem_top(None, "risk_ref.json", q, 1)
        if top and top[0][0] >= RISK_SEM_FLOOR:
            rs = _sem_row("risk_ref.json", top[0][1]).get("risk") or []
            if rs:
                pools.append(list(rs))'''
assert old_r2 in s, "风险循环处没匹配"
s = s.replace(old_r2, new_r2, 1)

# ⑤ 节拍
old_b = '''def _scene_beats(query):'''
new_b = '''BEAT_SEM_FLOOR = 0.34   # 实测：数钱→数 0.682（对）；颠锅→切 0.331（勉强，作下限参考）


def _scene_beats(query):'''
assert old_b in s
s = s.replace(old_b, new_b, 1)

old_b2 = '''        if any(k in q for k in (row.get("kw") or [name])):
            return (row.get("mid") or ""), (row.get("end") or "")
    return "", ""'''
new_b2 = '''        if any(k in q for k in (row.get("kw") or [name])):
            return (row.get("mid") or ""), (row.get("end") or "")
    # 关键词一条都没中：走语义，过下限才用
    top = _sem_top(None, "beat_ref.json", q, 1)
    if top and top[0][0] >= BEAT_SEM_FLOOR:
        row = _sem_row("beat_ref.json", top[0][1])
        return (row.get("mid") or ""), (row.get("end") or "")
    return "", ""'''
assert old_b2 in s, "节拍循环处没匹配"
s = s.replace(old_b2, new_b2, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)
print("  三条通道已接语义兜底（带下限）")
