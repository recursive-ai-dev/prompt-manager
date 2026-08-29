"""Application entry point for Prompt Manager."""

import argparse
import json
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

    # Lazy import for theme choices (avoid circular import at top-level)
    try:
        from prompt_manager.ui.theme import THEME_IDS  # type: ignore
    except Exception:
        THEME_IDS = []  # fallback if theme module missing

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
        "--new-template",
        action="store_true",
        help="Launch and immediately open the Templates manager to create a new template",
    )
    parser.add_argument(
        "--manage-templates",
        action="store_true",
        help="Launch and open the Template manager dialog on startup",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List all saved templates (name, category) and exit",
    )
    parser.add_argument(
        "--theme",
        choices=THEME_IDS,
        metavar="THEME",
        help=f"Launch with a specific theme ({', '.join(THEME_IDS) if THEME_IDS else 'see View menu'})",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="List all available themes and exit",
    )
    parser.add_argument(
        "--github-push",
        action="store_true",
        help="Push local library to configured GitHub repo via Contents API and exit (requires prior GitHub connection)",
    )
    parser.add_argument(
        "--github-pull",
        action="store_true",
        help="Pull library from configured GitHub repo and merge, then exit",
    )
    parser.add_argument(
        "--github-status",
        action="store_true",
        help="Show GitHub sync status and exit",
    )
    parser.add_argument(
        "--run-ai",
        metavar="TEXT_OR_FILE",
        help="Run prompt text or file directly through Pollinations.ai free text endpoint and print response",
    )
    parser.add_argument(
        "--ai-model",
        metavar="MODEL",
        default="openai-fast",
        help="Model to use with --run-ai (default: openai-fast)",
    )
    parser.add_argument(
        "--list-ai-models",
        action="store_true",
        help="List available Pollinations.ai text models and exit",
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

    if args.list_themes:
        try:
            from prompt_manager.ui.theme import list_themes as _list_themes

            for t in _list_themes():
                print(f"{t.id:20} {t.name:22} ({t.variant}) — {t.description}")
        except Exception as e:
            print(f"Failed to list themes: {e}")
        sys.exit(0)

    if args.list_templates:
        from prompt_manager.storage.database import Database as _DB
        from prompt_manager.storage.repository import PromptRepository as _Repo

        ensure_directories()
        _db = _DB()
        _repo = _Repo(_db)
        _templates = _repo.list_templates()
        if not _templates:
            print("(no templates — create one via Templates → Manage Templates or --new-template)")
        else:
            for tmpl in _templates:
                vars_list = ", ".join(s.name for s in tmpl.variable_specs()) or "no variables"
                print(f"{tmpl.name:30} [{tmpl.category:12}] id={tmpl.id[:8]} vars: {vars_list}")
                if tmpl.description:
                    print(f"  {tmpl.description}")
        sys.exit(0)

    # Handle headless GitHub actions (no GUI needed)
    if args.github_status:
        from prompt_manager.config import get_github_config

        gh = get_github_config()
        print(json.dumps(gh, indent=2))
        if not gh.get("token"):
            print("\nNot connected. Use the GUI: GitHub → Connect / Manage")
        sys.exit(0)

    if args.github_push or args.github_pull:
        # Headless sync without GUI
        ensure_directories()
        from prompt_manager.config import get_github_config as _get_gh
        from prompt_manager.storage.database import Database as _DB
        from prompt_manager.storage.repository import PromptRepository as _Repo
        from prompt_manager.integrations.github_client import GithubClient as _Client
        from prompt_manager.core.github_sync import push_library_via_api as _push, pull_library_via_api as _pull

        gh = _get_gh()
        if not gh.get("token") or not gh.get("repo"):
            print("GitHub not configured. Run GUI and use GitHub → Connect / Manage to set repo and token.", file=sys.stderr)
            sys.exit(2)
        db = _DB()
        repo = _Repo(db)
        client = _Client(gh["token"])
        try:
            if args.github_push:
                result = _push(repo, client, gh["repo"], branch=gh.get("branch", "main"), file_path=gh.get("file_path", "prompt-library.json"))
                sha = result.get("commit", {}).get("sha", "")[:7] if isinstance(result.get("commit"), dict) else ""
                print(f"Pushed to {gh['repo']} @ {sha}")
            else:
                count, info = _pull(repo, client, gh["repo"], branch=gh.get("branch", "main"), file_path=gh.get("file_path", "prompt-library.json"))
                print(f"Pulled {count} prompts from {gh['repo']}")
        except Exception as e:
            print(f"GitHub sync failed: {e}", file=sys.stderr)
            sys.exit(1)
    if args.list_ai_models:
        from prompt_manager.integrations.pollinations_client import PollinationsClient as _PolClient

        client = _PolClient()
        models = client.list_models()
        print("Pollinations.ai Free Text Models:")
        for m in models:
            name = m.get("name", "")
            desc = m.get("description", "")
            print(f"  • {name:20} — {desc}")
        sys.exit(0)

    if args.run_ai:
        from prompt_manager.integrations.pollinations_client import PollinationsClient as _PolClient, PollinationsError as _PolError

        raw_input = args.run_ai
        # Check if file path
        p = Path(raw_input)
        if p.exists() and p.is_file():
            prompt_content = p.read_text(encoding="utf-8")
        else:
            prompt_content = raw_input

        client = _PolClient()
        try:
            print(f"Generating via Pollinations ({args.ai_model})...", file=sys.stderr)
            result = client.generate(prompt=prompt_content, model=args.ai_model)
            print(result)
        except _PolError as e:
            print(f"Pollinations error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to generate: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    ensure_directories()

    # Persist CLI theme choice before window creation (window reads persisted id)
    if args.theme:
        try:
            from prompt_manager.config import set_theme_id as _set_theme_id

            _set_theme_id(args.theme)
        except Exception:
            pass

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setDesktopFileName("prompt-manager.desktop")

    window = MainWindow()

    if args.new:
        window._on_new_prompt()
    elif args.manage_templates or args.new_template:
        # Open template manager on startup; optionally pre-create
        window.show()
        # Use singleShot to ensure window is visible first
        from PyQt6.QtCore import QTimer

        if args.new_template:
            QTimer.singleShot(250, window._new_template)
        else:
            QTimer.singleShot(250, window._show_template_manager)
        # Still handle file arg after templates? fall through
        if args.file:
            window.import_file_from_cli(Path(args.file))
        sys.exit(app.exec())
    elif args.file:
        window.import_file_from_cli(Path(args.file))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
