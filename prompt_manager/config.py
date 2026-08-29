"""Application configuration and XDG path management for Prompt Manager."""

import json
import os
from pathlib import Path

APP_NAME = "prompt-manager"
APP_DISPLAY_NAME = "Prompt Manager"
APP_VERSION = "0.2.0"

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

DEFAULT_THEME_ID = "midnight_dark"


def ensure_directories() -> None:
    """Ensure data and configuration directories exist."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# ── Settings persistence (settings.json) ─────────────────────────────────

def _read_settings() -> dict:
    """Read settings.json, returning {} on missing/corrupt file."""
    if not CONFIG_FILE_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_settings(data: dict) -> None:
    """Write settings dict atomically."""
    ensure_directories()
    CONFIG_FILE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_theme_id() -> str:
    """Return persisted theme id, or DEFAULT_THEME_ID."""
    return _read_settings().get("theme", DEFAULT_THEME_ID)


def set_theme_id(theme_id: str) -> None:
    """Persist theme choice to settings.json."""
    data = _read_settings()
    data["theme"] = theme_id
    _write_settings(data)


def get_setting(key: str, default=None):
    return _read_settings().get(key, default)


def set_setting(key: str, value) -> None:
    data = _read_settings()
    data[key] = value
    _write_settings(data)


# ── GitHub integration persistence ────────────────────────────────────

def get_github_config() -> dict:
    """Return persisted GitHub config block (may be empty)."""
    data = _read_settings()
    gh = data.get("github", {})
    # Ensure defaults
    gh.setdefault("token", "")
    gh.setdefault("token_type", "")  # "pat" or "oauth"
    gh.setdefault("username", "")
    gh.setdefault("avatar_url", "")
    gh.setdefault("repo", "")  # full_name e.g. "owner/repo"
    gh.setdefault("branch", "main")
    gh.setdefault("file_path", "prompt-library.json")
    gh.setdefault("connected", False)
    gh.setdefault("oauth_client_id", "")
    gh.setdefault("last_sync", "")
    gh.setdefault("last_sync_sha", "")
    return gh


def set_github_config(patch: dict) -> None:
    """Merge patch into github config block and persist."""
    data = _read_settings()
    gh = data.get("github", {})
    gh.update(patch)
    data["github"] = gh
    _write_settings(data)


def clear_github_config() -> None:
    """Remove GitHub connection (token + repo) but keep branch/path defaults."""
    data = _read_settings()
    gh = data.get("github", {})
    for key in ["token", "token_type", "username", "avatar_url", "repo", "connected", "last_sync", "last_sync_sha"]:
        gh.pop(key, None)
    gh["connected"] = False
    data["github"] = gh
    _write_settings(data)


def is_github_connected() -> bool:
    gh = get_github_config()
    return bool(gh.get("token") and gh.get("connected"))


# ── Pollinations AI configuration ─────────────────────────────────────

DEFAULT_POLLINATIONS_MODEL = "openai-fast"
POLLINATIONS_MODELS = [
    "openai-fast",
    "openai",
    "mistral",
    "qwen",
    "llama",
    "deepseek",
    "claude",
]


def get_pollinations_config() -> dict:
    """Return persisted Pollinations configuration."""
    data = _read_settings()
    pol = data.get("pollinations", {})
    pol.setdefault("model", DEFAULT_POLLINATIONS_MODEL)
    pol.setdefault("api_key", "")
    pol.setdefault("temperature", 0.7)
    pol.setdefault("timeout", 45)
    return pol


def set_pollinations_config(patch: dict) -> None:
    """Merge patch into pollinations configuration and persist."""
    data = _read_settings()
    pol = data.get("pollinations", {})
    pol.update(patch)
    data["pollinations"] = pol
    _write_settings(data)

