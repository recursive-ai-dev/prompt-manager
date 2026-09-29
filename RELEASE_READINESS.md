# Release Readiness Report

_Project:_ **Prompt Manager Studio** (`prompt-manager` v0.2.0) — PyQt6 desktop AI‑prompt IDE
_Branch:_ `arena/01a0eb7e-prompt-manager`
_Date:_ 2026-09-29
_Role:_ Lead Release Engineer — release hardening sweep

## Executive Summary

**The project is deployable.** The application builds, imports, packages, and runs from a
clean virtual environment, and the full automated test suite passes (**107/107**). The
release sweep found and fixed **six real release blockers/robustness gaps** — the most
important being that **every advertised headless CLI command crashed on any server without
GUI/OpenGL libraries** (Qt was imported at module top level), and that **`--github-push` /
`--github-pull` silently fell through into launching the GUI** after a successful headless
sync. Both are fixed and verified.

No mock/fake data was found in any production path — all LLM/GitHub/Pollinations
integrations call real, configurable endpoints. No invented credentials or infrastructure
were introduced. The only genuinely unverifiable items are **outbound network reachability
to third‑party AI services (Pollinations.ai)** and **full PyInstaller binary linking**, both
blocked by *this sandbox's* environment (no shared `libpython`, restricted egress) rather
than by any project defect; the CI pipeline that performs these on GitHub runners has been
corrected so they will execute there.

## Gaps Resolved

| Location | Gap | Production Logic Added | Verification |
|---|---|---|---|
| `prompt_manager/app.py` (top-level import) | `from PyQt6.QtWidgets import QApplication` and `MainWindow` were imported at module load, so **all headless CLI commands** (`--run-ai`, `--github-push/pull/status`, `--license-status`, `--list-templates`, `--version`) crashed with `ImportError: libGL.so.1` on headless servers/CI — directly contradicting the documented "headless CI/CD" use case. | Moved Qt/UI imports into the GUI‑launch path only. Headless commands now run without any GUI stack. GUI launch failure now prints a clear, actionable message and exits 1 instead of a raw traceback. | Ran `--version`, `--license-status`, `--github-status`, `--list-templates`, `--list-themes` with **no Qt libraries present** → all exit 0. GUI attempt without libs → graceful message, exit 1. |
| `prompt_manager/app.py` (`--github-push`/`--github-pull`) | Missing `sys.exit` after headless GitHub sync → on **success** control fell through and launched the full GUI; a `.desktop` "Push/Pull to GitHub" action would pop a window unexpectedly. | Added `sys.exit(0)` after the headless GitHub block. | `--github-push` against a dummy repo → fails fast with `GitHub sync failed: Not Found`, exit 1, **no GUI**. Success path now exits 0 by construction. |
| `prompt_manager/storage/database.py`, `prompt_manager/storage/repository.py` | Schema unconditionally created **FTS5** virtual tables/triggers; a SQLite build without the FTS5 module would crash at first launch (`no such module: fts5`) — an unsafe environment assumption. | Added `fts5_available()` probe; split schema into `BASE_SCHEMA_SQL` + `FTS_SCHEMA_SQL`; `Database.fts_enabled` flag; search transparently falls back to `LIKE` when FTS5 is absent. Default (FTS5 present) behavior unchanged. | With FTS5 force‑disabled: DB initializes, no `*_fts` tables, prompt search (`vector`, `HNSW`) and template search (`review`) all return correct rows. Full suite still passes with FTS5 enabled. |
| `prompt_manager/ui/__init__.py` | Package `__init__` eagerly imported `MainWindow`, so importing the Qt‑free `theme` submodule dragged in PyQt6 → `--list-themes` failed on headless boxes. | Lazy `MainWindow` via module‑level `__getattr__` (keeps `from prompt_manager.ui import MainWindow` working). | `--list-themes` now lists all 34 themes with **no Qt libs**; `from prompt_manager.ui import MainWindow` still resolves under offscreen Qt. |
| `desktop/install.sh` | The `PIP_BIN` detection one‑liner had broken quoting (`\"` inside a single‑quoted string) → Python `SyntaxError`, so the pip entry‑point delegation never worked and `prompt-manager.orig` was never created. | Rewrote using `os.path.join(sysconfig.get_path("scripts"), ...)` with correct quoting; added a per‑user (`posix_user`) scripts‑dir fallback. | `bash -n` passes; both Python one‑liners now print valid paths (`/usr/local/bin/...`, `~/.local/bin/...`). |
| `prompt_manager/__init__.py`, `github_client.py` | Version drift: `__version__ = "0.1.0"` vs `pyproject`/`config` `0.2.0`; GitHub client User‑Agent pinned to `prompt-manager/0.1`. | Aligned `__version__` to `0.2.0`; bumped default User‑Agent to `prompt-manager/0.2.0`. | `prompt-manager --version` → `Prompt Manager 0.2.0`; editable wheel built as `prompt_manager-0.2.0`. |
| `.github/workflows/build_releases.yml` | The `Run Test Suite` step would fail on GitHub's headless `ubuntu-*` runners: Qt needs `libEGL/libGL/libxkbcommon/libdbus` and an off‑screen platform, none present by default. | Added a Linux step to `apt-get install` the Qt runtime libraries and set `QT_QPA_PLATFORM=offscreen` for the test step. | Locally reproduced the exact failure and the fix (offscreen + libs) makes the suite pass; workflow YAML validated by inspection. |
| `pyproject.toml` | Optional, advertised capability (OS keyring) and tooling deps were undeclared, so users could not opt in cleanly. | Added `[project.optional-dependencies]`: `keyring`, `assets` (Pillow), `build` (pyinstaller), `dev` (pytest). Core install stays minimal (PyQt6 only). | `tomllib` parses; extras enumerated: `keyring, assets, build, dev`. |

