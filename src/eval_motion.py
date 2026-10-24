"""
视频运镜基准：25 条

为什么需要它
------------
之前用 8 条查询调模型 —— 命中 1 条=12.5%、2 条=25%，
随机种子换一下就能"提升"或"退步"，那不是优化，是追噪声。

这个基准覆盖四个维度，每条都不含导演名：

    运镜类型    推近 / 拉远 / 横移 / 升降 / 环绕 / 手持 / 固定
    时长节奏    长镜头不剪辑 / 一镜到底 / 快切 / 突然动作
    主体变化    人走进走出 / 从远到近 / 停顿后再动
    光影变化    风起尘扫 / 火苗倒向 / 从暗到亮

判读口径
--------
    域命中      top1 落在 prompt_video（说明"这是视频查询"被认出来了）
    导演命中    top1 落在可接受导演之一（说明"运镜 -> 导演"的映射学到了）

用法：
    python src/eval_motion.py models/e5-director-c19 data/raw/corpus_v19.jsonl
    python src/eval_motion.py models/e5-director-c21 data/raw/corpus_v19.jsonl
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (中文描述, [可接受导演], 维度)
CASES = [
    ("镜头一动不动，两个人从画面左边走进来，站了一会儿，又从右边走出去",
     ["Hou Hsiao-hsien", "Jia Zhangke"], "固定+主体进出"),
    ("摄影机极慢地向前推，推了十几秒才靠近那个站着的人",
     ["Denis Villeneuve", "Hou Hsiao-hsien"], "推近"),
    ("镜头从下面往上摇，最后停在高处俯视整个房间",
     ["Alfred Hitchcock", "Stanley Kubrick"], "升降"),
    ("摄影机贴着人物侧面一路跟拍，脚步不停，最后急刹",
     ["Paul Greengrass", "Kathryn Bigelow"], "手持跟拍"),
    ("一个镜头跟着人从街上进门，穿过前厅上楼，全程不切",
     ["Alfonso Cuarón", "Hou Hsiao-hsien"], "一镜到底"),
    ("缓慢横移，前景的草一根根掠过镜头",
     ["Terrence Malick", "Hou Hsiao-hsien"], "横移"),
    ("镜头围着两个人转了大半圈，他们一直面对面站着",
     ["Park Chan-wook", "Alfonso Cuarón"], "环绕"),
    ("手持镜头跟着一个快步走的人穿过霓虹街道，画面有点拖影",
     ["Wong Kar-wai", "Martin Scorsese"], "手持+抽帧"),
    ("镜头匀速向前推，走廊两边完全对称，一直推到尽头",
     ["Stanley Kubrick", "Wes Anderson"], "匀速前推"),
    ("极远景停住很久，然后才慢慢推到一双眼睛",
     ["Sergio Leone", "Denis Villeneuve"], "静止转推近"),
    ("镜头对着墙上的东西慢慢变焦，突然切到另一个角度的墙",
     ["David Lynch", "Nicolas Roeg"], "变焦+跳切"),
    ("一整个长镜头里，摄影机缓慢漂过水面和散落的杂物",
     ["Andrei Tarkovsky", "Michelangelo Antonioni"], "超长镜头"),
    ("机位完全不动，只有手在画面里动",
     ["Robert Bresson"], "完全固定"),
    ("镜头保持静止特写，脸几乎不动，很久都没有剪",
     ["Ingmar Bergman", "Robert Bresson"], "静止特写"),
    ("静止的远景里突然刮起风，尘土横着扫过画面，然后人开始动",
     ["Akira Kurosawa"], "风起+突然动作"),
    ("镜头低低地贴着地面移动，然后一口气升起来变成俯视",
     ["Kathryn Bigelow", "Steven Spielberg"], "低角度+升起"),
    ("摄影机藏在草丛的高度，缓慢向前挪，前面的人没察觉",
     ["Terrence Malick", "Alfred Hitchcock"], "隐蔽前移"),
    ("镜头快速推近一张脸，然后猛地甩到旁边的人",
     ["Martin Scorsese", "Wong Kar-wai"], "快推+甩镜"),
    ("缓慢横移掠过一排排青铜铠甲，火把一根根经过镜头",
     ["Wuershan"], "横移+火光"),
    ("镜头仰起来，一直仰到看不见巨型结构的顶",
     ["Frant Gwo", "Denis Villeneuve"], "仰拍"),
    ("固定机位拍客栈大堂，一个人突然从楼上跃下来落在桌上",
     ["King Hu"], "固定+突然爆发"),
    ("镜头跟着白衣人往上升，袖子一直在飘，雾从镜头前掠过",
     ["Ching Siu-tung"], "跟拍上升"),
    ("一个镜头绕着燃烧的火圈转，火苗跟着镜头方向倒",
     ["Jiaozi", "Park Chan-wook"], "环绕+火光"),
    ("从室内慢慢推向窗口，窗外从暗变亮，最后一镜停在窗框上",
     ["Denis Villeneuve", "Ingmar Bergman"], "推近+光变"),
    ("一个不剪的长镜头里，镜头缓慢后退，人越走越远，最后变成远景",
     ["Hou Hsiao-hsien", "Michelangelo Antonioni"], "后退+不剪辑"),
]


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "models", "e5-director-c19")
    corpus_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "raw", "corpus_v19.jsonl")
    quiet = "--quiet" in sys.argv
    if not os.path.isdir(model):
        raise SystemExit(f"模型目录不存在：{model}")

    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8") if l.strip()]
    dom = [d["domain"] for d in corpus]
    dirs = [d["director"] for d in corpus]

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
    qe = encode([c[0] for c in CASES], "query: ")

    n_dom = n_dir = n_top3 = 0
    rows = []
    for qi, (q, accept, dim) in enumerate(CASES):
        s = de @ qe[qi]
        k = int(s.argmax())
        best = {}
        for j, d in enumerate(dirs):
            if d not in best or s[j] > best[d]:
                best[d] = float(s[j])
        names = [x for x, _ in sorted(best.items(), key=lambda kv: -kv[1])]
        ranks = [names.index(a) + 1 for a in accept if a in names]
        r = min(ranks) if ranks else 999
        ok_dom = (dom[k] == "prompt_video")
        ok_dir = (r == 1)
        n_dom += ok_dom
        n_dir += ok_dir
        n_top3 += (r <= 3)
        rows.append((dim, q, accept[0], dirs[k], r, ok_dom, ok_dir))

    if not quiet:
        print(f"模型 {os.path.basename(model)}   语料 {os.path.basename(corpus_path)} "
              f"({len(corpus)} 条)\n")
        print(f"{'维度':<14} {'查询':<30} {'期望':<18} {'实得':<18} 名次")
        print("-" * 100)
        for dim, q, want, got, r, ok_dom, ok_dir in rows:
            mark = "✅" if ok_dir else ("◐" if r <= 3 else "❌")
            dmark = "" if ok_dom else " [域错]"
            print(f"{dim:<14} {q[:28]:<30} {want[:16]:<18} {got[:16]:<18} "
                  f"{r if r != 999 else '不在库'} {mark}{dmark}")
        print("-" * 100)

    n = len(CASES)
    print(f"域命中  {n_dom}/{n} = {n_dom/n:.0%}")
    print(f"导演@1  {n_dir}/{n} = {n_dir/n:.0%}")
    print(f"导演@3  {n_top3}/{n} = {n_top3/n:.0%}")
    print("\n### MOTION_EVAL_DONE")


if __name__ == "__main__":
    main()
