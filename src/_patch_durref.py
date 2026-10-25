"""
时长改成查表：读 data/raw/duration_ref.json

起因
----
用户指出「镜头一的时长过长」。那一镜是「骑士站在石地中央，手按剑柄」——
**基本不动**，却因为有一个逗号被算成两拍，给了 5 秒。

根因不是系数错了，是**判据错了**：我按字数/逗号估时长。
时长应该由**运动幅度**决定：站着不动 5 秒是浪费，一个劈砍 3 秒是仓促。

改法
----
把经验做成**可编辑的数据表**（duration_ref.json），代码只负责查表。
以后要调时长，改 JSON 就行，不用动代码。
"""
import ast
import json
import os
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

if "_ref_duration" not in s:
    fn = '''_DUR_REF = {}


def _load_dur_ref():
    """读时长参考表。找不到就用内置兜底，不让节点因为缺文件崩掉。"""
    global _DUR_REF
    if _DUR_REF:
        return _DUR_REF
    p = os.path.join(ROOT, "data", "raw", "duration_ref.json")
    try:
        with open(p, encoding="utf-8") as f:
            _DUR_REF = json.load(f).get("classes", {})
    except Exception:
        _DUR_REF = {
            "static": {"words": ["站", "坐", "停", "不动"], "sec": 3},
            "action": {"words": ["走", "拿", "推", "转身"], "sec": 4},
            "strong": {"words": ["劈", "砍", "撞", "跑", "格挡"], "sec": 5},
            "transform": {"words": ["变成", "散开", "亮起"], "sec": 6},
        }
    return _DUR_REF


def _ref_duration(text):
    """按运动幅度给建议秒数。返回 (秒, 命中的类型名)。"""
    ref = _load_dur_ref()
    t = text or ""
    hit = {}
    for name, spec in ref.items():
        words = spec.get("words") or []
        n = sum(1 for w in words if w in t)
        if n:
            hit[name] = (spec.get("sec", 3), n)

    if not hit:
        return 3, "未识别"

    # 静态且没有动作类命中 -> 直接给静态秒数（不累加）
    moving = {k: v for k, v in hit.items()
              if k in ("action", "strong", "transform", "crowd")}
    if "static" in hit and not moving:
        return hit["static"][0], "static"

    # 否则取最长的那个类型
    name = max(hit, key=lambda k: hit[k][0])
    return hit[name][0], name


'''
    anchor = "def _est_beats(q):"
    assert anchor in s
    s = s.replace(anchor, fn + anchor, 1)

# _plan_duration：优先用查表结果，查不到才回落到拍数估算
old = '''    need = int(round(beats * _SEC_PER_BEAT))
    need = max(mn, min(need, mx))   # 下限也是硬约束：低于它提交无效'''
new = '''    # 先查表：时长由运动幅度决定，而不是字数或逗号数
    _rd, _rt = _ref_duration(q)
    need = int(_rd) if _rt != "未识别" else int(round(beats * _SEC_PER_BEAT))
    need = max(mn, min(need, mx))   # 下限也是硬约束：低于它提交无效'''
assert old in s, "need 计算处没匹配"
s = s.replace(old, new, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
print("  已接入时长参考表")
for q in ("骑士站在石地中央，手按剑柄",
          "一个对手入画劈下，他横剑格挡",
          "他收剑，前景虚焦身影退开",
          "竹简慢慢变成全息册子",
          "一个人拿起桌上的竹简"):
    sec, kind = N._ref_duration(q)
    print(f"    {q[:22]:<24} -> {sec}s  [{kind}]")
