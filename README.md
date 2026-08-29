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
- **🔗 GitHub Sync (OAuth + PAT + Git)**: Connect via OAuth Device Flow or PAT, save your library to a **new or existing repo**, push/pull via GitHub Contents API or local `git` binary.
- **🎨 13 Handcrafted Themes**: Midnight Dark/Light, Nord, Dracula, Catppuccin Mocha/Latte, Gruvbox Dark/Light, Solarized Dark/Light, Tokyo Night, Rosé Pine, Everforest — switch via `View → Theme` or `Ctrl+T`.
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
| `Ctrl + Shift + T` | Manage prompt templates |
| `Ctrl + G` | Push library to GitHub (requires GitHub connection) |
| `Ctrl + Shift + G` | Pull library from GitHub and merge |
| `Ctrl + T` | Toggle light/dark theme (Midnight Dark ↔ Light) |
| `Ctrl + Q` | Exit application |

---

## Reusable Prompt Templates

Prompt Manager provides dedicated infrastructure for creating reusable templates (skeletons with variables and system instructions):

- **Template Manager (`Ctrl+Shift+T`)**: Create, edit, duplicate, categorize, and search templates. Starts empty on a fresh install so you can define your own domain-specific templates.
- **Instantiation**: Instantiate a new prompt from any template via `Templates → Use Template → New Prompt` or the Template Manager dialog.
- **Import / Export**: Templates are included in full library backups (`File → Export Library`) and can also be exported/imported independently (`Templates → Export Templates`).
- **CLI Management**:
  - `prompt-manager --list-templates` — list saved templates and variables in terminal.
  - `prompt-manager --manage-templates` — launch directly into the Template Manager dialog.
  - `prompt-manager --new-template` — launch and immediately create a new template.

---

## GitHub Sync — OAuth, PAT & Git

Prompt Manager can back up your entire prompt library to GitHub and restore it on any machine.

**Connect:**
- **PAT (simplest)**: Create a token at `github.com/settings/tokens` with `repo` scope, then `GitHub → Connect / Manage → Paste PAT → Verify`.
- **OAuth Device Flow**: Create an OAuth App at `github.com/settings/developers`, paste its Client ID, click **Start OAuth Device Flow**, enter the code at `github.com/login/device`, and authorize.

**Choose a repository:**
- **Existing repo**: Refresh the list of your repos, pick `owner/repo`, and click **Use Selected Repo** — saves to that repo.
- **New repo**: Enter a name (e.g. `prompt-library`), optional description, choose private/public, and click **Create & Use New Repo** — the app calls `POST /user/repos` via the GitHub API.

**Sync:**
- `GitHub → Push Library` (`Ctrl+G`) — exports `prompt-library.json` (same format as `File → Export`) and `PUT /repos/{owner}/{repo}/contents/{path}` on branch `main` (configurable). Uses the Contents API (no local `git` needed) or `Push via Local Git` (clones to `~/.local/share/prompt-manager/github_sync/` and `git push` with token).
- `GitHub → Pull Library` (`Ctrl+Shift+G`) — fetches the JSON file via `GET /repos/.../contents/...`, decodes base64, and merges via `import_library_from_json`.
- Status shown in the status bar (`GitHub: owner/repo@main ●`) and via `GitHub → Sync Status`. Headless CLI: `prompt-manager --github-push / --github-pull / --github-status`.

Tokens and repo choice are stored in `~/.config/prompt-manager/settings.json` under the `github` block. The Contents API path and branch are configurable in the dialog (`prompt-library.json` by default on `main`).

---

## Themes

13 QSS themes built from a shared palette in `prompt_manager/ui/theme.py:39`:

`midnight_dark` (default), `midnight_light`, `nord`, `dracula`, `catppuccin_mocha`, `catppuccin_latte`, `gruvbox_dark`, `gruvbox_light`, `solarized_dark`, `solarized_light`, `tokyo_night`, `rose_pine`, `everforest`.

Switch via `View → Theme → 🌙/☀️`, `Ctrl+T` toggle, or `prompt-manager --theme dracula --list-themes`.

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
│   ├── app.py                     # Entry, Qt loop, --theme/--github-* CLI
│   ├── config.py                  # XDG dirs + settings.json (theme + github block)
│   ├── core/
│   │   ├── models.py              # Data models (Prompt, Folder, Tag, Revision)
│   │   ├── template_engine.py     # Variable extractor & hydration
│   │   ├── exporter.py            # OpenAI/Anthropic/Markdown formatters
│   │   ├── token_counter.py       # Token & text metrics
│   │   └── github_sync.py         # GitHub sync orchestrator (API + git)
│   ├── integrations/
│   │   ├── github_client.py       # GitHub API client (PAT, OAuth device flow, Contents API)
│   │   └── git_helper.py          # Local git binary wrapper (init/commit/push)
│   ├── storage/
│   │   ├── database.py            # SQLite schema, WAL, FTS5
│   │   ├── repository.py          # CRUD, FTS, tags/folders
│   │   └── backup.py              # Library JSON export/import
│   └── ui/
│       ├── main_window.py         # 3-column layout, menus (File/GitHub/View/Help)
│       ├── theme.py               # 13 QSS themes via palette builder
│       ├── components/
│       │   ├── sidebar.py
│       │   ├── prompt_list.py
│       │   ├── editor.py
│       │   ├── highlighter.py     # Theme-aware highlighter
│       │   ├── variable_form.py
│       │   ├── preview_panel.py   # Theme-aware preview
│       │   ├── toast.py
│       │   ├── revision_modal.py
│       │   └── github_dialog.py   # OAuth/PAT, repo create/select, push/pull
│       └── assets/icon.svg
├── desktop/
├── tests/                         # Exporter, repository, template, (github mocked)
├── pyproject.toml
└── README.md
```
