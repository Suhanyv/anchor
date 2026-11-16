"""
分镜表 v2：每镜可以给一句自己的内容

v1 的错：把"场景句 + 镜头名"直接拼起来，于是
    镜3「…跑，脚下」      景别被"特写"带成"从下巴到头顶"
    镜4 说是空镜，正文却还在跑，结尾还"跟着出画"

原因：细节镜和收尾镜**不是同一个句子的同一个动作**，硬拼必矛盾。
所以：建立/推进 可以从场景句推；细节/收 必须给一句自己的话。
"""
import argparse
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

PLAN = [
    ("建立", "正面推进", 10),
    ("推进", "背面跟拍", 12),
    ("细节", "脚下特写", 8),
    ("收", "空镜收尾", 10),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--lines", default="",
                    help="每镜一句内容，用分号隔开；不给则细节/收 会留空提醒")
    ap.add_argument("--style", default="文人水墨")
    ap.add_argument("--fmt", default="即梦 Seedance 2.5 · 整段（中文）")
    a = ap.parse_args()

    lines = [x.strip() for x in a.lines.split("；") if x.strip()]
    d = N.LocalStyleHint.INPUT_TYPES()["required"]
    M, C = d["模型目录"][1]["default"], d["语料文件"][1]["default"]
    S, K, MT = (d["题材文件"][1]["default"], d["工艺文件"][1]["default"],
                d["材质文件"][1]["default"])
    node = N.LocalStyleHint()

    rows, total, todo = [], 0, []
    for i, (role, st, sec) in enumerate(PLAN):
        content = lines[i] if i < len(lines) else None
        if content is None:
            if role in ("建立", "推进"):
                content = a.scene          # 这两个可以从场景句推
            else:
                todo.append(f"镜{i+1}（{role}·{st}）：需要一句自己的内容")
                continue
        q = f"用{a.style}，{sec} 秒，{content}，{st}"
        out, _ = node.run(q, M, C, S, K, MT, True, "文生视频", False,
                          a.fmt, "cpu", "视频", "导演/风格聚合", 1, "", False)
        cam = next((x.strip() for x in out.split("。")
                    if x.strip().startswith("机位")), "")
        rows.append((i + 1, role, st, sec, cam, out))
        total += sec

    print(f"\n=== 分镜表：{a.scene} ===\n")
    print("| # | 拍次 | 镜头 | 时长 | 机位 |")
    print("|---|---|---|---|---|")
    for n, role, st, sec, cam, _ in rows:
        print(f"| {n} | {role} | {st} | {sec}s | {cam[3:37]} |")
    print(f"\n合计 {total}s")
    if todo:
        print("\n还要补的：")
        for t in todo:
            print("  · " + t)
    print()
    for n, role, st, sec, _, out in rows:
        print(f"--- 镜{n} · {role} · {st} · {sec}s ---")
        print(out)
        print()
    print("### SHOTLIST_DONE")


if __name__ == "__main__":
    main()
