"""
查询域路由器：判断用户要「静态图」还是「视频」

设计原则
--------
**宁可判成 any，不要判错。** 判成 any 只是不做过滤（退化成现状），
判错会把正确答案整个过滤掉，比不过滤更糟。

所以规则是看信号是否**单向**：
  只有视频词  -> video
  只有图片词  -> image
  两者都有 / 都没有 -> any
"""
VIDEO_HINTS = [
    "视频", "运镜", "镜头运动", "动起来", "时长", "几秒", "秒钟", "秒的",
    "推镜", "拉镜", "摇镜", "移镜", "跟拍", "环绕", "升镜", "降镜", "甩镜",
    "sora", "可灵", "即梦", "runway", "veo", "kling", "pika", "海螺", "hailuo",
    "一镜到底", "转场", "慢动作", "升格", "逐帧", "镜头缓缓", "镜头推",
]
# 明确的静态/图片词（无歧义）
IMAGE_HINTS = [
    "图片", "照片", "静帧", "静态", "海报", "壁纸", "插画", "原画", "立绘",
    "出图", "一张图", "一张", "封面", "截图", "构图", "分辨率",
    "4k", "8k画质", "竖版图", "横版图", "画一张", "渲染图", "图生图", "动漫",
    "midjourney", "mj", "stable diffusion", "flux", "即梦图片", "niji",
]
# 「画面」有歧义：单独出现偏静态，但和运动词一起就是视频语境
AMBIG_STILL = ["画面", "镜头", "构图感"]
MOTION_WORDS = [
    "慢", "动", "推", "摇", "移", "跟", "环绕", "升", "降", "甩", "转",
    "秒", "帧", "切", "长镜", "手持", "漂", "运镜",
]


def detect(text):
    t = (text or "").lower()
    v = sum(1 for w in VIDEO_HINTS if w.lower() in t)
    i = sum(1 for w in IMAGE_HINTS if w.lower() in t)

    # 歧义词单独处理：有「画面」类词、但没有任何运动词，才计为静态
    if i == 0:
        still_hits = sum(1 for w in AMBIG_STILL if w in t)
        motion_hits = sum(1 for w in MOTION_WORDS if w in t)
        if still_hits and motion_hits == 0:
            i = 1

    if v and not i:
        return "prompt_video"
    if i and not v:
        return "prompt_image"
    return "any"


if __name__ == "__main__":
    tests = [
        "远远的镜头，一条草船在江上，有个老渔夫在划",
        "想做个草船的视频，运镜怎么描述",
        "草船的画面，出一张图",
        "草船 5 秒视频，镜头缓缓推近",
        "霓虹夜色，慢门，暧昧的感觉",
        "想要黑泽明那种色彩鲜艳的海报",
        "年画那种大红大绿",
        "sora 里怎么做一镜到底",
        "构图只有一点点东西",
        "草船的图片和视频都要",
    ]
    print("=== 路由测试 ===")
    for t in tests:
        print(f"  {detect(t):<14} <- {t}")
    print("\n### DOMAIN_ROUTER_DONE")
