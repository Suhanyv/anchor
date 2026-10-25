"""
新增「任务」维度：文生视频 / 图生视频 / 参考生视频

用户的三种视频生成方式，写法必须不同
------------------------------------
    文生视频    素材只有文字 -> 主体/场景/光/构图全都要写（现状，不变）
    图生视频    已有首帧   -> **只写动什么**；外观在图里，再描述一遍会让模型重画
    参考生视频  已有素材   -> 写清每条素材负责什么、**不复制什么**

关键设计决定
------------
对「图生视频」**不只是加一句提醒，而是真的不填外观槽位**（风格/光/工艺/材质）。
理由：那些信息已经在首帧图里了。填了 = 给模型两个来源 = 漂移。
空着的地方会显示占位符，反而是在告诉用户"这里不用你写"。

实现方式
--------
1. 新增参数 `任务`（默认 文生视频）
2. 现有 `run` 改名 `_run_inner`，外面套一个 `run` 包装器统一追加任务约定
   —— 这样 13 个格式分支一个都不用改
3. `_core` 看图生视频时清空外观字段
"""
import ast
import sys

P = r"F:\llm\comfyui\local_style_hint.py"
s = open(P, encoding="utf-8").read()

# ---------- 1) 模块级：当前任务 + 约定文本 + 包装器 ----------
if "_TASK_NOTE" not in s:
    helper = '''_CURRENT_TASK = "文生视频"

_TASK_NOTE = {
    "图生视频": (
        "\\n\\n【首帧约定】首帧图已提供，画面的外观、构图、光线以首帧为准。"
        "上面**没有填外观相关的槽位是有意的**——再描述一遍会让模型重画首帧。"
        "你只需要补：动什么、往哪个方向动、幅度多大、镜头怎么动、节奏。"
    ),
    "参考生视频": (
        "\\n\\n【参考约定】逐条写明每个素材负责什么（人物外观 / 动作路径 / 运镜节奏 / 音色），"
        "**并写明不要复制什么**。参考素材只承担明确职责，不要让模型自行推断。"
        "只描述要变化的部分；除变化项外，身份、服装、配色保持不变。"
    ),
}


def _post(text):
    return text + _TASK_NOTE.get(_CURRENT_TASK, "")


'''
    anchor = "def _exact_hits(query, rows, min_len=3):"
    assert anchor in s
    s = s.replace(anchor, helper + anchor, 1)

# ---------- 2) 参数 ----------
old_opt = '''                "输出格式": (['''
new_opt = '''                "任务": (["文生视频", "图生视频", "参考生视频"], {"default": "文生视频"}),
                "输出格式": (['''
assert old_opt in s
s = s.replace(old_opt, new_opt, 1)

# ---------- 3) run -> _run_inner，并套包装器 ----------
old_head = '''    def run(self, 中文描述, 模型目录, 语料文件, 题材文件, 工艺文件, 材质文件, 启用材质,
            输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):'''
new_head = '''    def run(self, *args, **kwargs):
        """对外入口：统一给输出追加「任务约定」"""
        text, dbg = self._run_inner(*args, **kwargs)
        return _post(text), dbg

    def _run_inner(self, 中文描述, 模型目录, 语料文件, 题材文件, 工艺文件, 材质文件, 启用材质,
                   任务, 输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):'''
if old_head in s:
    s = s.replace(old_head, new_head, 1)
    print("  已用两行签名替换")
else:
    # 逐行替换，避免缩进差异
    a1 = "    def run(self, 中文描述,"
    a2 = "输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):"
    assert a1 in s and a2 in s, "签名两行都找不到"
    s = s.replace(a1, "    def run(self, *args, **kwargs):\n"
                      "        text, dbg = self._run_inner(*args, **kwargs)\n"
                      "        return _post(text), dbg\n\n"
                      "    def _run_inner(self, 中文描述,", 1)
    s = s.replace(a2, "任务, 输出格式, 设备, 域, 匹配方式, 候选数, 追加到, 包含原文=False):", 1)
    print("  已用逐行替换")

# 在 _run_inner 开头设置当前任务
old_body = '''        输出格式 == "片段" and None'''
# 找不到就用更可靠的锚：函数体第一行注释
anchor2 = '''        # ---- 按目标格式分发 ----'''
assert anchor2 in s
s = s.replace(anchor2,
              '''        global _CURRENT_TASK
        _CURRENT_TASK = 任务

''' + anchor2, 1)

# ---------- 4) _core：图生视频时清空外观 ----------
old_core = '''    who_zh = item.get("director_zh") or item.get("director") or ""'''
new_core = '''    # 图生视频：外观已在首帧里，这里清空，避免两个来源打架（漂移）
    if _CURRENT_TASK == "图生视频":
        kw = []
        zh_light = ""

    who_zh = item.get("director_zh") or item.get("director") or ""'''
assert old_core in s, "_core 里 zh_light 构造处变了"
s = s.replace(old_core, new_core, 1)

# 风格字符串也清空
old_style = '''    if weak:
        zh_style = "<风格：库中没有可靠匹配，请自行指定>"
    else:
        zh_style = who_zh + ("：" + "、".join(kw[:4]) if kw else "")'''
new_style = '''    if _CURRENT_TASK == "图生视频":
        zh_style = ""          # 外观交给首帧
    elif weak:
        zh_style = "<风格：库中没有可靠匹配，请自行指定>"
    else:
        zh_style = who_zh + ("：" + "、".join(kw[:4]) if kw else "")'''
assert old_style in s, "zh_style 判定处变了"
s = s.replace(old_style, new_style, 1)

ast.parse(s)
open(P, "w", encoding="utf-8").write(s)

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N
it = N.LocalStyleHint.INPUT_TYPES()["required"]
print("  参数数:", len(it))
print("  任务:", it["任务"][0])
print("  run 是包装器:", "args" in N.LocalStyleHint.run.__code__.co_varnames)
