"""
时间约定：自动检测「延时 / 慢动作 / 实时」，并写出速度关系

为什么必须有这一层
------------------
"地球在太阳系不断公转" 这类描述里藏着一个物理矛盾：
**公转一圈 365 天，成片只有 5 秒。**

不写清楚，模型只有两种结局：
    1. 把它当实时镜头 -> 画出不可能的角速度 -> 观众觉得地球在乱飞
    2. 自作主张加轨道椭圆线 -> 变成科普示意图 -> 不是电影

而"延时"两个字一旦写明，模型就知道：允许慢过程快速发生，
并且**不能**出现无中间状态的瞬移。

三类
----
    延时摄影  长时间压进短片：云走、日出到日落、四季、天体公转/自转
    慢动作    极短时间拉长：水滴、碎裂、飞溅、头发
    实时      不额外加（默认，行为与以前完全一致）
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_time_note" not in s:
    fn = '''_TIME_LAPSE_WORDS = (
    "延时", "时间压缩", "时移", "缩时", "云在走", "日出到日落", "日落日出",
    "一整天", "一天里", "几天", "一年", "四季", "潮汐", "月相",
    "公转", "自转", "星轨", "银河移动", "影子移动",
)
_SLOWMO_WORDS = (
    "慢动作", "慢镜", "升格", "高速摄影", "极慢", "子弹时间",
    "水滴落下", "碎裂瞬间", "飞溅", "破片",
)


def _time_note(query, dur=6):
    """检测时间处理方式并返回约定块；实时/未提及返回空串。"""
    q = query or ""
    if any(w in q for w in _TIME_LAPSE_WORDS):
        return (
            f"\\n\\n【时间约定】这是**延时摄影**：把远长于 {dur} 秒的过程压缩进 {dur} 秒。"
            "因此允许慢速过程看起来在快速发生；"
            "但**不允许**出现：物体瞬移、无中间状态的跳变、光影硬切、"
            "以及示意图式的轨道线/箭头/标注。"
            "运动要有连续中间帧，只是整体速度被压缩。"
        )
    if any(w in q for w in _SLOWMO_WORDS):
        return (
            f"\\n\\n【时间约定】这是**慢动作**：把极短的过程拉长到 {dur} 秒。"
            "因此允许形变与飞溅被逐帧看清；"
            "但**不允许**出现：动作变成静止、粒子数量暴增、"
            "以及失去重力的漂浮感。"
        )
    return ""


'''
    anchor = "def _fmt_motion(item, subj, craft, mat, domain, query=\"\"):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# 接进 run 包装器：任务约定 + 时间约定一起追加
old = '''    def run(self, *args, **kwargs):
        """对外入口：统一给输出追加「任务约定」"""
        text, dbg = self._run_inner(*args, **kwargs)
        return _post(text), dbg'''
new = '''    def run(self, *args, **kwargs):
        """对外入口：统一追加「任务约定」与「时间约定」"""
        text, dbg = self._run_inner(*args, **kwargs)
        # 中文描述是第 1 个位置参数
        q = args[0] if args else kwargs.get("中文描述", "")
        note = _time_note(q, 6)
        if note:
            dbg = "【时间】检测到延时/慢动作\\n" + dbg
        return _post(text) + note, dbg'''
assert old in s, "run 包装器变了"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已加时间约定")
print("  _time_note:", hasattr(N, "_time_note"))
print("  公转 ->", bool(N._time_note("地球不断公转")))
print("  慢动作 ->", bool(N._time_note("慢动作拍水滴落下")))
print("  普通 ->", bool(N._time_note("一个男孩在卧室里相拥")))
