#!/usr/bin/env python3
"""Build a self-contained macOS .app bundle for LiveLingo."""
import os
import shutil
import plistlib
import glob

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "LiveLingo"
APP_PATH = os.path.join(PROJECT_DIR, f"{APP_NAME}.app")
ICON_PATH = os.path.join(PROJECT_DIR, "LiveLingo.icns")

PY_FILES = [
    "launcher.py", "main.py", "asr_engine.py", "translator.py",
    "audio_capture.py", "subtitle_ui.py", "device_selector.py",
    "settings_panel.py", "config.py",
]


def build():
    if os.path.exists(APP_PATH):
        shutil.rmtree(APP_PATH)

    contents = os.path.join(APP_PATH, "Contents")
    macos_dir = os.path.join(contents, "MacOS")
    resources = os.path.join(contents, "Resources")
    app_dir = os.path.join(resources, "app")
    os.makedirs(macos_dir)
    os.makedirs(resources)
    os.makedirs(app_dir)

    # Copy icon
    if os.path.exists(ICON_PATH):
        shutil.copy2(ICON_PATH, os.path.join(resources, f"{APP_NAME}.icns"))

    # Copy Python source files
    for f in PY_FILES:
        src = os.path.join(PROJECT_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(app_dir, f))

    # Write default config if not exists
    import json
    default_config = {
        "api_key": "",
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
        "device_id": None,
        "device_name": None,
    }
    with open(os.path.join(app_dir, "default_config.json"), "w") as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

    # Write Info.plist
    plist = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": f"com.bidezhu.{APP_NAME.lower()}",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        "LSMinimumSystemVersion": "14.0",
        "NSMicrophoneUsageDescription": "LiveLingo 需要麦克风权限来进行实时语音识别。",
        "NSHighResolutionCapable": True,
    }
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(plist, f)

    # Write PkgInfo
    with open(os.path.join(contents, "PkgInfo"), "w") as f:
        f.write("APPL????")

    # Resolve Tcl/Tk path
    venv_python = os.path.join(PROJECT_DIR, ".venv", "bin", "python")
    real_python = os.path.realpath(venv_python)
    python_base = os.path.dirname(os.path.dirname(real_python))
    tcl_dirs = glob.glob(os.path.join(python_base, "lib", "tcl*"))
    tk_dirs = glob.glob(os.path.join(python_base, "lib", "tk*"))
    tcl_dir = tcl_dirs[0] if tcl_dirs else ""
    tk_dir = tk_dirs[0] if tk_dirs else ""

    # Write main executable
    exec_script = f'''#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_RESOURCES="$APP_DIR/../Resources/app"
USER_DIR="$HOME/.livelingo"

mkdir -p "$USER_DIR"

# Copy source files to user dir
cp "$APP_RESOURCES"/*.py "$USER_DIR/" 2>/dev/null

# Copy default config if not exists
if [ ! -f "$USER_DIR/config.json" ]; then
    cp "$APP_RESOURCES/default_config.json" "$USER_DIR/config.json"
fi

# Find Python
PYTHON=""
for p in python3.11 python3.12 python3.13 python3; do
    if command -v $p &>/dev/null; then
        VER=$($p -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        if [ "$VER" -ge 11 ] 2>/dev/null; then
            PYTHON=$p
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "需要 Python 3.11+\\n\\n请先安装:\\nbrew install python@3.11\\n\\n或从 python.org 下载" buttons {{"OK"}} default button "OK" with icon stop with title "LiveLingo"'
    exit 1
fi

# Create venv if needed
if [ ! -f "$USER_DIR/.venv/bin/python" ]; then
    osascript -e 'display notification "首次运行，正在安装依赖..." with title "LiveLingo"' 2>/dev/null
    $PYTHON -m venv "$USER_DIR/.venv"
    source "$USER_DIR/.venv/bin/activate"
    pip install --upgrade pip -q
    pip install openai sounddevice numpy requests dashscope -q 2>&1 | tail -1
fi

# Resolve Tcl/Tk
VENV_PY="$USER_DIR/.venv/bin/python"
REAL_PY=$(readlink -f "$VENV_PY" 2>/dev/null || python3 -c "import os; print(os.path.realpath('$VENV_PY'))")
PY_BASE=$(dirname $(dirname "$REAL_PY"))
TCL_DIR=$(ls -d "$PY_BASE"/lib/tcl* 2>/dev/null | head -1)
TK_DIR=$(ls -d "$PY_BASE"/lib/tk* 2>/dev/null | head -1)
[ -n "$TCL_DIR" ] && export TCL_LIBRARY="$TCL_DIR"
[ -n "$TK_DIR" ] && export TK_LIBRARY="$TK_DIR"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:$PATH"

# Run
cd "$USER_DIR"
"$VENV_PY" launcher.py > /tmp/livelingo.log 2>&1 &
PID=$!

sleep 3
if ! kill -0 $PID 2>/dev/null; then
    ERROR=$(tail -3 /tmp/livelingo.log 2>/dev/null | head -c 200)
    osascript -e "display dialog \\"启动失败:\\n$ERROR\\" buttons {{\\"OK\\"}} default button \\"OK\\" with icon stop with title \\"LiveLingo\\"" 2>/dev/null
fi
'''

    exec_path = os.path.join(macos_dir, APP_NAME)
    with open(exec_path, "w") as f:
        f.write(exec_script)
    os.chmod(exec_path, 0o755)

    print(f"Built: {APP_PATH}")
    print(f"Icon: {'Yes' if os.path.exists(os.path.join(resources, f'{APP_NAME}.icns')) else 'No'}")
    print(f"App files: {len(os.listdir(app_dir))} files")


if __name__ == "__main__":
    build()
