"""
从 ModelScope 下载 Qwen2.5-3B-Instruct（HF 不通，ModelScope 通）

只下 transformers 直接能用的那几个文件：config / tokenizer / safetensors / index。

用法
----
    python src/fetch_llm.py            # 默认 3B
    python src/fetch_llm.py 1.5B       # 小一号
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"3B": "Qwen/Qwen2.5-3B-Instruct", "1.5B": "Qwen/Qwen2.5-1.5B-Instruct"}
KEEP = (".json", ".safetensors", ".txt")   # 只要这些
UA = "anchor-llm-fetch/1.0"


def api(model, path=""):
    u = (f"https://modelscope.cn/api/v1/models/{model}/repo/files"
         f"?Revision=master&Root={urllib.parse.quote(path)}")
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def download(model, name, dest, size):
    u = (f"https://modelscope.cn/api/v1/models/{model}/repo"
         f"?Revision=master&FilePath={urllib.parse.quote(name)}")
    tmp = dest + ".part"
    have = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    if have >= size and os.path.exists(dest):
        return "跳过"
    # 续传必须带 Range 头：不带的话服务器会把整个文件再发一遍，
    # 追加到 .part 后面，文件直接被写坏。（这个坑踩过一次）
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(u, headers=headers)
    mode = "ab" if have else "wb"
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, mode) as f:
        done = have
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if done // (200 << 20) != (done - len(chunk)) // (200 << 20):
                print(f"      {done / 1e6:.0f} / {size / 1e6:.0f} MB", flush=True)
    os.replace(tmp, dest)
    return "完成"


def main():
    key = (sys.argv[1] if len(sys.argv) > 1 else "3B").upper()
    model = MODELS.get(key, MODELS["3B"])
    dest = os.path.join(ROOT, "models", f"llm-qwen25-{key.lower()}")
    os.makedirs(dest, exist_ok=True)
    print(f"=== {model} -> {dest} ===")

    data = api(model)
    files = [f for f in data["Data"]["Files"]
             if f["Name"].endswith(KEEP) and f.get("Size", 0) > 0]
    total = sum(f["Size"] for f in files)
    print(f"  {len(files)} 个文件，合计 {total / 1e9:.2f} GB\n")

    t0 = time.time()
    for f in files:
        name, size = f["Name"], f["Size"]
        p = os.path.join(dest, name)
        if os.path.exists(p) and os.path.getsize(p) == size:
            print(f"  [已有] {name}")
            continue
        print(f"  [下载] {name}  {size / 1e6:.0f} MB")
        try:
            print(f"    {download(model, name, p, size)}")
        except Exception as e:  # noqa: BLE001
            print(f"    失败: {type(e).__name__}: {e}")
            continue

    got = sum(os.path.getsize(os.path.join(dest, f["Name"]))
              for f in files if os.path.exists(os.path.join(dest, f["Name"])))
    print(f"\n  完成 {got / 1e9:.2f} / {total / 1e9:.2f} GB，用时 {(time.time()-t0)/60:.1f} 分钟")
    print("\n### LLM_FETCH_DONE")


if __name__ == "__main__":
    main()
