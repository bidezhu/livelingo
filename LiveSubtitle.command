#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    ollama serve &>/dev/null &
    sleep 3
fi

# Run the app
source .venv/bin/activate
python main.py
