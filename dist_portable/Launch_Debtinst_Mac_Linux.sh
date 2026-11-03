#!/usr/bin/env bash
# =================================================================
# Debtinst_s - Zero-Dependency Fixed-Income & Gold Bond Terminal
# One-Click Launcher for macOS & Linux
# =================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "================================================================="
echo "  Debtinst_s - Zero-Dependency Fixed-Income & Gold Bond Terminal "
echo "================================================================="

MAIN_PATH=""
if [ -f "$SCRIPT_DIR/../main.py" ]; then
    MAIN_PATH="$SCRIPT_DIR/../main.py"
elif [ -f "$SCRIPT_DIR/main.py" ]; then
    MAIN_PATH="$SCRIPT_DIR/main.py"
fi

# 1. Try launching live server if python3 is available
if [ -n "$MAIN_PATH" ] && command -v python3 >/dev/null 2>&1; then
    echo "[*] Launching live server via python3..."
    python3 "$MAIN_PATH"
    exit 0
fi

# 2. Zero-dependency fallback: open standalone HTML
HTML_FILE="$SCRIPT_DIR/Debtinst_s_Standalone.html"
if [ ! -f "$HTML_FILE" ]; then
    echo "[!] Error: Standalone HTML not found at $HTML_FILE"
    exit 1
fi

echo "[*] Launching zero-install standalone HTML terminal..."

# Try Google Chrome app mode
if command -v google-chrome >/dev/null 2>&1; then
    google-chrome --app="file://$HTML_FILE" >/dev/null 2>&1 &
    exit 0
elif command -v chromium >/dev/null 2>&1; then
    chromium --app="file://$HTML_FILE" >/dev/null 2>&1 &
    exit 0
elif [ "$(uname)" = "Darwin" ]; then
    if [ -d "/Applications/Google Chrome.app" ]; then
        open -na "Google Chrome" --args --app="file://$HTML_FILE"
        exit 0
    fi
    open "$HTML_FILE"
    exit 0
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$HTML_FILE" >/dev/null 2>&1 &
    exit 0
fi

echo "Please open $HTML_FILE in your web browser."
