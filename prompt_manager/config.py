"""Application configuration and XDG path management for Prompt Manager."""

import os
from pathlib import Path

APP_NAME = "prompt-manager"
APP_DISPLAY_NAME = "Prompt Manager"
APP_VERSION = "0.1.0"

# XDG Base Directory specification compliance
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

APP_DATA_DIR = XDG_DATA_HOME / APP_NAME
APP_CONFIG_DIR = XDG_CONFIG_HOME / APP_NAME

DATABASE_PATH = APP_DATA_DIR / "prompts.db"
CONFIG_FILE_PATH = APP_CONFIG_DIR / "settings.json"

DEFAULT_TARGET_MODELS = [
    "General",
    "Claude 3.7 Sonnet",
    "Claude 3.5 Haiku",
    "GPT-4o",
    "GPT-4o mini",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
    "DeepSeek R1",
    "DeepSeek V3",
    "Ollama / Local LLM",
]

def ensure_directories() -> None:
    """Ensure data and configuration directories exist."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
