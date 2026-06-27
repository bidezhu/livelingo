#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Ollama is running
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "[..] 启动 Ollama 服务..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Activate venv and run
source .venv/bin/activate
python main.py "$@"
