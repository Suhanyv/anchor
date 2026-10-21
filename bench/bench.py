"""
本机训练能力基准测试 —— RTX 4060 Laptop 8GB / i7-12650H / 16GB
目标：把"embedding + reranker 能不能流畅训练"从估算换成实测。

测量项：
  1. matmul 有效算力 (bf16 / fp16 / fp32, 1024~8192)
  2. 显存带宽 (copy read+write)
  3. 编码器训练吞吐 (MiniLM 级 / BERT-base 级, 多种 seq×bs)
  4. 显存峰值 & 系统内存峰值（8GB / 16GB 两道墙）
  5. 持续满载 60s 的热降频曲线（笔记本关键指标）
"""
import ctypes
import gc
import json
import os
import statistics
import subprocess
import sys
import time

import torch
import torch.nn as nn

OUT_DIR = r"F:\llm\bench"
os.makedirs(OUT_DIR, exist_ok=True)

VOCAB = 30522
RESULTS = {}


# ---------------------------------------------------------------- 工具
def smi(field):
    try:
        out = subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={field}", "--format=csv,noheader,nounits"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        return [x.strip() for x in out.strip().splitlines()]
    except Exception:
        return None


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def ram_gb():
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullTotalPhys / 2**30, m.ullAvailPhys / 2**30


def vram_gb():
    free, total = torch.cuda.mem_get_info()
    return total / 2**30, free / 2**30


