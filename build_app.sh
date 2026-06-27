#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  打包 LiveSubtitle.app"
echo "========================================"

source .venv/bin/activate

echo "[..] 安装 PyInstaller..."
pip install pyinstaller

echo "[..] 打包中..."
pyinstaller \
    --name "LiveSubtitle" \
    --windowed \
    --noconfirm \
    --clean \
    main.py

echo ""
echo "========================================"
echo "  打包完成！"
echo "  应用位置: dist/LiveSubtitle.app"
echo "========================================"
