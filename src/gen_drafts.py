"""
三版草稿：本地 3B 出三种方向，人来挑

为什么是三种方向，不是三次随机采样
----------------------------------
纯随机采样出来的三版通常差不多（同一个模型的同一个倾向）。
所以三版给**不同的方向指令**：

    A 克制版   少动作，多留白，靠氛围
    B 事件版   每镜一个明确动作，节奏实
    C 陌生版   换个视点或换那个"不该给的东西"

挑完之后把偏好记进 data/raw/prefs.jsonl。
**偏好数据是这个系统唯一可能长出"品味"的原料**——
自己造不出标准答案，但可以从"人选了哪个"反推规则。

用法
----
    python src/gen_drafts.py "一个骑士手握一把长剑，和一群人交战，想要三个镜头"
    python src/gen_drafts.py "..." --pick B --note "B 的第二镜有真动作"
"""
import argparse
import json
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
PREFS = os.path.join(ROOT, "data/raw/prefs.jsonl")

# 违规与调性词：出现就标出来，不替人改
BAD = {"血": "暴力", "死": "暴力", "尸": "暴力", "倒地": "提前交代胜负",
       "壮观": "评价句", "震撼": "评价句", "美丽": "评价句", "唯美": "评价句",
       "视觉效果": "评价句", "令人": "评价句", "仿佛": "评价句", "似乎": "评价句"}

DIRECTIONS = {
    "A 克制版": "少动作、多留白：每镜只让人做一件很小的事，其余交给环境和停顿。",
    "B 事件版": "节奏要实：每镜都有一个说得清的动作和它的结果，不靠氛围撑。",
    "C 陌生版": "换视点：不要一直拍他本人，至少一镜从他之外的东西看过去"
                "（他的手、地上的东西、旁人的动作）。",
}

SYS = ("你是电影分镜师。只输出三行，不要标题不要解释。\n"
       "格式：镜头N（X秒）：<谁做了什么，结果是什么>\n"
       "只写能被拍到的具体东西，不写方位坐标，不写抒情和评价，"
       "不写血腥、不写倒地、不写胜负。")

FEW_U = ("请求：一个人走进便利店，想要三个镜头\n"
         "风格：是枝裕和（静止、日常、自然光）；道具：自动售货机；时长 4/5/4 秒")
FEW_A = ("镜头1（4秒）：男人推开门进来，门上的铃响了一下，他在门口停住\n"
         "镜头2（5秒）：他走到冷柜前拉开门，取出一瓶水，冷气从柜里溢出来\n"
         "镜头3（4秒）：他在收银台放下水，手停在口袋里找钱")


def scan(text):
    hits = [f"{k}（{v}）" for k, v in BAD.items() if k in text]
    return sorted(set(hits))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request")
    ap.add_argument("--pick", choices=list("ABC"), default=None)
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    items, mode, subj, dom, craft, mat = N._rank(
        a.request, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    kw = "、".join((it.get("kw_zh") or [])[:6])
    dur = [N._ref_duration(x)[0] for x in ("他站着", "一剑劈下", "收剑，人影退开")]
    print(f"检索：{it.get('director_zh')}（{kw}）道具 {(subj or {}).get('zh')} "
          f"时长 {dur}\n")

    tok = AutoTokenizer.from_pretrained(LLM_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_DIR, dtype=torch.bfloat16, device_map="auto", low_cpu_mem_usage=True)
    model.eval()

    drafts = {}
    for name, direction in DIRECTIONS.items():
        user = (f"整场戏：{a.request}\n"
                f"风格：{it.get('director_zh')}（{kw}）；道具：{(subj or {}).get('zh')}\n"
                f"三镜时长：{dur[0]} / {dur[1]} / {dur[2]} 秒\n\n"
                f"这一版的创作方向：{direction}\n写三行。")
        msgs = [{"role": "system", "content": SYS},
                {"role": "user", "content": FEW_U},
                {"role": "assistant", "content": FEW_A},
                {"role": "user", "content": user}]
        t = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(t, return_tensors="pt").to(model.device)
        t0 = time.time()
        with torch.no_grad():
            o = model.generate(**ids, max_new_tokens=260, do_sample=True,
                               temperature=0.8, top_p=0.9, repetition_penalty=1.1,
                               pad_token_id=tok.eos_token_id)
        resp = tok.decode(o[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True).strip()
        drafts[name] = resp
        flags = scan(resp)
        print(f"━━━ {name}（{time.time()-t0:.1f}s）━━━")
        print(resp)
        if flags:
            print(f"  ⚠️ 需要处理：{'、'.join(flags)}")
        print()

    if a.pick:
        rec = {"request": a.request, "style": it.get("director_zh"),
               "picked": a.pick, "note": a.note,
               "drafts": drafts, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        with open(PREFS, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n = sum(1 for _ in open(PREFS, encoding="utf-8"))
        print(f"已记录：选了 {a.pick}（累计 {n} 条偏好）")
    else:
        print("（挑一版后加 --pick A/B/C --note \"为什么\" 再跑一次，就会记下来）")

    print("\n### DRAFTS_DONE")


if __name__ == "__main__":
    main()
