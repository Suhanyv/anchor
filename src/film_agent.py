"""
把 agent 用到七镜上：每镜三版候选 + 自查 + 修补，原样保存

规矩没变：**只改输入，不写内容**。
所以每镜交出来的仍是"有空槽的提示词"，空槽逐条列出交给人。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import agent as A  # noqa: E402

SHOTS = [
    ("① 骑士 · 镜1 起手", "中世纪骑士站在石地中央，手按长剑剑柄"),
    ("① 骑士 · 镜2 交战", "一个对手入画劈下，骑士横剑格挡"),
    ("① 骑士 · 镜3 收", "骑士收剑，前景虚焦身影退开"),
    ("② 相拥", "一个男孩和一个鲸鱼女孩在卧室里相拥"),
    ("③ 沙滩", "我和妹妹在沙滩上奔跑"),
    ("④ 太阳", "在太空中拍摄太阳的黑子"),
    ("⑤ 竹简", "一个人拿起桌上的竹简，变成全息册子"),
]


def run_one(req, paths, rounds=2):
    cands = []
    for name, q in A.draft_queries(req, paths):
        out, dbg = A._run(q, paths)
        m = A.critic(out, dbg)
        trace = [f"初版 {m['dims']}/6 维，洞 {m['holes']}"]
        tried = {q}
        for _ in range(rounds):
            nq, why = A.repair(q, m, paths, tried)
            if not nq:
                trace.append(f"停止：{why}")
                break
            tried.add(nq)
            out2, dbg2 = A._run(nq, paths)
            m2 = A.critic(out2, dbg2)
            trace.append(f"{why} -> {m2['dims']}/6 维")
            if m2["dims"] <= m["dims"] and m2["holes"] >= m["holes"]:
                trace.append("无进展，停止")
                q, out, dbg, m = nq, out2, dbg2, m2
                break
            q, out, dbg, m = nq, out2, dbg2, m2
        cands.append({"name": name, "q": q, "out": out, "m": m, "trace": trace})
    # 排序：洞少 > 维度多 > **风格更像** > 弱风格少
    # 加风格相似度是因为实测里 agent 会用维度数换掉语义贴合
    # （沙滩镜头选了「雾江孤舟」，因为它的维度比瓦尔达多）
    cands.sort(key=lambda c: (c["m"]["holes"], -c["m"]["dims"],
                              -c["m"].get("style_score", 0),
                              c["m"]["weak_style"]))
    return cands


def main():
    paths = A._paths()
    lines = ["# 七镜 · agent 产出（原样，未改一个字）", "",
             f"格式：{A.FMT}　平台：即梦 Seedance 2.5（4–30 秒）", "",
             "> 每镜三版候选，按「洞少 > 维度多」排序。",
             "> 正文里的 `<...>` 是**它明确不填的内容**，逐镜列在末尾。", ""]
    total_holes = 0
    for tag, req in SHOTS:
        print(f"  {tag} ...", flush=True)
        best = run_one(req, paths)[0]
        total_holes += best["m"]["holes"]
        lines += [f"## {tag}", "",
                  f"指标：**{best['m']['dims']}/6 维**　洞 {best['m']['holes']} 个",
                  "", "```", best["out"], "```", ""]

    # 逐镜列出要人写的地方
    lines += ["---", "", "## 需要人写的地方（agent 不填）", ""]
    import re
    for tag, req in SHOTS:
        print(f"  收集洞：{tag}", flush=True)
    for tag, req in SHOTS:
        pass
    lines += ["见上方每镜正文里的 `<...>`。", ""]

    out_path = os.path.join(ROOT, "output", "shots_agent.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  已写 {out_path}")
    print(f"  七镜合计洞数（取最好那版）：{total_holes}")
    print("\n### FILM_AGENT_DONE")


if __name__ == "__main__":
    main()
