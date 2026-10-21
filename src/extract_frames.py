"""从生成的视频里抽 5 帧，供人工/视觉检查。"""
import os
import sys

SRC = r"D:\下载\生成侯孝贤风格视频.mp4"
OUT = r"F:\llm\bench\frames"


def main():
    import imageio.v3 as iio
    from PIL import Image

    os.makedirs(OUT, exist_ok=True)
    meta = iio.immeta(SRC, plugin="FFMPEG")
    print("meta:", meta)
    fps = meta.get("fps") or 24
    dur = meta.get("duration") or 10
    total = int(fps * dur)
    print(f"fps={fps} duration={dur} -> 估计 {total} 帧")

    targets = [int(total * p) for p in (0.05, 0.28, 0.50, 0.72, 0.95)]
    ts = set(targets)
    saved = 0
    for i, fr in enumerate(iio.imiter(SRC, plugin="FFMPEG")):
        if i in ts:
            img = Image.fromarray(fr)
            p = os.path.join(OUT, f"frame_{i:04d}.png")
            img.save(p)
            print(f"  saved {p}  {img.size}")
            saved += 1
        if i > max(targets):
            break
    print(f"\n共 {saved} 帧 -> {OUT}")
    print("\n### FRAMES_DONE")


if __name__ == "__main__":
    main()
