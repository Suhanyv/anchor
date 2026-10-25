"""
剥掉指令前缀：主体里不该出现"用 XX 生成一段…"这种命令

问题
----
用户在描述里会带指令：
    "用 minimax H3 文生视频：地球在太阳系里不断公转"
    "帮我做一段我和妹妹在沙滩上奔跑的镜头"

我们把 query 原样当主体（这是对的——中文平台的主体该用用户原话），
于是输出里出现了「主体动作：用 minimax H3 文生视频：地球…」。

那句话不是画面内容，是给工具下的命令。**模型看到会把"H3""文生视频"当成画面里的东西。**

规则
----
1. 有冒号且冒号后够长 -> 取冒号后的
2. 去掉平台名（minimax / 即梦 / sd2.5 / veo …）
3. 去掉生成动词短语（文生视频 / 图生视频 / 做一段 / 帮我 / 我想要 …）
4. 收尾去掉"的视频""的镜头"这类尾巴
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_strip_cmd" not in s:
    fn = '''_CMD_WORDS = (
    "文生视频", "图生视频", "参考生视频", "文生图", "图生图",
    "生成一段", "生成一个", "生成", "做一段", "做一个", "做个", "拍一段", "拍一个",
    "帮我", "帮忙", "请", "我想要", "想要", "给我", "能不能", "可以", "麻烦",
)
_TAIL_WORDS = ("的视频", "的镜头", "的画面", "的片子", "短片", "一段视频")


def _strip_cmd(q):
    """从描述里剥掉指令前缀与平台名，只留画面内容。"""
    import re as _re
    t = (q or "").strip()
    # 1) 冒号后面才是描述
    for sep in ("：", ":"):
        if sep in t:
            head, tail = t.split(sep, 1)
            if len(tail.strip()) >= 4:
                t = tail.strip()
            break
    # 2) 平台名
    for words, _also, _fmt in _PLATFORM_HINTS:
        for w in words:
            if len(w) >= 2:
                t = _re.sub(_re.escape(w), " ", t, flags=_re.I)
    # 3) 生成动词
    for w in _CMD_WORDS:
        t = t.replace(w, " ")
    # 4) 收尾
    t = t.strip()
    for w in _TAIL_WORDS:
        if t.endswith(w):
            t = t[: -len(w)]
    # 5) 收掉多余空白与标点
    t = _re.sub(r"\\s+", " ", t).strip(" ，,。.、·-")
    return t or (q or "").strip()


'''
    anchor = "def _core(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# _core 里 subject_zh 用剥过的
old = '''        "subject_zh": (query or "").strip(),'''
new = '''        "subject_zh": _strip_cmd(query),'''
assert old in s, "subject_zh 那一行变了"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
for q in ("用 minimax H3 文生视频：地球在太阳系里不断公转",
          "帮我做一段我和妹妹在沙滩上奔跑的镜头",
          "一个人拿起桌上的竹简",
          "我想要一段霓虹灯管照在湿街上的镜头"):
    print(f"  {q[:30]:<32} -> {N._strip_cmd(q)}")
