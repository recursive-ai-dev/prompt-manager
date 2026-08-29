# Prompt Manager Studio

A sleek, blazing-fast, and local-first AI Prompt IDE & Workspace for developers and prompt engineers. Store, template, organize, benchmark, and deploy AI prompts across OpenAI, Anthropic, Google Gemini, and Local Ollama with zero lock-in and offline cryptographic licensing.

![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-indigo)
![Framework](https://img.shields.io/badge/UI-PyQt6-green)
![Storage](https://img.shields.io/badge/storage-SQLite%20FTS5%20%2B%20Keyring-orange)
![Tier](https://img.shields.io/badge/edition-Studio%20Pro-gold)

---

## Highlights

- **⚡ Lightning-Fast & Lightweight**: Native Qt6 desktop application with sub-100ms cold startup and minimal (~40MB) memory footprint.
- **⚡ Multi-Model Evaluation Arena (`Ctrl+Shift+A`)**: Benchmark prompts against up to 3 LLMs side-by-side simultaneously (OpenAI GPT-4o, Claude 3.7 Sonnet, Gemini 2.5 Pro, and Local Ollama models) with latency, token consumption, and dollar cost telemetry ($ / 1k tokens).
- **🚀 Global Spotlight/Raycast Quick-Launcher HUD (`Ctrl+Space`)**: Floating instant-search command palette. Fill dynamic template variables inline and dispatch hydrated prompts directly to your system clipboard without breaking workflow context.
- **🔑 Zero-Trust Keyring Vault (BYOK)**: Secure OS-keychain backed API Key Management (Linux Secret Service / Apple Keychain / Windows Credential Manager) with encrypted local fallback.
- **✨ Offline-First Cryptographic Licensing**: 100% offline HMAC-SHA256 digital license verification supporting Lifetime Pro licenses, Team seats, and automatic 14-day Pro trials.
- **🔍 Full-Text Search (FTS5)**: Instant search indexing across titles, templates, descriptions, and system instructions.
- **🏷️ Multi-dimensional Organization**: Organize by nested folders, colored tags, target AI models, and starred favorites.
- **🧩 Dynamic Variable Engine**: Mustache-style templating (`{{var}}`, `{{var:default}}`, `{{var|multiline}}`, `{{var|options:a,b,c}}`) with an auto-generated live form.
- **👁️ Live Hydrated Preview**: See the rendered prompt in real time as you fill in parameters, with character, word, and estimated token counters.
- **📋 Universal Export Ecosystem**: One-click export to OpenAI API JSON, Anthropic Messages API JSON, LangChain Python templates (`.py`), LlamaIndex (`.py`), CSV spreadsheets (`.csv`), and Markdown ZIP bundles (`.zip`).
- **🤖 Free AI Test Runner (Pollinations.ai)**: One-click live prompt testing with zero API keys required (`Ctrl+R`), background non-blocking execution, real-time response metrics, model selection, and stop controls.
- **🕒 Revision History**: Automatic and manual snapshot checkpoints to inspect diffs and rollback prompts at any time.
- **🔗 GitHub Sync (OAuth + PAT + Git)**: Connect via OAuth Device Flow or PAT, push/pull via GitHub Contents API or local `git` binary.
- **🎨 13 Handcrafted Themes**: Midnight Dark/Light, Nord, Dracula, Catppuccin Mocha/Latte, Gruvbox Dark/Light, Solarized Dark/Light, Tokyo Night, Rosé Pine, Everforest — switch via `View → Theme` or `Ctrl+T`.

---

## Templating Syntax

Prompt Manager supports dynamic parameter extraction from your prompt templates:

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `{{name}}` | Basic text input | `Hello {{username}}` |
| `{{name:default}}` | Text input with default fallback | `Target: {{language:Python}}` |
| `{{name\|multiline}}` | Expandable multi-line textarea | `Code:\n{{snippet\|multiline}}` |
| `{{name:default\|multiline}}` | Multi-line textarea with default | `{{data:sample_payload\|multiline}}` |
| `{{name\|options:opt1,opt2}}` | Dropdown selector | `{{tone\|options:casual,formal,brief}}` |
| `{{name:default\|options:opt1,opt2}}` | Dropdown selector with default | `{{model:gpt-4o\|options:gpt-4o,claude}}` |

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + N` | Create a new prompt |
| `Ctrl + S` | Save prompt & create revision checkpoint |
| `Ctrl + K` or `Ctrl + F` | Jump to search bar |
| `Ctrl + Shift + C` | Copy hydrated prompt to clipboard |
| `Ctrl + Shift + A` | **Open Multi-Model Evaluation Arena** |
| `Ctrl + Space` / `Ctrl + Alt + P` | **Open Quick Launcher HUD** |
| `Ctrl + ,` | **Open Settings & API Keys Dialog** |
| `Ctrl + R` | Run / test prompt with free AI (Pollinations) |
| `Ctrl + D` | Duplicate active prompt |
| `Ctrl + Shift + T` | Manage prompt templates |
| `Ctrl + G` | Push library to GitHub (requires GitHub connection) |
| `Ctrl + Shift + G` | Pull library from GitHub and merge |
| `Ctrl + T` | Toggle light/dark theme (Midnight Dark ↔ Light) |
| `Ctrl + Q` | Exit application |

---

## Multi-Model Arena & BYOK Providers

Connect your direct provider API keys via **Tools → Settings & API Keys (`Ctrl+,`)**:

- **OpenAI**: GPT-4o, GPT-4o Mini, o1-mini, o3-mini
- **Anthropic**: Claude 3.7 Sonnet, Claude 3.5 Haiku, Claude 3 Opus
- **Google Gemini**: Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash
- **Local Ollama**: `http://localhost:11434` with auto-discovery of locally installed models (`llama3.2`, `deepseek-r1`, `mistral`, `qwen2.5`)
- **OpenRouter**: Unified model aggregator
- **Pollinations.ai**: Free tier (Zero setup, no API key needed)

---

## CLI Power Commands

Prompt Manager includes comprehensive headless and shortcut commands:

```bash
# Launch directly into the Multi-Model Arena
prompt-manager --arena

# Launch floating Quick Launcher HUD
prompt-manager --hud

# Open Settings & API Keys
prompt-manager --settings

# Check Pro License and Trial status
prompt-manager --license-status

# Activate a Pro License Key
prompt-manager --activate-license "PM-PRO-LIFETIME-..."

# Generate a sample Pro License Key for evaluation
prompt-manager --generate-license "My Company"

# Run a prompt string directly in terminal via Pollinations
prompt-manager --run-ai "Explain vector search in 3 points" --ai-model openai-fast

# Push/Pull to GitHub headlessly in CI/CD scripts
prompt-manager --github-push
prompt-manager --github-pull
prompt-manager --github-status
```

---

## Cross-Platform Distribution & Builds

Standalone binaries can be compiled for Linux, macOS, and Windows via PyInstaller:

```bash
# Build standalone desktop binary
python desktop/build_binaries.py
```

Outputs:
- **Linux**: `dist/prompt-manager/prompt-manager`
- **macOS**: `dist/prompt-manager.app`
- **Windows**: `dist/prompt-manager/prompt-manager.exe`

Automated CI/CD build releases across all 3 platforms are configured in `.github/workflows/build_releases.yml`.

---

## Installation & Menu Integration (Linux)

To install Prompt Manager as a native desktop application in your Linux application launcher:

```bash
./desktop/install.sh
```

This will:
1. Create a launcher wrapper in `~/.local/bin/prompt-manager`.
2. Install the high-res SVG icon to `~/.local/share/icons/hicolor/scalable/apps/prompt-manager.svg`.
3. Install the FreeDesktop entry to `~/.local/share/applications/prompt-manager.desktop`.
4. Trigger `update-desktop-database` to immediately register in KDE / GNOME application menus.

To uninstall:
```bash
./desktop/uninstall.sh
```

---

## Project Structure

```
prompt-manager/
├── prompt_manager/
│   ├── app.py                     # Entry, Qt loop, --arena/--hud/--settings/--license CLI
│   ├── config.py                  # XDG dirs + settings.json
│   ├── core/
│   │   ├── models.py              # Data models (Prompt, Folder, Tag, Revision, Template)
│   │   ├── template_engine.py     # Mustache variable extractor & hydration
│   │   ├── keychain.py            # OS Keyring + encrypted vault BYOK credential storage
│   │   ├── licensing.py           # Offline HMAC-SHA256 license verification & Pro trial
│   │   ├── arena.py               # Concurrent multi-model evaluation engine
│   │   ├── exporter.py            # OpenAI, Anthropic, LangChain, LlamaIndex, CSV formatters
│   │   ├── token_counter.py       # BPE token counter & text metrics
│   │   └── github_sync.py         # GitHub sync orchestrator (API + git)
│   ├── integrations/
│   │   ├── llm_providers.py       # OpenAI, Anthropic, Gemini, Ollama, OpenRouter, Pollinations
│   │   ├── pollinations_client.py # Free text AI client
│   │   ├── github_client.py       # GitHub API client (PAT, OAuth device flow)
│   │   └── git_helper.py          # Local git binary wrapper
│   ├── storage/
│   │   ├── database.py            # SQLite schema, WAL, FTS5
│   │   ├── repository.py          # CRUD, FTS, tags/folders/templates
│   │   └── backup.py              # JSON, CSV, and Markdown ZIP export/import
│   └── ui/
│       ├── main_window.py         # 3-column layout, menus (File/Tools/Templates/View/GitHub/Help)
│       ├── theme.py               # 13 QSS themes via palette builder
│       ├── components/
│       │   ├── arena_dialog.py    # 3-way multi-model benchmark dialog
│       │   ├── quick_launcher.py  # Floating Spotlight/Raycast HUD command palette
│       │   ├── settings_dialog.py # BYOK API keys, general preferences & licensing
│       │   ├── preview_panel.py   # Live output preview with Arena & Free AI trigger
│       │   ├── editor.py          # Syntax-highlighted template editor
│       │   ├── sidebar.py         # Folders, tags, and filters
│       │   ├── prompt_list.py     # Searchable prompt list
│       │   ├── variable_form.py   # Dynamic parameter input form
│       │   ├── revision_modal.py  # Snapshot diff and rollback modal
│       │   ├── toast.py           # Notification overlay
│       │   └── github_dialog.py   # GitHub sync modal
│       └── assets/icon.svg
├── desktop/
│   ├── build_binaries.py          # Cross-platform PyInstaller packager
│   ├── install.sh                 # Linux desktop installer
│   ├── uninstall.sh               # Linux uninstaller
│   └── prompt-manager.desktop
├── .github/workflows/
│   └── build_releases.yml         # CI/CD multi-OS release builder
├── tests/                         # Full test suite (77 tests)
├── pyproject.toml
└── README.md
```
