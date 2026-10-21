"""
Patch missing bytes per chunk, join, and verify SHA256.

Only requests the missing byte ranges - far cheaper than re-downloading 1.8 GB.
"""
import hashlib
import os
import sys
import time
import urllib.request

URL = 'https://mirrors.aliyun.com/pytorch-wheels/cu130/torch-2.9.1%2Bcu130-cp312-cp312-win_amd64.whl'
OUT = r'F:\llm\downloads\torch-2.9.1-cu130-cp312-win_amd64.whl'
EXPECTED = 1862081240
SHA256 = 'cd3232a562ad2a2699d48130255e1b24c07dfe694a40dcd24fad683c752de121'
N = 8

per = EXPECTED // N
parts = [f'{OUT}.part{i:02d}' for i in range(N)]


def fetch_once(start, end, path):
    """Request [start..end] and append. Returns bytes written (may be short)."""
    req = urllib.request.Request(URL, headers={'Range': f'bytes={start}-{end}'})
    written = 0
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status != 206:
            raise RuntimeError(f'server returned {r.status}, Range not honored')
        with open(path, 'ab') as f:
            while True:
                b = r.read(1 << 18)
                if not b:
                    break
                f.write(b)
                written += len(b)
    return written


def fill_to(path, base_start, target_size, label):
    """Keep fetching until the part file reaches target_size."""
    have = os.path.getsize(path) if os.path.exists(path) else 0
    if have > target_size:
        with open(path, 'r+b') as f:
            f.truncate(target_size)
        have = target_size

    stall = 0
    while have < target_size:
        end = base_start + target_size - 1
        start_req = base_start + have
        want = end - start_req + 1
        try:
            got = fetch_once(start_req, end, path)
        except Exception as e:  # noqa: BLE001
            print(f'    {label}: error {e}')
            got = 0
        new_have = os.path.getsize(path)
        print(f'    {label}: requested {want:,}, got {new_have-have:,}, now {new_have:,}/{target_size:,}')
        if got == 0 or new_have <= have:
            stall += 1
            if stall >= 8:
                print(f'    {label}: STALLED after 8 empty attempts')
                return False
            time.sleep(2 * stall)
        else:
            stall = 0
        have = new_have
    return True


print('=== 1. inspect / patch chunks ===')
for i in range(N):
    p = parts[i]
    start = i * per
    end = EXPECTED - 1 if i == N - 1 else start + per - 1
    want = end - start + 1
    have = os.path.getsize(p) if os.path.exists(p) else 0

    if have == want:
        print(f'  part{i:02d}: OK ({have:,})')
        continue

    print(f'  part{i:02d}: {have:,} / {want:,}  (short {want-have:,})')
    if not fill_to(p, start, want, f'part{i:02d}'):
        sys.exit(1)

total = sum(os.path.getsize(p) for p in parts)
print(f'\ntotal: {total:,}  expected: {EXPECTED:,}  diff: {total-EXPECTED:,}')
if total != EXPECTED:
    print('### STILL MISMATCHED')
    sys.exit(1)

print('\n=== 2. join ===')
with open(OUT, 'wb') as dst:
    for p in parts:
        with open(p, 'rb') as src:
            while True:
                b = src.read(8 << 20)
                if not b:
                    break
                dst.write(b)
print(f'joined: {os.path.getsize(OUT):,} bytes')

print('\n=== 3. sha256 verify ===')
h = hashlib.sha256()
with open(OUT, 'rb') as f:
    while True:
        b = f.read(8 << 20)
        if not b:
            break
        h.update(b)
got = h.hexdigest()
print(f'  got      : {got}')
print(f'  expected : {SHA256}')
if got != SHA256:
    print('### SHA256 MISMATCH - file corrupted')
    sys.exit(1)
print('  OK sha256 matches')

print('\n=== 4. cleanup chunks ===')
for p in parts:
    if os.path.exists(p):
        os.remove(p)

print('\n### PATCH_JOIN_OK')
