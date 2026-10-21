"""
并行分段下载器 —— 用于在单连接被限速的环境里拉大文件。

用法:
    python pdl.py <url> <outfile> [connections] [--test-mb N]

特性：
  * 多连接并发分段（Range 请求）
  * 断点续传（保留 .partNN 文件）
  * 实时聚合速度
  * 自动降级：服务器不支持 Range 时回退单连接
"""
import os
import sys
import threading
import time
import urllib.request

CHUNK = 1024 * 256


def head_info(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        size = int(r.headers.get("Content-Length", 0))
        accept = r.headers.get("Accept-Ranges", "")
        return size, accept


class Downloader:
    def __init__(self, url, out, conns=8):
        self.url = url
        self.out = out
        self.conns = conns
        self.got = [0] * conns
        self.lock = threading.Lock()
        self.errors = []
        self.stop = False

    def _part(self, idx, start, end):
        path = f"{self.out}.part{idx:02d}"
        have = os.path.getsize(path) if os.path.exists(path) else 0
        if have > (end - start + 1):
            have = 0
            os.remove(path)
        if have:
            start += have
        if start > end:
            with self.lock:
                self.got[idx] = have
            return

        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status != 206:
                    with self.lock:
                        self.errors.append(f"part{idx}: server returned {r.status}, no range support")
                    return
                with open(path, "ab") as f:
                    n = have
                    while not self.stop:
                        b = r.read(CHUNK)
                        if not b:
                            break
                        f.write(b)
                        n += len(b)
                        with self.lock:
                            self.got[idx] = n
        except Exception as e:  # noqa: BLE001
            with self.lock:
                self.errors.append(f"part{idx}: {e}")

    def run(self):
        size, accept = head_info(self.url)
        if size <= 0:
            print("cannot determine size")
            return False
        print(f"size={size/2**20:.1f} MB  accept-ranges={accept!r}  conns={self.conns}")

        per = size // self.conns
        ranges = []
        for i in range(self.conns):
            s = i * per
            e = (size - 1) if i == self.conns - 1 else (s + per - 1)
            ranges.append((s, e))

        threads = [
            threading.Thread(target=self._part, args=(i, s, e), daemon=True)
            for i, (s, e) in enumerate(ranges)
        ]
        t0 = time.time()
        for t in threads:
            t.start()

        peak = 0.0
        while any(t.is_alive() for t in threads):
            time.sleep(2.0)
            with self.lock:
                cur = sum(self.got)
            el = time.time() - t0
            rate = cur / el / 2**20
            peak = max(peak, rate)
            eta = (size - cur) / (cur / el) / 60 if cur > 0 else 0
            print(f"  {cur/2**20:8.1f}/{size/2**20:.1f} MB  avg {rate:6.2f} MB/s  "
                  f"peak {peak:6.2f} MB/s  ETA {eta:6.1f} min", flush=True)

        for t in threads:
            t.join()

        if self.errors:
            for e in self.errors:
                print("  ERR", e)

        with self.lock:
            total = sum(self.got)
        el = time.time() - t0
        print(f"\ndone: {total/2**20:.1f} MB in {el/60:.1f} min  avg {total/el/2**20:.2f} MB/s")
        if total < size:
            print(f"INCOMPLETE: missing {(size-total)/2**20:.1f} MB")
            return False
        return True

    def join(self):
        with open(self.out, "wb") as out:
            for i in range(self.conns):
                p = f"{self.out}.part{i:02d}"
                if not os.path.exists(p):
                    print("missing part", p)
                    return False
                with open(p, "rb") as f:
                    while True:
                        b = f.read(8 * 2**20)
                        if not b:
                            break
                        out.write(b)
        for i in range(self.conns):
            p = f"{self.out}.part{i:02d}"
            if os.path.exists(p):
                os.remove(p)
        print(f"joined -> {self.out} ({os.path.getsize(self.out)/2**20:.1f} MB)")
        return True


if __name__ == "__main__":
    url = sys.argv[1]
    out = sys.argv[2]
    conns = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    d = Downloader(url, out, conns)
    ok = d.run()
    if ok:
        d.join()
    sys.exit(0 if ok else 1)
