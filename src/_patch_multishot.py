"""
多镜头：一条描述里有多个镜头时，输出「共用块 + 逐镜」

设计原则
--------
1. **只在有结构时拆**：镜头标记 / 行首序号 / 箭头
2. **只给数量也能用**："想要三个镜头" 但没有结构 -> 出 N 个空槽，
   共用块照写。**不替用户编动作**（编出来一定重复）
3. **共用块只写一次**：风格/光线/画幅/声音/negative 提到共用块。
   这不是省字，是防漂移——逐镜重复写风格会让三次生成得到三种色调，剪不起来。

与图生视频同理
--------------
"一个镜头的 look 只该有一个来源。" 多来源 = 漂移。
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_split_shots" not in s:
    fns = '''_CN_NUM = "一二三四五六七八九十"
_SHOT_HEAD = (
    r"(?:镜头|镜号|第)\\s*[" + _CN_NUM + r"1-9]\\s*(?:个)?(?:镜(?:头)?)?",
)
_COUNT_PAT = r"([一二三四五六七八九十1-9])\\s*(?:个)?镜头"


def _split_shots(q):
    """把一条描述拆成多个镜头。拆不出来返回 []。

    只认三种显式结构，不做语义猜测：
        1. 镜头标记（镜头一 / 第2镜 / 镜号3）
        2. 行首序号（1. / 2、/ 3)）
        3. 箭头或竖线（→ / -> / |）
    """
    import re
    t = (q or "").strip()
    if not t:
        return []

    # 1) 镜头标记
    parts = re.split(_SHOT_HEAD[0] + r"\\s*[：:.、]?", t)
    parts = [p.strip(" ：:，,。.、-—\\n") for p in parts if p and len(p.strip()) >= 3]
    if len(parts) >= 2:
        return parts

    # 2) 行首数字序号
    if re.search(r"(?m)^\\s*[1-9][.、)]\\s+\\S", t):
        parts = [p.strip() for p in re.split(r"(?m)^\\s*[1-9][.、)]\\s+", t)
                 if p and len(p.strip()) >= 3]
        if len(parts) >= 2:
            return parts

    # 3) 箭头 / 竖线
    if re.search(r"→|->|—>|｜|\\|", t):
        parts = [p.strip(" ，,。.、") for p in re.split(r"→|->|—>|｜|\\|", t)
                 if p and len(p.strip(" ，,。.、")) >= 3]
        if len(parts) >= 2:
            return parts

    return []


def _count_shots(q):
    """用户只说"想要三个镜头"但没给结构时，读出数量。读不到返回 0。"""
    import re
    m = re.search(_COUNT_PAT, q or "")
    if not m:
        return 0
    c = m.group(1)
    if c.isdigit():
        return int(c)
    idx = _CN_NUM.find(c)
    return (idx + 1) if idx >= 0 else 0


def _fmt_multishot(shots, item, subj, craft, mat, domain, fmt=""):
    """共用块 + 逐镜。shots 里的空串表示"这一镜待填"。"""
    c = _core(item, subj, craft, mat, domain, "")
    ar = c["ar"]
    light = c["zh_light"] or "<光线与色调>"
    style = c["zh_style"] or "<风格>"
    out = [
        f"【共用】{light}。{style}。{ar}。",
        "        只使用<环境声>，不要配乐，不要字幕。",
        "        不要出现：<2-4 个会让这批全废掉的错误，例如多余的人、"
        "手部畸形、兵器穿模、色调不一致>。",
    ]
    if "Veo" in fmt:
        out.append("        ⚠️ Veo 一次只出一镜 8 秒，下面每一镜需要单独生成一次。")
    out.append("")
    for i, sh in enumerate(shots, 1):
        body = sh.strip() or "<写这一镜的动作：只有 1-2 个动作，写清从什么变成什么>"
        out.append(f"【镜头 {i}】{body}")
    out.append("")
    out.append("（共用块只写一次：逐镜重复风格会让各次生成色调不一致，剪不到一起。）")
    return "\\n".join(out)


'''
    anchor = "def _strip_cmd(q):"
    assert anchor in s
    s = s.replace(anchor, fns + anchor, 1)

# 接进 _run_inner：在任务分派之前
anchor2 = '''        # ---- 任务约定（文生图不加，保持原样）----'''
assert anchor2 in s
add = '''        # ---- 多镜头：检出结构就出「共用块 + 逐镜」----
        _shots = _split_shots(中文描述)
        if len(_shots) < 2:
            _n = _count_shots(中文描述)
            if _n >= 2:
                _shots = [""] * _n   # 只给了数量：出空槽，不替用户编动作
        if len(_shots) >= 2:
            _ms = _fmt_multishot(_shots, items[0], subj, craft, mat,
                                 domain_used, 输出格式)
            _tag = ("检出多镜结构" if any(_shots)
                    else f"只检出数量 {len(_shots)} 镜，已出空槽")
            dbg = f"【多镜头】{_tag}\\n" + dbg
            return (_ms, dbg)

''' + anchor2
s = s.replace(anchor2, add, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加多镜头")
print("  _split_shots:", hasattr(N, "_split_shots"), " _count_shots:", hasattr(N, "_count_shots"))
for q in ("镜头一：他站起来。镜头二：他走出去。",
          "拿起竹简 → 竹简变化 → 变成册子",
          "一个骑士和一群人交战，想要三个镜头"):
    print(f"    {q[:24]:<26} -> {len(N._split_shots(q))} 段 / 数量 {N._count_shots(q)}")
