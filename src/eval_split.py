"""
图像 / 视频混检时，视频查询会不会被图像文档抢走？

为什么要测
----------
现状：826 条文档（图像 627 / 视频 199）放在**同一个索引**里，靠 domain 字段硬过滤。
「域」参数选「视频」时会过滤，但：选「自动」时靠 router 猜，猜错就没有视频了。

更根本的问题：视频文档的 text_semantic 与图像文档写法一样（都是静态描述 + motion 元数据），
没有时序语言。所以即便检索对了，输出的提示词也不像"视频提示词"。

本脚本测：给一批**明显带时间/运镜**的中文描述，看 top1 落在图像还是视频文档上。
如果 top1 大量是图像文档，就证明了"必须分开"。
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 明显是"视频"的描述：提到运镜 / 时长 / 过程 / 变化
VIDEO_QUERIES = [
    ("镜头慢慢推近一个坐在窗边的人，一直推到他脸的特写", ["Alfred Hitchcock", "Hou Hsiao-hsien"]),
    ("跟拍一辆车穿过雪地，摄影机一直在它侧面匀速移动", ["Denis Villeneuve", "Ridley Scott"]),
    ("长镜头不剪辑，两个人从走廊这头走到那头，中途一直没断", ["Hou Hsiao-hsien", "Alfonso Cuarón"]),
    ("镜头从地面升起来，最后停在高处俯视整个空间", ["Denis Villeneuve", "Stanley Kubrick"]),
    ("手持晃动的跟拍，一群人跑过狭窄通道，末尾急停", ["Paul Greengrass", "Kathryn Bigelow"]),
    ("镜头缓慢横移，前景的树枝一条条掠过画面", ["Terrence Malick", "Hou Hsiao-hsien"]),
    ("一镜到底，从屋外走进去，穿过三个房间到窗边", ["Alfonso Cuarón", "Hou Hsiao-hsien"]),
    ("两个人对视着慢慢转圈，镜头跟着他们旋转", ["Park Chan-wook", "Wong Kar-wai"]),
]

IMAGE_QUERIES = [
    ("一个穿着青铜纹重甲的武士站成一排，黄昏", ["Wuershan"]),
    ("一只青铜巨兽从城墙后面立起来", ["Wuershan"]),
    ("白衣女子站在薄雾里，红绸飘着", ["Ching Siu-tung"]),
    ("客栈里一张桌子，上面放着一把剑", ["King Hu"]),
]


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "e5-director-c19")
    corpus_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "raw", "corpus_v17.jsonl")
    if not os.path.isdir(model):
        raise SystemExit(f"模型目录不存在：{model}")

    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8") if l.strip()]
    dom = [d["domain"] for d in corpus]
    print(f"语料 {len(corpus)} 条：图像 {dom.count('prompt_image')} / 视频 {dom.count('prompt_video')}\n")

    tok = AutoTokenizer.from_pretrained(model)
    enc = AutoModel.from_pretrained(model).eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    @torch.no_grad()
    def encode(texts, prefix):
        out = []
        for i in range(0, len(texts), 32):
            b = tok([prefix + t for t in texts[i:i + 32]], padding=True,
                    truncation=True, max_length=128, return_tensors="pt")
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(F.normalize(((h * m).sum(1) / m.sum(1).clamp(min=1e-6)).float(), dim=-1))
        return torch.cat(out).numpy()

    de = encode([d["text_semantic"] for d in corpus], "passage: ")
    dirs = [d["director"] for d in corpus]

    for name, qs, want_dom in (("视频类描述", VIDEO_QUERIES, "prompt_video"),
                               ("图像类描述", IMAGE_QUERIES, "prompt_image")):
        qe = encode([q for q, _ in qs], "query: ")
        print(f"=== {name}（期望 top1 落在 {want_dom}）===")
        print(f"{'查询':<38} {'top1 域':<14} {'top1 是谁':<18} 期望导演")
        print("-" * 96)
        n_right_dom = 0
        n_right_dir = 0
        for qi, (q, accept) in enumerate(qs):
            s = de @ qe[qi]
            k = int(s.argmax())
            got_dom = dom[k]
            right = (got_dom == want_dom)
            n_right_dom += right
            hit_dir_ok = dirs[k] in accept
            n_right_dir += hit_dir_ok
            hit_dir = "✅" if hit_dir_ok else "  "
            print(f"{q[:36]:<38} {got_dom:<14} {dirs[k][:16]:<18} {accept[0][:14]} {hit_dir}")
        print(f"-> 域对了 {n_right_dom}/{len(qs)}   导演对了 {n_right_dir}/{len(qs)}")
        print()


if __name__ == "__main__":
    main()
    print("### SPLIT_AUDIT_DONE")
