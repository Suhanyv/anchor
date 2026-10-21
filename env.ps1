# ============================================================
#  环境变量 —— 用法：  . F:\llm\env.ps1
#  所有缓存/临时文件都指向 F 盘，C 盘零占用
# ============================================================

$env:HF_ENDPOINT   = 'https://hf-mirror.com'   # HuggingFace 国内镜像，必须设
$env:HF_HOME       = 'F:\llm\cache\hf'
$env:TORCH_HOME    = 'F:\llm\cache\torch'
$env:PIP_CACHE_DIR = 'F:\llm\cache\pip'
$env:TEMP          = 'F:\llm\temp'
$env:TMP      = 'F:\llm\temp'
$env:PYTHONUTF8    = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:TOKENIZERS_PARALLELISM = 'false'          # 避免 DataLoader 与 tokenizer 抢线程

# 可选：如果你的 FlClash 有可用节点，取消下面两行注释走代理
# $env:HTTP_PROXY  = 'http://127.0.0.1:7890'
# $env:HTTPS_PROXY = 'http://127.0.0.1:7890'

Write-Host 'env loaded:' -ForegroundColor Green
Write-Host "  HF_ENDPOINT = $env:HF_ENDPOINT"
Write-Host "  HF_HOME     = $env:HF_HOME"
Write-Host "  TEMP        = $env:TEMP"
