#!/usr/bin/env bash
set -e

echo "=== Uninstalling Prompt Manager Desktop Integration ==="

BIN_PATH="${HOME}/.local/bin/prompt-manager"
DESKTOP_PATH="${HOME}/.local/share/applications/prompt-manager.desktop"
ICON_PATH="${HOME}/.local/share/icons/hicolor/scalable/apps/prompt-manager.svg"
PIXMAP_PATH="${HOME}/.local/share/pixmaps/prompt-manager.svg"

rm -f "${BIN_PATH}"
rm -f "${DESKTOP_PATH}"
rm -f "${ICON_PATH}"
rm -f "${PIXMAP_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${HOME}/.local/share/applications"
fi

echo "Prompt Manager desktop integration removed."
echo "(Note: Your prompt database at ~/.local/share/prompt-manager/ remains intact)"
