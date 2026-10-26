"""
直接在管线里让本地小模型写分镜：可行性测试

目的只有一个：**它写得好不好。** 不好就不值得做进节点。

做法
----
把节点检索到的东西（风格中文名 + 关键词、主体、时长）当作**事实**喂给它，
让它只做一件事：编三拍。其余一律不许它发挥——
    不许它改风格（那是检索的事）
    不许它加特效（那是模板的事）
    只许它写：谁、在哪、做什么

对照
----
跑完把它的输出和我写的那三镜并排看。我写的不算标准答案，
但它要是三句都空泛（"紧张地战斗"这种），就说明 3B 不够。
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
    "你是电影分镜师。只输出三行分镜，不要解释，不要加标题。\n"
    "每行格式：镜头N（X秒）：<谁、在哪、做什么>\n"
    "硬规则：\n"
    "1. 每一镜只写一个动作，写清方向或幅度\n"
    "2. 只写能被拍到的具体东西，不写情绪词（紧张/激烈/震撼一律不许）\n"
    "3. 不许提风格名、导演名、镜头参数（那些另有地方写）\n"
    "4. 三种镜头分工：第一镜交代场面与人数但不给正脸；第二镜只打一个人；"
    "第三镜收住，不交代结果\n"
)


def build_context():
    """把节点检索到的事实取出来，作为给 LLM 的约束。"""
    items, mode, subj, dom, craft, mat = N._rank(
        REQ, M, C, "cpu", 1, "导演/风格聚合", "视频", S, K, MT, True)
    it = items[0]
    kw = "、".join((it.get("kw_zh") or [])[:6])
    who = (subj or {}).get("zh", "—")
    return {
        "style": it.get("director_zh") or it.get("director"),
        "kw": kw,
        "subject": who,
        "dur": [N._ref_duration(x)[0] for x in
                ("他站着", "一剑劈下", "收剑，人影退开")],
    }


def main():
    ctx = build_context()
    print("=== 检索到的事实 ===")
    print(f"  风格 {ctx['style']}   关键词 {ctx['kw']}")
    print(f"  主体 {ctx['subject']}   建议时长 {ctx['dur']}\n")

    if not os.path.isdir(LLM_DIR):
        print(f"  模型目录不存在：{LLM_DIR}")
        print("\n### LLM_TEST_NO_MODEL")
        return

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(LLM_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_DIR, dtype=torch.bfloat16, device_map="auto",
        low_cpu_mem_usage=True)
    model.eval()
    print(f"  加载 {time.time()-t0:.1f}s   设备 {next(model.parameters()).device}")

    user = (
        f"请求：{REQ}\n\n"
        f"已知事实（照用，不要改）：\n"
        f"- 美术风格：{ctx['style']}，画面关键词：{ctx['kw']}\n"
        f"- 主要道具：{ctx['subject']}\n"
        f"- 三镜时长：{ctx['dur'][0]}秒 / {ctx['dur'][1]}秒 / {ctx['dur'][2]}秒\n\n"
        f"现在写这三行分镜。"
    )
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": user}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=320, do_sample=True,
                             temperature=0.8, top_p=0.9,
                             repetition_penalty=1.05,
                             pad_token_id=tok.eos_token_id)
    new = out[0][ids["input_ids"].shape[1]:]
    resp = tok.decode(new, skip_special_tokens=True).strip()

    print(f"\n=== 它写的（{time.time()-t0:.1f}s）===\n")
    print(resp)
    print("\n=== 我写的（对照）=== ")
    print("镜头1（3秒）：全景或中远景，他在军阵、黄昏、尘土里，画框边缘有几个人影"
          "但脸都不清；机位缓慢横移")
    print("镜头2（5秒）：近景只跟骑士，一个对手从左侧挥入劈下，他横剑架住，"
          "两刃相碰，火星很小")
    print("镜头3（4秒）：镜头拉开，他背对镜头，剑尖垂向地面；其余人影从两侧退出画面")
    print("\n### LLM_TEST_DONE")


if __name__ == "__main__":
    main()
