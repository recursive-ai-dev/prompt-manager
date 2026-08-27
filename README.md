# Prompt Manager

A sleek, fast, and feature-rich desktop application for storing, organizing, templating, and deploying AI prompts on Linux (tailored for KDE Plasma / Wayland / X11).

![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20(KDE%20%7C%20GNOME)-indigo)
![Framework](https://img.shields.io/badge/UI-PyQt6-green)
![Storage](https://img.shields.io/badge/storage-SQLite%20FTS5-orange)

---

## Highlights

- **⚡ Lightning-Fast & Lightweight**: Native Qt6 desktop application with sub-100ms cold startup and minimal (~40MB) memory footprint.
- **🔍 Full-Text Search (FTS5)**: Instant search indexing across titles, templates, descriptions, and system instructions.
- **🏷️ Multi-dimensional Organization**: Organize by nested folders, colored tags, target AI models, and starred favorites.
- **🧩 Dynamic Variable Engine**: Mustache-style templating (`{{var}}`, `{{var:default}}`, `{{var|multiline}}`, `{{var|options:a,b,c}}`) with an auto-generated live form.
- **👁️ Live Hydrated Preview**: See the rendered prompt in real time as you fill in parameters, with character, word, and estimated token counters.
- **📋 One-Click Clipboard Dispatch**: Instant copy to clipboard as formatted text, OpenAI API JSON, or Anthropic Messages API JSON.
- **🕒 Revision History**: Automatic and manual snapshot checkpoints to inspect diffs and rollback prompts at any time.
- **🚀 Native Desktop Integration**: Installs directly into KDE Kickoff menu, KRunner (`Alt+Space`), system tray, and terminal path (`prompt-manager`).

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
| `Ctrl + D` | Duplicate active prompt |
| `Ctrl + Q` | Exit application |

---

## Installation & Menu Integration

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
│   ├── app.py                     # Application entry point & Qt event loop
│   ├── config.py                  # XDG directory management & settings
│   ├── core/
│   │   ├── models.py              # Data models (Prompt, Folder, Tag, Revision)
│   │   ├── template_engine.py     # Variable extractor & hydration engine
│   │   ├── exporter.py            # OpenAI, Anthropic, Markdown formatters
│   │   └── token_counter.py       # Heuristic token & text metrics
│   ├── storage/
│   │   ├── database.py            # SQLite schema, WAL mode, FTS5 & triggers
│   │   ├── repository.py          # CRUD, FTS queries, tag & folder filtering
│   │   └── backup.py              # Entire library export/import to JSON
│   └── ui/
│       ├── main_window.py         # 3-column Qt layout, menus, and shortcuts
│       ├── theme.py               # Modern dark theme QSS stylesheet
│       ├── components/
│       │   ├── sidebar.py         # Folders, tags, favorites navigation
│       │   ├── prompt_list.py     # Search bar, prompt cards, context menu
│       │   ├── editor.py          # Syntax-highlighted template editor
│       │   ├── highlighter.py     # QSyntaxHighlighter for {{vars}} and markdown
│       │   ├── variable_form.py   # Dynamic input form for variables
│       │   ├── preview_panel.py   # Compiled preview, copy actions, metrics
│       │   ├── toast.py           # Animated transient toast notification
│       │   └── revision_modal.py  # Revision snapshots inspection dialog
│       └── assets/
│           └── icon.svg           # High-resolution SVG application icon
├── desktop/
│   ├── prompt-manager.desktop     # FreeDesktop XDG specification
│   ├── install.sh                 # Complete automated installer
│   └── uninstall.sh               # Clean uninstallation script
├── tests/                         # Full automated test suite
├── pyproject.toml
└── README.md
```
