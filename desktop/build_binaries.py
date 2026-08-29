#!/usr/bin/env python3
"""Cross-platform binary builder for Prompt Manager Studio.

Packages Prompt Manager into standalone, self-contained desktop executables
for Linux (binary/AppImage), macOS (.app/.dmg), and Windows (.exe/.zip)
using PyInstaller.
"""

from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "prompt_manager" / "ui" / "assets"


def build_executable():
    """Execute PyInstaller build with appropriate platform flags and asset bundling."""
    os_name = platform.system().lower()
    print(f"==================================================")
    print(f" Building Prompt Manager Studio for [{os_name}]")
    print(f"==================================================")

    # Check for PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Base PyInstaller arguments
    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=prompt-manager",
        "--noconfirm",
        "--clean",
        "--windowed",  # No terminal window on launch
        f"--add-data={ASSETS_DIR}{os.pathsep}prompt_manager/ui/assets",
        f"--paths={PROJECT_ROOT}",
    ]

    # Platform specific flags
    if os_name == "linux":
        icon_path = ASSETS_DIR / "icon.svg"
        if icon_path.exists():
            pyinstaller_args.append(f"--icon={icon_path}")
        pyinstaller_args.extend([
            "--onedir",
        ])
    elif os_name == "darwin":  # macOS
        icon_path = ASSETS_DIR / "icon.icns"
        if icon_path.exists():
            pyinstaller_args.append(f"--icon={icon_path}")
        pyinstaller_args.extend([
            "--onedir",
            "--osx-bundle-identifier=com.promptmanager.studio",
        ])
    elif os_name == "windows":
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            pyinstaller_args.append(f"--icon={icon_path}")
        pyinstaller_args.extend([
            "--onedir",
        ])

    # Entry point
    entry_script = PROJECT_ROOT / "prompt_manager" / "app.py"
    pyinstaller_args.append(str(entry_script))

    print(f"Running command: {' '.join(pyinstaller_args)}")
    result = subprocess.run(pyinstaller_args, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print(f"\n✅ Build succeeded! Output available at: {DIST_DIR / 'prompt-manager'}")
    else:
        print(f"\n❌ Build failed with exit code: {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_executable()
