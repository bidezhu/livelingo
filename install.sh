#!/bin/bash
set -e
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     LiveLingo 安装向导               ║"
echo "  ║     中英双语实时字幕工具             ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check/install Python 3.11
if command -v python3.11 &>/dev/null; then
    PYTHON=python3.11
    echo "[OK] Python 3.11 已安装"
elif command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$PY_VER" == "3.11" || "$PY_VER" == "3.12" || "$PY_VER" == "3.13" ]]; then
        PYTHON=python3
        echo "[OK] Python $PY_VER 已安装"
    else
        echo "[..] 安装 Python 3.11..."
        if command -v brew &>/dev/null; then
            brew install python@3.11
            PYTHON=python3.11
        else
            echo "请先安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "然后运行: brew install python@3.11"
            exit 1
        fi
    fi
else
    echo "未找到 Python，请先安装 Homebrew 再运行此脚本"
    exit 1
fi

# 2. Create venv
if [ ! -d ".venv" ]; then
    echo "[..] 创建虚拟环境..."
    $PYTHON -m venv .venv
    echo "[OK] 虚拟环境已创建"
else
    echo "[OK] 虚拟环境已存在"
fi

# 3. Install dependencies
echo "[..] 安装依赖 (首次较慢)..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install openai sounddevice numpy requests dashscope -q
echo "[OK] 依赖安装完成"

# 4. Configure API Key
if [ ! -f "config.json" ]; then
    echo ""
    echo "请输入百炼 API Key (从 bailian.console.aliyun.com 获取):"
    read -r API_KEY
    cat > config.json << EOF
{
  "api_key": "$API_KEY",
  "asr_model": "fun-asr-realtime",
  "translate_model": "qwen-plus",
  "sample_rate": 16000,
  "font_size_cn": 28,
  "font_size_en": 20,
  "max_subtitle_lines": 4,
  "window_height": 220,
  "silence_timeout": 1.5,
  "bg_color": "#1a1a1a",
  "text_color_cn": "#FFFFFF",
  "text_color_en": "#BBBBBB",
  "text_color_partial": "#888888",
  "device_id": null,
  "device_name": null
}
EOF
    echo "[OK] 配置已保存"
else
    echo "[OK] 配置文件已存在"
fi

# 5. Build .app
echo "[..] 生成 LiveLingo.app..."
python3 build_app.py
echo "[OK] LiveLingo.app 已生成"

echo ""
echo "  ══════════════════════════════════════"
echo "  安装完成！双击 LiveLingo.app 即可使用"
echo "  ══════════════════════════════════════"
echo ""
