#!/usr/bin/env bash
# 一键复现：从干净克隆到可用的模型 + 全部基准
#
# 用法：
#   bash src/reproduce.sh              # 只重建模型并做冒烟测试
#   bash src/reproduce.sh --bench      # 额外跑全部基准（约 5 分钟）
#
# 前置：python 3.12 + torch（CUDA 版须从 pytorch 官方索引装）
#      pip install torch --index-url https://download.pytorch.org/whl/cu130
#      pip install -r requirements.txt

set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"
CORPUS="data/raw/corpus_v16.jsonl"
QUERIES="data/raw/queries_v4_fixed16.jsonl"
OUT="models/e5-director-c18"

echo "=== 0. 环境检查 ==="
$PY - <<'EOF'
import sys
print(f"  python {sys.version.split()[0]}")
for p in ("torch", "transformers"):
    try:
        m = __import__(p)
        print(f"  {p:<14} {m.__version__}")
    except ImportError:
        print(f"  {p:<14} 缺失 —— 先 pip install -r requirements.txt")
        sys.exit(1)
EOF

echo
echo "=== 1. 数据检查 ==="
for f in "$CORPUS" "$QUERIES" data/raw/subjects_v4.jsonl \
         data/raw/crafts_v3.jsonl data/raw/materials_v4.jsonl; do
  if [ -f "$f" ]; then
    echo "  有  $f  ($(wc -l < "$f") 行)"
  else
    echo "  缺  $f"; exit 1
  fi
done

echo
echo "=== 2. 重建模型（约 2 分钟 CPU）==="
if [ -d "$OUT" ]; then
  echo "  $OUT 已存在，跳过（删掉可强制重建）"
else
  $PY src/train_embed.py --epochs 6 --batch-size 32 --lr 2e-5 \
      --dev-ratio 0.01 --select-mode final \
      --corpus "$CORPUS" --queries "$QUERIES" --out-dir "$OUT"
fi

echo
echo "=== 3. 冒烟测试：两条 query 应当命中 ==="
$PY - <<'EOF'
import sys, os
sys.path.insert(0, "comfyui")
import local_style_hint as N
node = N.LocalStyleHint()
cases = [
    ("霓虹夜色，慢门，暧昧的感觉", "Wong Kar-wai"),
    ("从树枝后面看过去，前景有草叶遮挡", "Alfred Hitchcock"),
]
ok = 0
for q, want in cases:
    out, dbg = node.run(q, "models/e5-director-c18",
                        "data/raw/corpus_v16.jsonl", "data/raw/subjects_v4.jsonl",
                        "data/raw/crafts_v3.jsonl", "data/raw/materials_v4.jsonl",
                        True, "cpu", "不限", "导演/风格聚合", 1, "", False)
    hit = want.lower() in out.lower()
    ok += hit
    print(f"  [{'OK' if hit else 'FAIL'}] {q[:20]:<22} -> {out[:64]}")
print(f"  {ok}/{len(cases)} 通过")
sys.exit(0 if ok == len(cases) else 1)
EOF

if [ "${1:-}" = "--bench" ]; then
  echo
  echo "=== 4. 全部基准 ==="
  $PY src/eval_scene.py models/e5-director-c18 "$CORPUS"
  $PY src/eval_material.py models/e5-director-c18 "$CORPUS"
  echo "  结果见 bench/*.json"
fi

echo
echo "=== 完成。示例： python src/serve_style.py --port 8848 ==="
