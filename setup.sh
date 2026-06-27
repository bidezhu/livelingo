#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Live Subtitle - 环境安装"
echo "========================================"

# 1. Homebrew
if ! command -v brew &>/dev/null; then
    echo "[..] 安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[OK] Homebrew 已安装"
fi

# 2. Python 3.11
if ! command -v python3.11 &>/dev/null; then
    echo "[..] 安装 Python 3.11..."
    brew install python@3.11
else
    echo "[OK] Python 3.11 已安装"
fi

# 3. Ollama
if ! command -v ollama &>/dev/null; then
    echo "[..] 安装 Ollama..."
    brew install ollama
else
    echo "[OK] Ollama 已安装"
fi

# 4. Start Ollama service
echo "[..] 启动 Ollama 服务..."
ollama serve &>/dev/null &
sleep 3

# 5. Pull translation model
echo "[..] 拉取翻译模型 qwen3.5:9b (首次约6.6GB)..."
ollama pull qwen3.5:9b
echo "[OK] 翻译模型就绪"

# 6. Create venv
if [ ! -d ".venv" ]; then
    echo "[..] 创建 Python 虚拟环境..."
    python3.11 -m venv .venv
fi
source .venv/bin/activate

# 7. Install dependencies
echo "[..] 安装 Python 依赖 (首次较慢)..."
pip install --upgrade pip
pip install torch torchaudio
pip install funasr sounddevice numpy scipy requests

echo ""
echo "========================================"
echo "  安装完成！运行 ./run.sh 启动字幕工具"
echo "========================================"
