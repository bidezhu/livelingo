#!/usr/bin/env python3
"""Build a proper macOS .app bundle for LiveLingo."""
import os
import shutil
import subprocess
import plistlib

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "LiveLingo"
APP_PATH = os.path.join(PROJECT_DIR, f"{APP_NAME}.app")
ICON_PATH = os.path.join(PROJECT_DIR, "LiveLingo.icns")


def build():
    if os.path.exists(APP_PATH):
        shutil.rmtree(APP_PATH)

    # Create .app directory structure
    contents = os.path.join(APP_PATH, "Contents")
    macos_dir = os.path.join(contents, "MacOS")
    resources = os.path.join(contents, "Resources")
    os.makedirs(macos_dir)
    os.makedirs(resources)

    # Copy icon
    if os.path.exists(ICON_PATH):
        shutil.copy2(ICON_PATH, os.path.join(resources, f"{APP_NAME}.icns"))

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
        "NSMicrophoneUsageDescription": "LiveLingo needs microphone access for real-time speech recognition.",
        "NSHighResolutionCapable": True,
        "LSUIElement": False,
    }
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(plist, f)

    # Write main executable shell script
    exec_script = f'''#!/bin/bash
# LiveLingo - Real-time Bilingual Subtitle Tool
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$APP_DIR/../../.." && pwd)"

# Find venv python
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    osascript -e 'display dialog "Python virtual environment not found.\\nPlease run setup.sh first." buttons {{"OK"}} default button "OK" with icon stop with title "LiveLingo"'
    exit 1
fi

# Setup Tcl/Tk for Python
PYTHON_DIR=$(dirname $(dirname "$VENV_PYTHON"))
TCL_DIR=$(ls -d "$PYTHON_DIR"/lib/tcl* 2>/dev/null | head -1)
TK_DIR=$(ls -d "$PYTHON_DIR"/lib/tk* 2>/dev/null | head -1)
[ -n "$TCL_DIR" ] && export TCL_LIBRARY="$TCL_DIR"
[ -n "$TK_DIR" ] && export TK_LIBRARY="$TK_DIR"

# Setup PATH
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:$PATH"

# Log file
LOG="/tmp/livelingo.log"

# Run launcher
cd "$PROJECT_DIR"
"$VENV_PYTHON" launcher.py > "$LOG" 2>&1 &
PID=$!

# Wait briefly, check if it crashed
sleep 2
if ! kill -0 $PID 2>/dev/null; then
    ERROR=$(tail -5 "$LOG" 2>/dev/null)
    osascript -e "display dialog \\"LiveLingo failed to start:\\n$ERROR\\" buttons {{\\"OK\\"}} default button \\"OK\\" with icon stop with title \\"LiveLingo\\"" 2>/dev/null
fi
'''

    exec_path = os.path.join(macos_dir, APP_NAME)
    with open(exec_path, "w") as f:
        f.write(exec_script)
    os.chmod(exec_path, 0o755)

    # Write PkgInfo
    with open(os.path.join(contents, "PkgInfo"), "w") as f:
        f.write("APPL????")

    print(f"Built: {APP_PATH}")
    print(f"Icon: {'Yes' if os.path.exists(os.path.join(resources, f'{APP_NAME}.icns')) else 'No'}")


if __name__ == "__main__":
    build()
