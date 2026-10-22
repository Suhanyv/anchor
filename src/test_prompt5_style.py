"""测：这条神话史诗分镜的「整体风格块」，我们的系统能不能命名对。"""
import sys

sys.path.insert(0, r"F:\llm\comfyui")
import local_style_hint as N  # noqa: E402

M = r"F:\llm\models\e5-director-c10"
C = r"F:\llm\data\raw\corpus_v10.jsonl"
S = r"F:\llm\data\raw\subjects_v1.jsonl"

node = N.LocalStyleHint()

CASES = [
    # 整体风格块的核心诉求
    ("中国神话史诗电影，巨大的金色佛掌从天而降压向四颗眼球，金色佛光，超广角低机位",
     "整体风格-神力与巨物"),
    ("东方神明雕塑质感，白色丝绸道袍，黑色神牛毛发，体积光，电影级戏剧光影",
     "整体风格-材质与光"),
    ("超高速电影运镜，空间扭曲，环形冲击波，金色经文洪流",
     "整体风格-特效与运镜"),
    # 场景内容
    ("黑暗宇宙虚空中漂浮着四颗巨大的彩色眼球，各自散发不同颜色的混沌能量",
     "场景-混沌巨眼"),
    ("一位僧人和一位老道站在虚空里，僧人穿青灰僧袍手持锡杖，老道骑黑牛穿白道袍",
     "场景-两位神明"),
]

print("=== 神话史诗分镜的风格命名测试 ===")
print(f"{'#':<3} {'题材':<12} {'top1':<26} {'分':>6}  top2 / top3")
print("-" * 104)
for i, (q, tag) in enumerate(CASES, 1):
    out, dbg = node.run(q, M, C, S, "cpu", "视频", "导演/风格聚合", 3, "", False)
    lines = dbg.split("\n")
    subj = lines[1] if len(lines) > 1 else ""
    ranks = [l for l in lines if l.strip()[:1].isdigit()]
    top1 = ranks[0].split(". ")[1][:24] if ranks else "?"
    score = ranks[0].split()[-1] if ranks else "?"
    rest = " | ".join(r.split(". ")[1][:20] for r in ranks[1:3])
    print(f"{i:<3} {tag:<12} {top1:<26} {score:>6}  {rest}")
    if subj:
        print(f"      {subj.strip()}")
print()
print("### P5_RETRIEVE_DONE")
