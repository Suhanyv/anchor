"""
3B 加 few-shot 再试一次：它是不是"不知道什么叫分镜"，而不是"写不出来"

上一轮它写的是站位（"剑指向左后方，人群密集于右前方"），没有事件。
两种可能：
    A 它不懂"分镜 = 事件推进"   -> 给一个好例子就能学会
    B 3B 的能力上限就在这        -> 换 7B 或做量化

这个脚本只改一处：加一对示例（用另一个场景，避免它抄）。
"""
import os
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

SYS = (
    "你是电影分镜师，只输出三行，不要标题不要解释。\n"
    "每行格式：镜头N（X秒）：<画面内容>\n"
    "每一行必须写清【谁】【做了什么动作】【结果或下一步】，不要写方位坐标。\n"
)

# 示例用另一个场景，避免它照抄
FEWSHOT_USER = (
    "请求：一个人走进便利店，想要三个镜头\n"
    "已知事实：风格 是枝裕和，关键词 静止、日常、自然光；道具 自动售货机；"
    "时长 4/5/4 秒"
)
FEWSHOT_ASSIST = (
    "镜头1（4秒）：男人推开门进来，门上的铃响了一下，他在门口停住，抬眼看了看货架\n"
    "镜头2（5秒）：他走到冷柜前拉开门，取出一瓶水，冷气从柜里溢出来\n"
    "镜头3（4秒）：他在收银台放下水，手停在口袋里找钱，收银员没有抬头"
)


def main():
    items, mode, subj, dom, craft, mat = N._rank(
        REQ, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    kw = "、".join((it.get("kw_zh") or [])[:6])
    dur = [N._ref_duration(x)[0] for x in ("他站着", "一剑劈下", "收剑，人影退开")]
    print(f"=== 检索事实 ===\n  风格 {it.get('director_zh')}  {kw}\n"
          f"  道具 {(subj or {}).get('zh')}   时长 {dur}\n")

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(LLM_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_DIR, dtype=torch.bfloat16, device_map="auto", low_cpu_mem_usage=True)
    model.eval()
    print(f"  加载 {time.time()-t0:.0f}s")

    user = (
        f"请求：{REQ}\n\n"
        f"已知事实（照用）：\n"
        f"- 风格：{it.get('director_zh')}，画面关键词：{kw}\n"
        f"- 道具：{(subj or {}).get('zh')}\n"
        f"- 时长：{dur[0]} / {dur[1]} / {dur[2]} 秒\n\n"
        f"写这三行。"
    )
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": FEWSHOT_USER},
            {"role": "assistant", "content": FEWSHOT_ASSIST},
            {"role": "user", "content": user}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)

    outs = []
    for i in range(2):          # 跑两次：看稳定性
        t0 = time.time()
        with torch.no_grad():
            o = model.generate(**ids, max_new_tokens=300, do_sample=True,
                               temperature=0.7, top_p=0.9, repetition_penalty=1.1,
                               pad_token_id=tok.eos_token_id)
        resp = tok.decode(o[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True).strip()
        outs.append(resp)
        print(f"\n=== 第 {i+1} 次（{time.time()-t0:.1f}s）===\n{resp}")

    print("\n### LLM_FEWSHOT_DONE")


if __name__ == "__main__":
    main()
