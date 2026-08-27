#!/usr/bin/env bash
set -e

# Resolve repository directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Installing Prompt Manager Desktop Application ==="
echo "Repository path: ${REPO_DIR}"

# Ensure standard XDG directories
BIN_DIR="${HOME}/.local/bin"
APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
PIXMAPS_DIR="${HOME}/.local/share/pixmaps"

mkdir -p "${BIN_DIR}" "${APPS_DIR}" "${ICONS_DIR}" "${PIXMAPS_DIR}"

# 1. Create executable wrapper in ~/.local/bin/prompt-manager
LAUNCHER="${BIN_DIR}/prompt-manager"
echo "Creating launcher wrapper at: ${LAUNCHER}"
cat <<EOF > "${LAUNCHER}"
#!/usr/bin/env bash
export PYTHONPATH="${REPO_DIR}:\$PYTHONPATH"
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-wayland;xcb}"
exec /usr/bin/python3 -m prompt_manager.app "\$@"
EOF
chmod +x "${LAUNCHER}"

# 2. Install SVG Icon
ICON_SRC="${REPO_DIR}/prompt_manager/ui/assets/icon.svg"
ICON_DEST="${ICONS_DIR}/prompt-manager.svg"
echo "Installing application icon to: ${ICON_DEST}"
cp -f "${ICON_SRC}" "${ICON_DEST}"
cp -f "${ICON_SRC}" "${PIXMAPS_DIR}/prompt-manager.svg"

# 3. Install .desktop Entry
DESKTOP_SRC="${SCRIPT_DIR}/prompt-manager.desktop"
DESKTOP_DEST="${APPS_DIR}/prompt-manager.desktop"
echo "Installing desktop entry to: ${DESKTOP_DEST}"

# Substitute absolute executable path
sed -e "s|^Exec=prompt-manager|Exec=${LAUNCHER}|g" "${DESKTOP_SRC}" > "${DESKTOP_DEST}"
chmod +x "${DESKTOP_DEST}"

# 4. Refresh Desktop Database
if command -v update-desktop-database >/dev/null 2>&1; then
    echo "Updating desktop database..."
    update-desktop-database "${APPS_DIR}"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true
fi

# 5. Validate Desktop File
if command -v desktop-file-validate >/dev/null 2>&1; then
    echo "Validating desktop file syntax..."
    desktop-file-validate "${DESKTOP_DEST}" && echo "✓ Desktop file is valid."
fi

echo ""
echo "======================================================="
echo " Prompt Manager successfully installed!"
echo " -> Available in KDE Kickoff menu & KRunner (Alt+Space)"
echo " -> Available in terminal as: prompt-manager"
echo "======================================================="
