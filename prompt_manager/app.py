"""Application entry point for Prompt Manager."""

import argparse
import os
from pathlib import Path
import signal
import sys
from PyQt6.QtWidgets import QApplication

from prompt_manager.config import APP_DISPLAY_NAME, APP_NAME, APP_VERSION, ensure_directories
from prompt_manager.ui.main_window import MainWindow


def main():
    """Start the Prompt Manager Qt desktop application."""
    # Ensure standard desktop integration under Wayland and X11
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    # Allow graceful termination with Ctrl+C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = argparse.ArgumentParser(
        prog="prompt-manager",
        description="Prompt Manager — Prompt organizer, templating engine, and editor for Linux.",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Launch and immediately create a new prompt",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_DISPLAY_NAME} {APP_VERSION}",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Optional prompt or library file (.md, .json, .txt) to open",
    )
    args = parser.parse_args()

    ensure_directories()

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setDesktopFileName("prompt-manager.desktop")

    window = MainWindow()

    if args.new:
        window._on_new_prompt()
    elif args.file:
        window.import_file_from_cli(Path(args.file))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