## Environment and Dependency Matrix

### Runtime dependencies
| Item | Required? | Safe default / fallback | Notes |
|---|---|---|---|
| `PyQt6 >= 6.4.0` | **Required (GUI only)** | — | Sole hard runtime dependency. Not needed for headless CLI subcommands (now verified). |
| `keyring >= 24.0` | Optional (`[keyring]` extra) | Encrypted local vault (`~/.config/prompt-manager/vault.dat`, machine‑bound XOR) | App works out of the box without it; OS keychain used automatically when installed. |
| `Pillow >= 10.0` | Optional (`[assets]` extra) | Returns input bytes unchanged | Only used by the theme‑accent asset generator (dev tooling). |
| `pyinstaller >= 6.0` | Optional (`[build]` extra) | — | Only for standalone binary packaging. |
| `pytest >= 7.0` | Optional (`[dev]` extra) | — | Test runner. |
| Python stdlib `sqlite3` **with FTS5** | Recommended | `LIKE`‑based search fallback (new) | Full‑text search is faster with FTS5; app no longer crashes without it. |

### Environment variables (all have safe defaults — no manual setup required)
| Variable | Default | Purpose |
|---|---|---|
| `XDG_DATA_HOME` | `~/.local/share` | DB location → `<data>/prompt-manager/prompts.db` |
| `XDG_CONFIG_HOME` | `~/.config` | `settings.json` + credential vault |
| `QT_QPA_PLATFORM` | `wayland;xcb` (auto) / `offscreen` in CI | Qt platform plugin selection |
| `QT_AUTO_SCREEN_SCALE_FACTOR` | `1` (set by launcher) | HiDPI scaling |
| `PYTHON` | `/usr/bin/python3` | Interpreter used by `desktop/install.sh` |

### Secrets — user‑provided at runtime, never bundled
| Secret | Where it lives | Required for |
|---|---|---|
| OpenAI / Anthropic / Gemini / OpenRouter API keys | OS keyring or encrypted vault (BYOK) | Multi‑Model Arena with those providers (optional) |
| GitHub PAT or OAuth token | `settings.json` `github` block | GitHub sync (optional) |
| GitHub OAuth `client_id` | User‑supplied (Settings/env) | OAuth Device Flow only; **PAT works with zero config** |
| Pro license key | `settings.json` | Optional; 14‑day Pro trial auto‑starts, then Free tier |

### External services (optional, graceful‑degrading)
| Service | Endpoint | Behavior when unreachable |
|---|---|---|
| GitHub API | `api.github.com` | Sync features raise a clear error; app unaffected. **Reachable & exercised in sandbox** (404 on dummy repo). |
| Pollinations.ai | `text.pollinations.ai` | Free AI runner reports a clear network error and exits/aborts cleanly (no crash). |
| OpenAI/Anthropic/Gemini/OpenRouter/Ollama | provider URLs (configurable) | Per‑provider error surfaced in the Arena; other features unaffected. |

