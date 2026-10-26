"""
分三次生成：每镜单独给任务，看分工能不能守住

上一轮的问题
------------
三镜一起让它写 -> 第一镜就开打（"斩落一名敌兵"），分工全丢。
原因：全局规则一次给三条，3B 记不住，会退化成"每镜打一下"。

这一轮
------
一次只问一镜，把该镜的任务写进这一镜的指令里：
    第1镜：交代场面与人数，**不许开打**，不许给正脸
    第2镜：只打一个人，只一个动作
    第3镜：收住，不交代结果

另外加一道后处理，过滤抒情与评价句（"壮观""震撼""美丽""视觉效果"），
看过滤后还剩多少是能用的。
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import torch                                      # noqa: E402
import local_style_hint as N                      # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

LLM_DIR = os.path.join(ROOT, "models", "llm-qwen25-3b")
M = os.path.join(ROOT, "models/e5-director-c27")
C = os.path.join(ROOT, "data/raw/corpus_v21.jsonl")
S = os.path.join(ROOT, "data/raw/subjects_v12.jsonl")
K = os.path.join(ROOT, "data/raw/crafts_v6.jsonl")
MT = os.path.join(ROOT, "data/raw/materials_v11.jsonl")

REQ = "一个骑士手握一把长剑，和一群人交战，想要三个镜头"

# 调性词：这类词在提示词里没用，还占字数
BAN = ("壮观", "震撼", "美丽", "唯美", "视觉效果", "画面感", "史诗般", "令人",
       "不禁", "仿佛", "似乎", "如同")

TASKS = [
    ("第 1 镜", "只交代场面与人数，**不许开打**，不许给任何人的正脸；"
                "写清他在画面里的位置和环境里有什么"),
    ("第 2 镜", "只打一个人：一个对手入画，一个动作，然后停。不许出现第二个人"),
    ("第 3 镜", "收住：不交代胜负，不出现倒地的人；写他站着的样子和画面怎么停"),
]

SYS = ("你是电影分镜师。只输出一行，不要标题不要解释。\n"
       "格式：镜头N（X秒）：<谁做了什么动作，结果是什么>\n"
       "只写能被拍到的具体东西，不写方位坐标，不写抒情和评价。")


def clean(s):
    """去掉含调性词的分句"""
    parts = re.split(r"[，,。；;]", s)
    keep = [p for p in parts if p and not any(b in p for b in BAN)]
    return "，".join(keep)


def main():
    items, mode, subj, dom, craft, mat = N._rank(
        REQ, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    kw = "、".join((it.get("kw_zh") or [])[:6])
    dur = [N._ref_duration(x)[0] for x in ("他站着", "一剑劈下", "收剑，人影退开")]
    print(f"=== 检索事实 ===\n  风格 {it.get('director_zh')}  {kw}   时长 {dur}\n")

    tok = AutoTokenizer.from_pretrained(LLM_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_DIR, dtype=torch.bfloat16, device_map="auto", low_cpu_mem_usage=True)
    model.eval()

    for i, (tag, task) in enumerate(TASKS):
        user = (f"整场戏：{REQ}\n"
                f"风格：{it.get('director_zh')}（{kw}）；道具：{(subj or {}).get('zh')}\n\n"
                f"现在只写{tag}，{dur[i]} 秒。\n"
                f"这一镜的任务：{task}")
        msgs = [{"role": "system", "content": SYS},
                {"role": "user", "content": user}]
        t = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(t, return_tensors="pt").to(model.device)
        t0 = time.time()
        with torch.no_grad():
            o = model.generate(**ids, max_new_tokens=120, do_sample=True,
                               temperature=0.7, top_p=0.9, repetition_penalty=1.1,
                               pad_token_id=tok.eos_token_id)
        resp = tok.decode(o[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True).strip()
        print(f"--- {tag}（{time.time()-t0:.1f}s）---")
        print(f"  原始：{resp}")
        print(f"  过滤：{clean(resp)}")
        print()

    print("### LLM_PER_SHOT_DONE")


if __name__ == "__main__":
    main()
