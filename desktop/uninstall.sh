#!/usr/bin/env bash
set -euo pipefail

echo "=== Uninstalling Prompt Manager Desktop Integration ==="

BIN_PATH="${HOME}/.local/bin/prompt-manager"
BIN_ORIG="${HOME}/.local/bin/prompt-manager.orig"
DESKTOP_PATH="${HOME}/.local/share/applications/prompt-manager.desktop"
ICON_PATH="${HOME}/.local/share/icons/hicolor/scalable/apps/prompt-manager.svg"
PIXMAP_PATH="${HOME}/.local/share/pixmaps/prompt-manager.svg"
PIP_MARKER="${HOME}/.local/share/prompt-manager/.pip-installed"

# ── Remove launcher wrappers ─────────────────────────────────────────
for p in "${BIN_PATH}" "${BIN_ORIG}"; do
    if [[ -f "${p}" || -L "${p}" ]]; then
        rm -f "${p}"
        echo "Removed ${p}"
    fi
done

# ── Remove desktop entry & icons ─────────────────────────────────────
for p in "${DESKTOP_PATH}" "${ICON_PATH}" "${PIXMAP_PATH}"; do
    if [[ -f "${p}" ]]; then
        rm -f "${p}"
        echo "Removed ${p}"
    fi
done

# Remove PNG fallbacks if they were rendered
for sz in 16 24 32 48 64 128 256; do
    PNG="${HOME}/.local/share/icons/hicolor/${sz}x${sz}/apps/prompt-manager.png"
    if [[ -f "${PNG}" ]]; then
        rm -f "${PNG}"
        echo "Removed ${PNG}"
    fi
done

# Optionally remove pip-installed package (ask first)
if command -v python3 >/dev/null 2>&1 && python3 -m pip show prompt-manager >/dev/null 2>&1; then
    echo ""
    read -r -p "Also uninstall pip package 'prompt-manager' (pip uninstall)? [y/N] " _ans
    if [[ "${_ans:-}" =~ ^[Yy]$ ]]; then
        python3 -m pip uninstall -y prompt-manager 2>&1 | tail -n 5 || true
        rm -f "${PIP_MARKER}" 2>/dev/null || true
        echo "Pip package removed."
    else
        echo "Keeping pip package. To remove later: pip uninstall prompt-manager"
        # Purge cached wrapper marker but keep package
        rm -f "${PIP_MARKER}" 2>/dev/null || true
    fi
fi

# ── Refresh caches ───────────────────────────────────────────────────
if command -v update-desktop-database >/dev/null 2>&1; then
    echo "Updating desktop database..."
    update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 2>/dev/null || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 2>/dev/null || true
fi

echo ""
echo "Prompt Manager desktop integration removed."
echo "(Your prompt database at ~/.local/share/prompt-manager/prompts.db and settings.json remain intact.)"
echo "To fully wipe data: rm -rf ~/.local/share/prompt-manager ~/.config/prompt-manager"