def hline(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


# ---------------------------------------------------------------- 0. 设备
hline("0. 设备信息")
torch.backends.cudnn.benchmark = True
dev = torch.cuda.get_device_name(0)
cap = torch.cuda.get_device_capability(0)
props = torch.cuda.get_device_properties(0)
tot_ram, avail_ram = ram_gb()
vg_total, vg_free = vram_gb()

print(f"GPU           : {dev}")
print(f"compute cap   : {cap[0]}.{cap[1]}  SMs={props.multi_processor_count}")
print(f"显存          : {vg_total:.2f} GB total, {vg_free:.2f} GB free")
print(f"torch         : {torch.__version__}   cuda={torch.version.cuda}  cudnn={torch.backends.cudnn.version()}")
print(f"bf16 支持     : {torch.cuda.is_bf16_supported()}")
print(f"系统内存      : {tot_ram:.1f} GB total, {avail_ram:.1f} GB free")
RESULTS["device"] = {
    "gpu": dev, "capability": list(cap), "sms": props.multi_processor_count,
    "vram_total_gb": round(vg_total, 2), "torch": torch.__version__,
    "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
    "bf16": torch.cuda.is_bf16_supported(),
    "ram_total_gb": round(tot_ram, 1),
}


# ---------------------------------------------------------------- 1. matmul
hline("1. matmul 有效算力 (TFLOPS)")
print(f"{'dtype':>10} {'size':>6} {'TFLOPS':>9}")


def bench_matmul(dtype, n, warmup=5, iters=20):
    a = torch.randn(n, n, device="cuda", dtype=dtype)
    b = torch.randn(n, n, device="cuda", dtype=dtype)
    for _ in range(warmup):
        torch.mm(a, b)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        torch.mm(a, b)
    torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / iters
    del a, b
    gc.collect(); torch.cuda.empty_cache()
    return 2 * n**3 / dt / 1e12


matmul_res = {}
for dtype, label in [(torch.bfloat16, "bf16"), (torch.float16, "fp16"), (torch.float32, "fp32")]:
    matmul_res[label] = {}
    for n in (1024, 2048, 4096, 8192):
        need = 2 * n * n * torch.finfo(dtype).bits / 8 / 2**30
        if need > 5.0:          # 8GB 卡上留余量
            print(f"{label:>10} {n:>6} {'skip(too big)':>9}")
            continue
        try:
            tf = bench_matmul(dtype, n)
            matmul_res[label][n] = round(tf, 2)
            print(f"{label:>10} {n:>6} {tf:>9.2f}")
        except RuntimeError as e:
            print(f"{label:>10} {n:>6} {'OOM':>9}")
            gc.collect(); torch.cuda.empty_cache()
RESULTS["matmul_tflops"] = matmul_res
peak_compute = max((v for d in matmul_res.values() for v in d.values()), default=0)


# ---------------------------------------------------------------- 2. 带宽
hline("2. 显存带宽 (GB/s)")


def bench_membw(mb=512, iters=30):
    n = mb * 1024 * 1024 // 4
    a = torch.empty(n, device="cuda", dtype=torch.float32)
    b = torch.empty_like(a)
    a.fill_(1.0)
    torch.cuda.synchronize()
    for _ in range(5):
        b.copy_(a)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        b.copy_(a)
    torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / iters
    moved = a.numel() * 4 * 2      # 读 + 写
    del a, b
    gc.collect(); torch.cuda.empty_cache()
    return moved / dt / 1e9


try:
    bw = bench_membw()
    print(f"copy 512MB read+write : {bw:.1f} GB/s")
    RESULTS["mem_bw_gbs"] = round(bw, 1)
except RuntimeError:
    print("bandwidth test OOM")
    RESULTS["mem_bw_gbs"] = None


# ---------------------------------------------------------------- 3. 编码器
hline("3. 编码器训练吞吐 (fwd+bwd, bf16 autocast)")


class Encoder(nn.Module):
    """BERT 风格编码器 + mean pooling，用于 embedding / reranker 训练基准。"""

    def __init__(self, layers, hidden, heads, maxlen=512, ffn_mult=4):
        super().__init__()
        self.tok = nn.Embedding(VOCAB, hidden)
        self.pos = nn.Embedding(maxlen, hidden)
        layer = nn.TransformerEncoderLayer(
            d_model=hidden, nhead=heads, dim_feedforward=hidden * ffn_mult,
            batch_first=True, activation="gelu", norm_first=True,
        )
        self.enc = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(hidden)
        self.head = nn.Linear(hidden, hidden)

    def forward(self, ids):
        h = self.tok(ids) + self.pos(torch.arange(ids.size(1), device=ids.device))
        h = self.enc(h)
        h = self.norm(h.mean(dim=1))
        return self.head(h)

    def n_params(self):
        return sum(p.numel() for p in self.parameters())


def bench_train(layers, hidden, heads, seq, bs, steps=8, warmup=3, tag=""):
    """返回 step_time / samples_per_s / tokens_per_s / peak_vram / ram_delta。"""
    gc.collect(); torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    _, avail_before = ram_gb()

    model = Encoder(layers, hidden, heads, maxlen=seq).cuda().train()
    n_par = model.n_params()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ids = torch.randint(0, VOCAB, (bs, seq), device="cuda")
    tgt = torch.randn(bs, hidden, device="cuda")
    lossf = nn.MSELoss()

    def one():
        opt.zero_grad(set_to_none=True)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = model(ids)
            loss = lossf(out.float(), tgt)
        loss.backward()
        opt.step()

    for _ in range(warmup):
        one()
    torch.cuda.synchronize()

    t0 = time.perf_counter()
    for _ in range(steps):
        one()
    torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / steps

    peak = torch.cuda.max_memory_allocated() / 2**30
    _, avail_after = ram_gb()
    ram_delta = avail_before - avail_after

    del model, opt, ids, tgt
    gc.collect(); torch.cuda.empty_cache()

    return {
        "tag": tag, "layers": layers, "hidden": hidden, "heads": heads,
        "params_m": round(n_par / 1e6, 1),
        "seq": seq, "bs": bs,
        "step_s": round(dt, 4),
        "samples_s": round(bs / dt, 1),
        "tokens_s": round(bs * seq / dt, 0),
        "peak_vram_gb": round(peak, 2),
        "ram_delta_gb": round(ram_delta, 2),
    }


# 待测配置：(层数, 隐藏, 头数, seq, batch, 说明)
CONFIGS = [
    (6,  384, 6,  256, 64, "MiniLM-6L  嵌入"),
    (6,  384, 6,  256, 128, "MiniLM-6L  嵌入(大batch)"),
    (12, 768, 12, 256, 32, "BERT-base  嵌入"),
    (12, 768, 12, 256, 64, "BERT-base  嵌入(大batch)"),
    (12, 768, 12, 512, 16, "BERT-base  reranker"),
    (12, 768, 12, 512, 32, "BERT-base  reranker(大batch)"),
]

train_res = []
print(f"{'config':<26} {'param':>7} {'seq':>4} {'bs':>4} {'step':>7} {'samp/s':>8} {'tok/s':>9} {'VRAM':>6}")
for layers, hidden, heads, seq, bs, tag in CONFIGS:
    try:
        r = bench_train(layers, hidden, heads, seq, bs, tag=tag)
        train_res.append(r)
        print(f"{tag:<26} {r['params_m']:>7.1f} {seq:>4} {bs:>4} "
              f"{r['step_s']:>7.3f} {r['samples_s']:>8.1f} {r['tokens_s']:>9.0f} "
              f"{r['peak_vram_gb']:>6.2f}")
    except RuntimeError as e:
        msg = "OOM" if "out of memory" in str(e).lower() else str(e)[:40]
        print(f"{tag:<26} {'.':>7} {seq:>4} {bs:>4} {'--':>7} {'--':>8} {'--':>9} {msg:>6}")
        gc.collect(); torch.cuda.empty_cache()
RESULTS["train"] = train_res


# ---------------------------------------------------------------- 4. 热降频
hline("4. 持续满载 60s 热降频曲线")
print(f"{'t(s)':>5} {'TFLOPS':>8} {'温度C':>6} {'功耗W':>7} {'显存GB':>7}")

n = 4096
aa = torch.randn(n, n, device="cuda", dtype=torch.bfloat16)
bb = torch.randn(n, n, device="cuda", dtype=torch.bfloat16)
for _ in range(10):
    torch.mm(aa, bb)
torch.cuda.synchronize()

sustain = []
t_start = time.perf_counter()
win_t0 = t_start
win_iters = 0
while True:
    torch.mm(aa, bb)
    win_iters += 1
    now = time.perf_counter()
    if now - win_t0 >= 10.0:
        elapsed = now - t_start
        tf = win_iters * 2 * n**3 / (now - win_t0) / 1e12
        temp = smi("temperature.gpu")
        power = smi("power.draw")
        vg = torch.cuda.memory_allocated() / 2**30
        temp = temp[0] if temp else "?"
        power = power[0] if power else "?"
        print(f"{elapsed:>5.0f} {tf:>8.2f} {temp:>6} {power:>7} {vg:>7.2f}")
        sustain.append({"t_s": round(elapsed), "tflops": round(tf, 2),
                        "temp_c": temp, "power_w": power})
        win_t0 = now; win_iters = 0
    if now - t_start >= 60.0:
        break
torch.cuda.synchronize()
del aa, bb
gc.collect(); torch.cuda.empty_cache()

if len(sustain) >= 2:
    first, last = sustain[0]["tflops"], sustain[-1]["tflops"]
    drop = (first - last) / first * 100
    print(f"\n首个窗口 {first:.2f} → 末个窗口 {last:.2f} TFLOPS，衰减 {drop:+.1f}%")
    RESULTS["sustain"] = {"windows": sustain, "drop_pct": round(drop, 1)}
else:
    RESULTS["sustain"] = {"windows": sustain}


# ---------------------------------------------------------------- 5. 结论
hline("5. 汇总")

summary = {}
for r in train_res:
    summary[f"L{r['layers']}_H{r['hidden']}_s{r['seq']}_b{r['bs']}"] = r

RESULTS["summary"] = summary
RESULTS["peak_compute_tflops"] = peak_compute
RESULTS["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=2)

print(f"峰值 matmul 算力 : {peak_compute:.2f} TFLOPS")
print(f"显存带宽         : {RESULTS.get('mem_bw_gbs')} GB/s")
print(f"结果已存         : {os.path.join(OUT_DIR, 'results.json')}")
print("\n### BENCH_DONE")