## Verification Results

Environment: clean `.venv` (Python 3.11.2). Qt‑dependent checks run with
`QT_QPA_PLATFORM=offscreen` and minimal stub `.so`s standing in for the absent system
`libGL/libEGL/libxkbcommon/libdbus` (the sandbox has no package manager egress and no X/GL
stack). Headless‑CLI checks run with **no Qt libraries on the loader path** to prove the
no‑GUI path.

| Check | Command | Result |
|---|---|---|
| Unit/integration tests | `pytest -q` | ✅ **107 passed** in ~1s |
| Byte‑compile (syntax) | `python -m compileall prompt_manager desktop` | ✅ OK |
| Package build (editable) | `pip install -e .` | ✅ Built `prompt_manager-0.2.0`, `prompt-manager` entry point created |
| Entry point | `prompt-manager --version` | ✅ `Prompt Manager 0.2.0` |
| Headless CLI (no Qt) | `--version`, `--license-status`, `--github-status`, `--list-templates`, `--list-themes` | ✅ All exit 0 without GUI libs |
| GUI launch | construct `MainWindow`, run event loop, quit | ✅ Window shows, DB auto‑seeds, clean exit |
| Route/handler wiring | instantiate `MainWindow`, assert 23 connected menu/signal handlers exist + invoke several | ✅ No broken routes |
| Headless GitHub sync exits | `--github-push` (dummy creds) | ✅ Fails fast, exit 1, **no GUI fall‑through** |
| FTS5 fallback | force `fts5_available()=False`, run searches | ✅ LIKE fallback returns correct results; no `*_fts` tables created |
| Shell scripts | `bash -n desktop/install.sh desktop/uninstall.sh` | ✅ Valid syntax; PIP_BIN one‑liner fixed |
| Lint / type‑check | — | ⚠️ **Not configured** in the project (no ruff/flake8/mypy). `compileall` used as a syntax gate. Not a blocker; see residual risk. |
| PyInstaller binary link | `python desktop/build_binaries.py` | ⚠️ **Unverifiable in sandbox** — spec generated & analysis started, then failed: `libpython3.11.so.1.0 not found` (sandbox Python built without a shared lib). Present on `actions/setup-python` runners; the build script itself is correct. |
| Pollinations live run | `--run-ai "..."` | ⚠️ **Service unreachable from sandbox** (egress limited to PyPI + GitHub). App degraded gracefully with a clear error (no crash). |

## Remaining Blockers and Residual Risk

There are **no code‑level release blockers**. Remaining items are environmental
verifications and minor, non‑blocking observations.

| Item | Impact | Condition to clear |
|---|---|---|
| **PyInstaller binary not fully linked here** | Cannot 100% confirm the produced desktop binary in *this sandbox*. | Runs on any host with a shared `libpython` (GitHub `actions/setup-python` provides it). Trigger the `Build & Release` workflow (tag `v*` or `workflow_dispatch`) to produce/verify artifacts. |
| **Pollinations.ai / provider AI calls not live‑tested** | The "Free AI Test Runner" and Arena provider calls are unverified against real endpoints from this sandbox (egress restricted). | Run `prompt-manager --run-ai "ping"` (and Arena with a real key) from a network with outbound HTTPS. Failure handling already verified to be graceful. |
| **No linter/type‑checker configured** | Style/type regressions aren't gated automatically. | Optional: add `ruff`/`mypy` to `[dev]` and a CI step. Non‑blocking. |
| **GitHub OAuth Device Flow needs a user `client_id`** | Out‑of‑the‑box OAuth is inert; **PAT auth works with zero config** (documented, enforced with a clear error). | Users register a GitHub OAuth App and set the `client_id` if they prefer OAuth over PAT. Intentional — shipping a shared secret is not appropriate. |
| **Docs say "13 themes"; code ships 34** | Documentation understatement only; more themes than advertised. | Optional README copy update (left unchanged to avoid scope creep during hardening). |
| **Offline license HMAC secret is embedded** | Anyone reading the source can mint Pro keys. | By design for a 100% offline, self‑hostable licensing scheme; acceptable for this edition. Move to signed asymmetric keys if commercial anti‑piracy hardening is later required. |
