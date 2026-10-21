"""从视频抽 5 帧。用法： python extract_frames.py <视频路径> [输出目录]"""
import os
import sys


def main():
    import imageio.v3 as iio
    from PIL import Image

    src = sys.argv[1] if len(sys.argv) > 1 else r"D:\下载\生成侯孝贤风格视频.mp4"
    out = sys.argv[2] if len(sys.argv) > 2 else r"F:\llm\bench\frames"
    if not os.path.exists(src):
        print(f"NOT FOUND: {src}")
        sys.exit(1)

    os.makedirs(out, exist_ok=True)
    meta = iio.immeta(src, plugin="FFMPEG")
    print(f"src : {src}")
    print(f"size: {os.path.getsize(src)/2**20:.2f} MB")
    print(f"meta: {meta}")
    fps = meta.get("fps") or 24
    dur = meta.get("duration") or 10
    total = int(fps * dur)

    targets = [int(total * p) for p in (0.05, 0.28, 0.50, 0.72, 0.95)]
    ts = set(targets)
    saved = 0
    for i, fr in enumerate(iio.imiter(src, plugin="FFMPEG")):
        if i in ts:
            img = Image.fromarray(fr)
            p = os.path.join(out, f"v2_{i:04d}.png")
            img.save(p)
            print(f"  saved {p}  {img.size}")
            saved += 1
        if i > max(targets):
            break
    print(f"\n{saved} 帧 -> {out}")
    print("\n### FRAMES_DONE")


if __name__ == "__main__":
    main()
