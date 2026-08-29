"""GitHub Connection Dialog — OAuth Device Flow + PAT, repo create/select, push/pull."""

from __future__ import annotations

from datetime import datetime
import json
import os
import urllib.parse
import urllib.request
import webbrowser
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.config import get_github_config, set_github_config, clear_github_config
from prompt_manager.integrations.github_client import (
    GithubClient,
    GithubError,
    DEFAULT_OAUTH_SCOPE,
    request_device_code,
    DeviceCodeResponse,
)
from prompt_manager.integrations.github_client import ACCESS_TOKEN_URL
from prompt_manager.core.github_sync import validate_github_config


class _DevicePollWorker(QObject):
    """Worker that polls GitHub device flow endpoint until token or error."""

    token_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, client_id: str, device_code: str, interval: int, expires_in: int):
        super().__init__()
        self.client_id = client_id
        self.device_code = device_code
        self.interval = max(interval, 5)
        self.expires_in = expires_in
        self._stop = False

    def stop(self):
        self._stop = True

    def run_poll(self):
        import time
        import urllib.parse
        import urllib.request
        import json

        deadline = time.time() + self.expires_in
        current_interval = self.interval
        self.status_update.emit(f"Polling every {current_interval}s… (expires in {self.expires_in}s)")
        while time.time() < deadline and not self._stop:
            time.sleep(current_interval)
            if self._stop:
                break
            data = urllib.parse.urlencode(
                {
                    "client_id": self.client_id,
                    "device_code": self.device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                }
            ).encode("utf-8")
            headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
            req = urllib.request.Request(ACCESS_TOKEN_URL, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as e:
                self.status_update.emit(f"Poll error: {e} — retrying")
                continue

            if "access_token" in payload and payload["access_token"]:
                self.token_received.emit(payload["access_token"])
                return
            error = payload.get("error")
            if error == "authorization_pending":
                self.status_update.emit("Waiting for you to authorize in browser…")
                continue
            elif error == "slow_down":
                current_interval += 5
                self.status_update.emit(f"Slow down — new interval {current_interval}s")
                continue
            elif error == "expired_token":
                self.error_occurred.emit("Device code expired — please restart")
                return
            elif error == "access_denied":
                self.error_occurred.emit("You denied access — flow cancelled")
                return
            elif error:
                desc = payload.get("error_description") or error
                self.error_occurred.emit(desc)
                return
        if not self._stop:
            self.error_occurred.emit("Timed out waiting for authorization")


class GithubDialog(QDialog):
    """Modal dialog for GitHub connection & repo sync configuration."""

    # Emitted after successful push/pull so main window can refresh
    sync_completed = pyqtSignal(str)  # "push" | "pull"

    def __init__(self, parent=None, repo=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Connection — Prompt Manager")
        self.resize(720, 620)
        self.setModal(True)

        self._repo = repo  # PromptRepository for immediate sync actions (optional, will lazy-load)
        self._device_response: Optional[DeviceCodeResponse] = None
        self._poll_thread: Optional[QThread] = None
        self._poll_worker: Optional[_DevicePollWorker] = None
        self._verified_username: str = ""

        self._build_ui()
        self._load_from_config()
        self._update_connection_ui()

    # ── UI Construction ─────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("<b>Sync your prompt library to GitHub</b> — connect via OAuth or PAT, then push to a new or existing repository.")
        header.setWordWrap(True)
        header.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(header)

        self.tabs = QTabWidget(self)

        # Tab 1: Connection
        self.tab_connect = QWidget()
        self._build_connect_tab()
        self.tabs.addTab(self.tab_connect, "🔐 Connection")

        # Tab 2: Repository & Sync
        self.tab_repo = QWidget()
        self._build_repo_tab()
        self.tabs.addTab(self.tab_repo, "📚 Repository & Sync")

        layout.addWidget(self.tabs, stretch=1)

        # Bottom buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self._on_close_attempt)
        layout.addWidget(btn_box)

    def _build_connect_tab(self):
        layout = QVBoxLayout(self.tab_connect)
        layout.setSpacing(10)

        # Status banner
        self.conn_status_label = QLabel("Not connected")
        self.conn_status_label.setStyleSheet("padding: 8px; border-radius: 6px; font-weight: 600;")
        layout.addWidget(self.conn_status_label)

        self.conn_detail_label = QLabel("")
        self.conn_detail_label.setWordWrap(True)
        self.conn_detail_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.conn_detail_label)

        # ── PAT Group ──────────────────────────────────────────────
        pat_group = QGroupBox("Personal Access Token (PAT)")
        pat_group.setToolTip("Create a token at github.com/settings/tokens — needs `repo` scope for private repos, `public_repo` for public.")
        pat_layout = QVBoxLayout(pat_group)

        pat_form = QFormLayout()
        self.pat_input = QLineEdit()
        self.pat_input.setPlaceholderText("ghp_... or github_pat_...")
        self.pat_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pat_input.setToolTip("Your GitHub PAT. Stored in ~/.config/prompt-manager/settings.json")
        pat_form.addRow("Token:", self.pat_input)

        pat_layout.addLayout(pat_form)

        # Show/hide toggle
        pat_btn_row = QHBoxLayout()
        self.pat_show_btn = QPushButton("👁 Show")
        self.pat_show_btn.setCheckable(True)
        self.pat_show_btn.toggled.connect(self._toggle_pat_visibility)
        pat_btn_row.addWidget(self.pat_show_btn)

        self.pat_verify_btn = QPushButton("Verify & Save Token")
        self.pat_verify_btn.setObjectName("primaryButton")
        self.pat_verify_btn.clicked.connect(self._verify_pat)
        pat_btn_row.addWidget(self.pat_verify_btn)

        self.pat_clear_btn = QPushButton("Disconnect")
        self.pat_clear_btn.clicked.connect(self._disconnect)
        pat_btn_row.addWidget(self.pat_clear_btn)

        pat_btn_row.addStretch()
        pat_layout.addLayout(pat_btn_row)

        help_label = QLabel(
            'Need a token? <a href="https://github.com/settings/tokens/new">Create at github.com/settings/tokens/new</a> '
            "(classic) or <a href=\"https://github.com/settings/tokens\">fine-grained</a> — scope <code>repo</code>."
        )
        help_label.setOpenExternalLinks(True)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("font-size: 11px; color: #64748b;")
        pat_layout.addWidget(help_label)

        layout.addWidget(pat_group)

        # ── OAuth Device Flow Group ────────────────────────────────
        oauth_group = QGroupBox("OAuth Device Flow (no PAT needed)")
        oauth_group.setToolTip("Uses GitHub OAuth Device Flow — you authorize in your browser without pasting a token.")
        oauth_layout = QVBoxLayout(oauth_group)

        oauth_form = QFormLayout()
        self.oauth_client_input = QLineEdit()
        self.oauth_client_input.setPlaceholderText("Ov1...  (leave empty to use PAT only)")
        self.oauth_client_input.setToolTip(
            "Your GitHub OAuth App Client ID. Create an OAuth App at github.com/settings/developers → OAuth Apps → New OAuth App. "
            "Callback URL can be http://localhost. For device flow, no secret needed."
        )
        oauth_form.addRow("OAuth Client ID:", self.oauth_client_input)
        oauth_layout.addLayout(oauth_form)

        oauth_btn_row = QHBoxLayout()
        self.oauth_start_btn = QPushButton("🔑 Start OAuth Device Flow")
        self.oauth_start_btn.clicked.connect(self._start_device_flow)
        oauth_btn_row.addWidget(self.oauth_start_btn)

        self.oauth_cancel_btn = QPushButton("Cancel Polling")
        self.oauth_cancel_btn.setEnabled(False)
        self.oauth_cancel_btn.clicked.connect(self._cancel_device_flow)
        oauth_btn_row.addWidget(self.oauth_cancel_btn)
        oauth_btn_row.addStretch()
        oauth_layout.addLayout(oauth_btn_row)

        # Device code display (hidden until flow starts)
        self.oauth_code_widget = QWidget()
        oauth_code_layout = QVBoxLayout(self.oauth_code_widget)
        oauth_code_layout.setContentsMargins(0, 0, 0, 0)

        self.oauth_instruction_label = QLabel("")
        self.oauth_instruction_label.setWordWrap(True)
        self.oauth_instruction_label.setStyleSheet("padding: 8px; border: 1px solid #2d3340; border-radius: 6px; background: #1a1e26;")
        self.oauth_instruction_label.setTextFormat(Qt.TextFormat.RichText)
        self.oauth_instruction_label.setOpenExternalLinks(True)
        oauth_code_layout.addWidget(self.oauth_instruction_label)

        code_row = QHBoxLayout()
        self.oauth_user_code_label = QLabel("")
        self.oauth_user_code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.oauth_user_code_label.setStyleSheet("font-family: monospace; font-size: 16px; font-weight: 700; letter-spacing: 2px; padding: 6px 10px; border: 1px dashed #3b82f6; border-radius: 6px;")
        code_row.addWidget(self.oauth_user_code_label)
        code_row.addStretch()

        self.oauth_copy_code_btn = QPushButton("Copy Code")
        self.oauth_copy_code_btn.clicked.connect(self._copy_user_code)
        code_row.addWidget(self.oauth_copy_code_btn)

        self.oauth_open_browser_btn = QPushButton("Open Browser")
        self.oauth_open_browser_btn.setObjectName("primaryButton")
        self.oauth_open_browser_btn.clicked.connect(self._open_verification_uri)
        code_row.addWidget(self.oauth_open_browser_btn)

        oauth_code_layout.addLayout(code_row)

        self.oauth_poll_status = QLabel("")
        self.oauth_poll_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        oauth_code_layout.addWidget(self.oauth_poll_status)

        self.oauth_progress = QProgressBar()
        self.oauth_progress.setRange(0, 0)
        self.oauth_progress.setVisible(False)
        self.oauth_progress.setMaximumHeight(6)
        oauth_code_layout.addWidget(self.oauth_progress)

        oauth_layout.addWidget(self.oauth_code_widget)
        self.oauth_code_widget.setVisible(False)

        hint = QLabel("Tip: OAuth avoids storing a long-lived PAT. The device flow token has the same <code>repo</code> scope you choose during OAuth App setup.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #64748b;")
        oauth_layout.addWidget(hint)

        layout.addWidget(oauth_group)
        layout.addStretch()

    def _build_repo_tab(self):
        layout = QVBoxLayout(self.tab_repo)
        layout.setSpacing(10)

        # Current connection summary
        self.repo_current_label = QLabel("No GitHub connection — connect first in the Connection tab.")
        self.repo_current_label.setWordWrap(True)
        self.repo_current_label.setStyleSheet("padding: 8px; border-radius: 6px;")
        layout.addWidget(self.repo_current_label)

        # ── Select existing repo ───────────────────────────────────
        existing_group = QGroupBox("Save to Existing Repository")
        ex_layout = QVBoxLayout(existing_group)

        combo_row = QHBoxLayout()
        self.repo_combo = QComboBox()
        self.repo_combo.setEditable(True)
        self.repo_combo.setPlaceholderText("owner/repo  or select from list")
        self.repo_combo.setToolTip("Pick an existing repo you own (or type owner/repo directly)")
        combo_row.addWidget(self.repo_combo, stretch=1)

        self.repo_refresh_btn = QPushButton("↻ Refresh")
        self.repo_refresh_btn.setToolTip("Fetch your GitHub repositories")
        self.repo_refresh_btn.clicked.connect(self._refresh_repos)
        combo_row.addWidget(self.repo_refresh_btn)

        ex_layout.addLayout(combo_row)

        save_existing_row = QHBoxLayout()
        self.repo_use_existing_btn = QPushButton("✔ Use Selected Repo")
        self.repo_use_existing_btn.setObjectName("primaryButton")
        self.repo_use_existing_btn.clicked.connect(self._use_existing_repo)
        save_existing_row.addWidget(self.repo_use_existing_btn)
        save_existing_row.addStretch()
        ex_layout.addLayout(save_existing_row)

        ex_layout.addWidget(QLabel("<span style='color:#64748b;font-size:11px;'>You need push access. Private repos require <code>repo</code> scope.</span>"))

        layout.addWidget(existing_group)

        # ── Create new repo ────────────────────────────────────────
        create_group = QGroupBox("Or Create a New Repository")
        cr_layout = QFormLayout(create_group)

        self.new_repo_name = QLineEdit()
        self.new_repo_name.setPlaceholderText("prompt-library  (lowercase, hyphens)")
        cr_layout.addRow("New repo name:", self.new_repo_name)

        self.new_repo_desc = QLineEdit()
        self.new_repo_desc.setPlaceholderText("My synced prompt library — managed by Prompt Manager")
        cr_layout.addRow("Description:", self.new_repo_desc)

        self.new_repo_private = QCheckBox("Private repository")
        self.new_repo_private.setChecked(True)
        cr_layout.addRow("", self.new_repo_private)

        self.new_repo_create_btn = QPushButton("✨ Create & Use New Repo")
        self.new_repo_create_btn.setObjectName("primaryButton")
        self.new_repo_create_btn.clicked.connect(self._create_new_repo)
        cr_layout.addRow("", self.new_repo_create_btn)

        layout.addWidget(create_group)

        # ── Sync settings ──────────────────────────────────────────
        sync_group = QGroupBox("Sync Settings")
        sync_form = QFormLayout(sync_group)

        self.branch_input = QLineEdit()
        self.branch_input.setText("main")
        self.branch_input.setPlaceholderText("main")
        sync_form.addRow("Branch:", self.branch_input)

        self.file_path_input = QLineEdit()
        self.file_path_input.setText("prompt-library.json")
        self.file_path_input.setPlaceholderText("prompt-library.json  or prompts/library.json")
        sync_form.addRow("File path:", self.file_path_input)

        self.commit_msg_input = QLineEdit()
        self.commit_msg_input.setPlaceholderText("Sync prompt library via Prompt Manager (auto)")
        sync_form.addRow("Commit message:", self.commit_msg_input)

        layout.addWidget(sync_group)

        # ── Sync actions ───────────────────────────────────────────
        actions_group = QGroupBox("Sync Actions")
        act_layout = QVBoxLayout(actions_group)

        # Primary API actions
        api_row = QHBoxLayout()
        self.push_api_btn = QPushButton("⬆ Push Library to GitHub (API)")
        self.push_api_btn.setObjectName("primaryButton")
        self.push_api_btn.setToolTip("Export library to JSON and PUT to GitHub via Contents API (no local git needed)")
        self.push_api_btn.clicked.connect(self._push_via_api)
        api_row.addWidget(self.push_api_btn)

        self.pull_api_btn = QPushButton("⬇ Pull Library from GitHub")
        self.pull_api_btn.setToolTip("Fetch JSON file from GitHub and merge into local database")
        self.pull_api_btn.clicked.connect(self._pull_via_api)
        api_row.addWidget(self.pull_api_btn)

        act_layout.addLayout(api_row)

        # Secondary: local git & individual files
        git_row = QHBoxLayout()
        self.push_git_btn = QPushButton("⬆ Push via Local Git")
        self.push_git_btn.setToolTip("Uses system `git` binary — clones, commits and pushes locally under ~/.local/share/prompt-manager/github_sync/")
        self.push_git_btn.clicked.connect(self._push_via_git)
        git_row.addWidget(self.push_git_btn)

        self.push_individual_btn = QPushButton("📄 Push as Markdown Files")
        self.push_individual_btn.setToolTip("Push each prompt as an individual Markdown file under prompts/ folder")
        self.push_individual_btn.clicked.connect(self._push_individual)
        git_row.addWidget(self.push_individual_btn)

        act_layout.addLayout(git_row)

        self.sync_status_label = QLabel("")
        self.sync_status_label.setWordWrap(True)
        self.sync_status_label.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 4px;")
        act_layout.addWidget(self.sync_status_label)

        layout.addWidget(actions_group)
        layout.addStretch()

    # ── Config load/save ──────────────────────────────────────────

    def _load_from_config(self):
        gh = get_github_config()
        token = gh.get("token", "")
        if token:
            # Show masked
            self.pat_input.setText(token)
        self.branch_input.setText(gh.get("branch", "main"))
        self.file_path_input.setText(gh.get("file_path", "prompt-library.json"))
        # repo combo: add current repo if any
        repo = gh.get("repo", "")
        if repo:
            self.repo_combo.clear()
            self.repo_combo.addItem(repo)
            self.repo_combo.setCurrentText(repo)
        client_id = gh.get("oauth_client_id", "") or os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
        if client_id:
            self.oauth_client_input.setText(client_id)
        # Commit message leave placeholder (not persisted)

    def _save_repo_settings(self):
        # Persist branch/path/commit template
        set_github_config(
            {
                "branch": self.branch_input.text().strip() or "main",
                "file_path": self.file_path_input.text().strip() or "prompt-library.json",
                "oauth_client_id": self.oauth_client_input.text().strip(),
            }
        )
        # If repo combo has a value and user clicked Use, that method persists repo

    def _update_connection_ui(self):
        gh = get_github_config()
        connected = bool(gh.get("connected") and gh.get("token"))
        if connected:
            user = gh.get("username") or "Connected"
            repo = gh.get("repo") or "no repo selected"
            self.conn_status_label.setText(f"✅ Connected as {user}")
            self.conn_status_label.setStyleSheet("padding: 8px; border-radius: 6px; font-weight: 600; background: #064e3b; color: #a7f3d0; border: 1px solid #059669;")
            self.conn_detail_label.setText(f"Repo: {repo}  •  Branch: {gh.get('branch','main')}  •  Path: {gh.get('file_path','prompt-library.json')}")
            self.repo_current_label.setText(f"✅ <b>Connected as {user}</b> — Target: <code>{repo}</code> on <code>{gh.get('branch','main')}</code> → <code>{gh.get('file_path')}</code>")
            self.repo_current_label.setStyleSheet("padding: 8px; border-radius: 6px; background: #064e3b; color: #d1fae5; border: 1px solid #059669;")
        else:
            self.conn_status_label.setText("⚪ Not connected — verify a PAT or complete OAuth flow")
            self.conn_status_label.setStyleSheet("padding: 8px; border-radius: 6px; font-weight: 600; background: #1e293b; color: #94a3b8; border: 1px solid #334155;")
            if gh.get("token"):
                self.conn_detail_label.setText("Token saved but not verified — click Verify & Save Token")
            else:
                self.conn_detail_label.setText("Add a PAT or use OAuth Device Flow. Your token is stored locally in settings.json")
            self.repo_current_label.setText("⚪ <b>Not connected</b> — go to <b>Connection</b> tab to authenticate first. You can still type <code>owner/repo</code> manually.")
            self.repo_current_label.setStyleSheet("padding: 8px; border-radius: 6px; background: #422006; color: #fde68a; border: 1px solid #92400e;")

        # Enable repo actions only if connected (but allow typing repo manually)
        has_token = bool(gh.get("token"))
        self.repo_refresh_btn.setEnabled(has_token)
        self.repo_use_existing_btn.setEnabled(has_token or bool(self.repo_combo.currentText().strip()))
        self.new_repo_create_btn.setEnabled(has_token)
        # Sync buttons need repo selected
        has_repo = bool(gh.get("repo"))
        self.push_api_btn.setEnabled(has_repo and has_token)
        self.pull_api_btn.setEnabled(has_repo and has_token)
        self.push_git_btn.setEnabled(has_repo and has_token)
        self.push_individual_btn.setEnabled(has_repo and has_token)
        # Repo combo enabled even if not connected, to allow manual entry
        self.repo_combo.setEnabled(True)

    # ── PAT flow ──────────────────────────────────────────────────

    def _toggle_pat_visibility(self, checked: bool):
        self.pat_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        self.pat_show_btn.setText("🙈 Hide" if checked else "👁 Show")

    def _verify_pat(self):
        token = self.pat_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Token required", "Paste your GitHub PAT (ghp_… or github_pat_…).")
            return
        self.pat_verify_btn.setEnabled(False)
        self.pat_verify_btn.setText("Verifying…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            client = GithubClient(token)
            user = client.get_user()
            username = user.get("login", "unknown")
            avatar = user.get("avatar_url", "")
            # Persist
            set_github_config(
                {
                    "token": token,
                    "token_type": "pat",
                    "username": username,
                    "avatar_url": avatar,
                    "connected": True,
                    "last_sync": "",
                }
            )
            # Also persist branch/path/client id
            self._save_repo_settings()
            self._verified_username = username
            QMessageBox.information(self, "Verified", f"✅ Connected as {username}")
            self._update_connection_ui()
            # Auto-refresh repos after success
            self._refresh_repos(silent=True)
        except GithubError as e:
            QMessageBox.critical(self, "Verification failed", f"GitHub rejected the token:\n{e}\n\nStatus: {e.status or '—'}\nCheck that the token has `repo` scope and has not expired.")
        except Exception as e:
            QMessageBox.critical(self, "Verification failed", f"Unexpected error:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.pat_verify_btn.setEnabled(True)
            self.pat_verify_btn.setText("Verify & Save Token")
            self._update_connection_ui()

    def _disconnect(self):
        reply = QMessageBox.question(
            self,
            "Disconnect GitHub",
            "Remove stored GitHub token and disconnect?\n\nYour local prompts will NOT be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        clear_github_config()
        self.pat_input.clear()
        self.repo_combo.clear()
        self._update_connection_ui()
        self._save_repo_settings()
        QMessageBox.information(self, "Disconnected", "GitHub connection removed.")

    # ── OAuth Device Flow ─────────────────────────────────────────

    def _start_device_flow(self):
        client_id = self.oauth_client_input.text().strip() or os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
        if not client_id:
            QMessageBox.warning(
                self,
                "Client ID required",
                "For OAuth Device Flow you need a GitHub OAuth App Client ID.\n\n"
                "1. Go to github.com/settings/developers → OAuth Apps → New OAuth App\n"
                "2. Application name: Prompt Manager\n"
                "3. Homepage: http://localhost\n"
                "4. Callback: http://localhost\n"
                "5. Copy the Client ID and paste it above.\n\n"
                "Alternatively, use a PAT (simpler) in the section above.",
            )
            return
        # Persist client id
        set_github_config({"oauth_client_id": client_id})
        self.oauth_start_btn.setEnabled(False)
        self.oauth_start_btn.setText("Requesting device code…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            resp = request_device_code(client_id, scope=DEFAULT_OAUTH_SCOPE)
            self._device_response = resp
            # Show code UI
            self.oauth_code_widget.setVisible(True)
            self.oauth_user_code_label.setText(resp.user_code)
            self.oauth_instruction_label.setText(
                f"1. Open <a href=\"{resp.verification_uri}\">{resp.verification_uri}</a><br>"
                f"2. Enter code <b>{resp.user_code}</b><br>"
                f"3. Authorize <b>Prompt Manager</b> → you’ll be connected automatically.<br>"
                f"<span style='color:#64748b;'>Complete URL: <a href=\"{resp.verification_uri_complete}\">{resp.verification_uri_complete}</a></span>"
            )
            self.oauth_poll_status.setText(f"Waiting for authorization… (expires in {resp.expires_in}s, polling every {resp.interval}s)")
            self.oauth_progress.setVisible(True)
            self.oauth_cancel_btn.setEnabled(True)
            # Start polling worker in thread
            self._start_poll_thread(client_id, resp.device_code, resp.interval, resp.expires_in)
        except GithubError as e:
            QMessageBox.critical(self, "OAuth error", f"Failed to start device flow:\n{e}")
            self.oauth_start_btn.setEnabled(True)
            self.oauth_start_btn.setText("🔑 Start OAuth Device Flow")
        except Exception as e:
            QMessageBox.critical(self, "OAuth error", f"Unexpected error:\n{e}")
            self.oauth_start_btn.setEnabled(True)
            self.oauth_start_btn.setText("🔑 Start OAuth Device Flow")
        finally:
            QGuiApplication.restoreOverrideCursor()

    def _start_poll_thread(self, client_id: str, device_code: str, interval: int, expires_in: int):
        # Clean previous
        self._cancel_device_flow(silent=True)
        self._poll_thread = QThread(self)
        self._poll_worker = _DevicePollWorker(client_id, device_code, interval, expires_in)
        self._poll_worker.moveToThread(self._poll_thread)
        self._poll_thread.started.connect(self._poll_worker.run_poll)
        self._poll_worker.token_received.connect(self._on_oauth_token)
        self._poll_worker.error_occurred.connect(self._on_oauth_error)
        self._poll_worker.status_update.connect(lambda msg: self.oauth_poll_status.setText(msg))
        self._poll_thread.start()

    def _cancel_device_flow(self, silent: bool = False):
        if self._poll_worker:
            self._poll_worker.stop()
        if self._poll_thread:
            self._poll_thread.quit()
            self._poll_thread.wait(1000)
        self._poll_worker = None
        self._poll_thread = None
        if not silent:
            self.oauth_progress.setVisible(False)
            self.oauth_poll_status.setText("Cancelled")
            self.oauth_start_btn.setEnabled(True)
            self.oauth_start_btn.setText("🔑 Start OAuth Device Flow")
            self.oauth_cancel_btn.setEnabled(False)

    def _on_oauth_token(self, token: str):
        self.oauth_progress.setVisible(False)
        self.oauth_cancel_btn.setEnabled(False)
        self.oauth_start_btn.setEnabled(True)
        self.oauth_start_btn.setText("🔑 Start OAuth Device Flow")
        # Verify token get user
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            client = GithubClient(token)
            user = client.get_user()
            username = user.get("login", "unknown")
            avatar = user.get("avatar_url", "")
            set_github_config(
                {
                    "token": token,
                    "token_type": "oauth",
                    "username": username,
                    "avatar_url": avatar,
                    "connected": True,
                    "last_sync": "",
                }
            )
            self._save_repo_settings()
            QMessageBox.information(self, "OAuth success", f"✅ Connected as {username} via OAuth")
            self._update_connection_ui()
            self._refresh_repos(silent=True)
        except Exception as e:
            QMessageBox.critical(self, "OAuth verification failed", f"Got token but failed to verify:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._cancel_device_flow(silent=True)
            self.oauth_progress.setVisible(False)

    def _on_oauth_error(self, msg: str):
        self.oauth_progress.setVisible(False)
        self.oauth_cancel_btn.setEnabled(False)
        self.oauth_start_btn.setEnabled(True)
        self.oauth_start_btn.setText("🔑 Start OAuth Device Flow")
        self.oauth_poll_status.setText(msg)
        QMessageBox.warning(self, "OAuth flow", msg)
        self._cancel_device_flow(silent=True)

    def _copy_user_code(self):
        if self._device_response:
            QGuiApplication.clipboard().setText(self._device_response.user_code)
            self.oauth_poll_status.setText("Code copied to clipboard ✓")

    def _open_verification_uri(self):
        if self._device_response:
            url = self._device_response.verification_uri_complete or self._device_response.verification_uri
            QDesktopServices.openUrl(QUrl(url))
        else:
            QDesktopServices.openUrl(QUrl("https://github.com/login/device"))

    # ── Repo list / create ────────────────────────────────────────

    def _get_client(self) -> Optional[GithubClient]:
        gh = get_github_config()
        token = gh.get("token", "")
        if not token:
            QMessageBox.warning(self, "Not connected", "Connect to GitHub first (PAT or OAuth).")
            return None
        return GithubClient(token)

    def _refresh_repos(self, silent: bool = False):
        client = self._get_client()
        if not client:
            if not silent:
                QMessageBox.warning(self, "Not connected", "Connect to GitHub first.")
            return
        self.repo_refresh_btn.setEnabled(False)
        self.repo_refresh_btn.setText("Loading…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            repos = client.get_user_repos(per_page=100)
            # Sort by updated
            repos_sorted = sorted(repos, key=lambda r: r.get("updated_at", ""), reverse=True)
            current = self.repo_combo.currentText()
            self.repo_combo.clear()
            for r in repos_sorted:
                full = r.get("full_name", "")
                private = "🔒" if r.get("private") else "🌐"
                self.repo_combo.addItem(f"{private} {full}", full)
                # Also add plain full_name as data for easier retrieval
            # If current was typed manually, preserve it
            if current and current not in [self.repo_combo.itemData(i) for i in range(self.repo_combo.count())]:
                self.repo_combo.addItem(current, current)
            if repos_sorted and not current:
                # Don't auto-select; let user pick
                pass
            if not silent:
                self.sync_status_label.setText(f"Fetched {len(repos_sorted)} repos ✓")
        except GithubError as e:
            if not silent:
                QMessageBox.critical(self, "Fetch failed", f"Could not list repos:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.repo_refresh_btn.setEnabled(True)
            self.repo_refresh_btn.setText("↻ Refresh")

    def _resolve_combo_repo(self) -> str:
        # If combo has currentData, use it; else use currentText stripped
        data = self.repo_combo.currentData()
        text = self.repo_combo.currentText().strip()
        # Text may be like "🔒 owner/repo" — strip emoji and spaces
        if text.startswith("🔒") or text.startswith("🌐"):
            text = text[2:].strip()
        # Prefer data if it looks like full_name
        if data and "/" in data:
            return data.strip()
        # Fallback to text
        # Text may contain extra label; extract first token with slash
        for token in text.split():
            if "/" in token:
                return token.strip()
        return text

    def _use_existing_repo(self):
        repo = self._resolve_combo_repo()
        if not repo or "/" not in repo:
            QMessageBox.warning(self, "Pick a repo", "Select a repository from the list or type owner/repo.")
            return
        # Validate existence via API if connected
        client = self._get_client()
        if client:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                info = client.get_repo(repo)
                # Store
                set_github_config({"repo": info.get("full_name", repo), "connected": True})
                self._save_repo_settings()
                self._update_connection_ui()
                QMessageBox.information(self, "Repository set", f"Using <b>{info.get('full_name', repo)}</b><br>Branch: {self.branch_input.text().strip() or 'main'}<br>Path: {self.file_path_input.text().strip() or 'prompt-library.json'}")
                self.sync_status_label.setText(f"Target set to {repo} ✓")
            except GithubError as e:
                QMessageBox.critical(self, "Repo not accessible", f"Could not access {repo}:\n{e}\n\nCheck that you have push access and the name is correct (owner/repo).")
            finally:
                QGuiApplication.restoreOverrideCursor()
        else:
            # Offline: just save locally
            set_github_config({"repo": repo})
            self._save_repo_settings()
            self._update_connection_ui()
            QMessageBox.information(self, "Repository set", f"Using {repo} (not verified — connect to verify)")

    def _create_new_repo(self):
        name = self.new_repo_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Name required", "Enter a name for the new repository (e.g. prompt-library).")
            return
        # Basic validation: GitHub repo name restrictions
        if " " in name or "/" in name:
            QMessageBox.warning(self, "Invalid name", "Repository name must not contain spaces or slashes. Use hyphens or underscores.")
            return
        desc = self.new_repo_desc.text().strip() or "Prompt library synced via Prompt Manager"
        private = self.new_repo_private.isChecked()
        client = self._get_client()
        if not client:
            return
        self.new_repo_create_btn.setEnabled(False)
        self.new_repo_create_btn.setText("Creating…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            repo_info = client.create_repo(name=name, private=private, description=desc, auto_init=True)
            full = repo_info.get("full_name", f"{repo_info.get('owner', {}).get('login','')}/{name}")
            # Save as target
            set_github_config({"repo": full, "connected": True})
            self._save_repo_settings()
            # Refresh combo
            self.repo_combo.clear()
            self.repo_combo.addItem(f"{'🔒' if private else '🌐'} {full}", full)
            self.repo_combo.setCurrentText(full)
            self._update_connection_ui()
            QMessageBox.information(
                self,
                "Repository created",
                f"✅ Created <b>{full}</b> ({'private' if private else 'public'})<br><br>"
                f"<a href=\"{repo_info.get('html_url','https://github.com/' + full)}\">{repo_info.get('html_url','')}</a>",
            )
            self.sync_status_label.setText(f"Created and selected {full} ✓")
        except GithubError as e:
            if e.status == 422 and "already exists" in str(e).lower():
                QMessageBox.warning(self, "Already exists", f"A repository named '{name}' already exists. Choose another name or use the existing repo selector.")
            else:
                QMessageBox.critical(self, "Create failed", f"Could not create repository:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.new_repo_create_btn.setEnabled(True)
            self.new_repo_create_btn.setText("✨ Create & Use New Repo")

    # ── Sync actions ──────────────────────────────────────────────

    def _validate_sync_config(self) -> Optional[tuple[str, str, str]]:
        gh = get_github_config()
        repo = gh.get("repo", "").strip() or self._resolve_combo_repo()
        branch = self.branch_input.text().strip() or gh.get("branch", "main")
        path = self.file_path_input.text().strip() or gh.get("file_path", "prompt-library.json")
        err = validate_github_config(repo, branch, path)
        if err:
            QMessageBox.warning(self, "Configuration error", err)
            return None
        # Persist branch/path
        set_github_config({"branch": branch, "file_path": path})
        return repo, branch, path

    def _get_repo_for_sync(self):
        # Ensure we have a repo object to sync; lazy-load if parent didn't pass one
        if self._repo:
            return self._repo
        # Create temporary repo access from main window's repo if available
        try:
            from prompt_manager.storage.database import Database
            from prompt_manager.storage.repository import PromptRepository

            db = Database()
            return PromptRepository(db)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Could not access local prompts:\n{e}")
            return None

    def _push_via_api(self):
        cfg = self._validate_sync_config()
        if not cfg:
            return
        repo_full, branch, path = cfg
        client = self._get_client()
        if not client:
            return
        repo_obj = self._get_repo_for_sync()
        if not repo_obj:
            return
        msg = self.commit_msg_input.text().strip()
        count = len(repo_obj.list_prompts())
        if not msg:
            msg = f"Sync prompt library ({count} prompts) via Prompt Manager"

        self.push_api_btn.setEnabled(False)
        self.push_api_btn.setText("Pushing…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.sync_status_label.setText(f"Pushing {count} prompts to {repo_full}/{path}@{branch}…")
        try:
            from prompt_manager.core.github_sync import push_library_via_api

            result = push_library_via_api(repo_obj, client, repo_full, branch=branch, file_path=path, commit_message=msg)
            sha = result.get("commit", {}).get("sha", "")[:7] if isinstance(result.get("commit"), dict) else ""
            set_github_config({"last_sync": datetime.now().isoformat(), "last_sync_sha": sha})
            html_url = result.get("content", {}).get("html_url", "") if isinstance(result.get("content"), dict) else ""
            self.sync_status_label.setText(f"✅ Pushed to {repo_full} @ {sha} ✓")
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Icon.Information)
            msgbox.setWindowTitle("Push complete")
            msgbox.setText(f"✅ Pushed <b>{count} prompts</b> to <b>{repo_full}</b><br>Branch: <code>{branch}</code><br>Path: <code>{path}</code><br>Commit: <code>{sha}</code>")
            if html_url:
                msgbox.setInformativeText(f'<a href="{html_url}">View file on GitHub</a>')
                msgbox.setTextFormat(Qt.TextFormat.RichText)
            msgbox.exec()
            self.sync_completed.emit("push")
        except GithubError as e:
            QMessageBox.critical(self, "Push failed", f"GitHub rejected the push:\n{e}\nStatus: {e.status or '—'}")
            self.sync_status_label.setText(f"Push failed: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Push failed", f"Unexpected error:\n{e}")
            self.sync_status_label.setText(f"Push failed: {e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.push_api_btn.setEnabled(True)
            self.push_api_btn.setText("⬆ Push Library to GitHub (API)")
            self._update_connection_ui()

    def _pull_via_api(self):
        cfg = self._validate_sync_config()
        if not cfg:
            return
        repo_full, branch, path = cfg
        client = self._get_client()
        if not client:
            return
        repo_obj = self._get_repo_for_sync()
        if not repo_obj:
            return
        reply = QMessageBox.question(
            self,
            "Pull from GitHub",
            f"Pull <code>{path}</code> from <b>{repo_full}@{branch}</b> and merge into your local library?<br><br>"
            "Existing prompts with the same ID will be overwritten, new ones added. Folders/tags will be merged.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.pull_api_btn.setEnabled(False)
        self.pull_api_btn.setText("Pulling…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.sync_status_label.setText(f"Pulling {path} from {repo_full}@{branch}…")
        try:
            from prompt_manager.core.github_sync import pull_library_via_api

            count, info = pull_library_via_api(repo_obj, client, repo_full, branch=branch, file_path=path)
            self.sync_status_label.setText(f"✅ Pulled {count} prompts ✓")
            QMessageBox.information(self, "Pull complete", f"✅ Imported <b>{count} prompts</b> from <b>{repo_full}</b><br>(file sha: <code>{info.get('sha','')[:7]}</code>)")
            self.sync_completed.emit("pull")
        except GithubError as e:
            QMessageBox.critical(self, "Pull failed", f"Could not pull:\n{e}\nStatus: {e.status or '—'}")
            self.sync_status_label.setText(f"Pull failed: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Pull failed", f"Unexpected error:\n{e}")
            self.sync_status_label.setText(f"Pull failed: {e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.pull_api_btn.setEnabled(True)
            self.pull_api_btn.setText("⬇ Pull Library from GitHub")

    def _push_via_git(self):
        cfg = self._validate_sync_config()
        if not cfg:
            return
        repo_full, branch, path = cfg
        gh = get_github_config()
        token = gh.get("token", "")
        if not token:
            QMessageBox.warning(self, "Not connected", "Connect to GitHub first.")
            return
        # Check git available
        try:
            from prompt_manager.integrations.git_helper import is_git_available

            if not is_git_available():
                QMessageBox.warning(self, "Git not found", "`git` binary not found. Install git or use the API push instead.")
                return
        except Exception:
            pass
        repo_obj = self._get_repo_for_sync()
        if not repo_obj:
            return
        msg = self.commit_msg_input.text().strip() or f"Sync prompt library via Prompt Manager"
        self.push_git_btn.setEnabled(False)
        self.push_git_btn.setText("Pushing via git…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            from prompt_manager.core.github_sync import push_library_via_git

            result = push_library_via_git(repo_obj, repo_full, token, branch=branch, file_path=path, commit_message=msg)
            if result == "no-changes":
                QMessageBox.information(self, "Git push", "No changes to push — local library already matches remote.")
                self.sync_status_label.setText("No changes to push")
            else:
                QMessageBox.information(self, "Git push complete", f"✅ Pushed via local git<br>Commit: <code>{result[:7]}</code><br>Branch: {branch}")
                self.sync_status_label.setText(f"✅ Git push {result[:7]} ✓")
                self.sync_completed.emit("push")
        except Exception as e:
            # Try to scrub token from error
            err_str = str(e).replace(token, "***")
            QMessageBox.critical(self, "Git push failed", f"Local git push failed:\n{err_str}")
            self.sync_status_label.setText(f"Git push failed")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.push_git_btn.setEnabled(True)
            self.push_git_btn.setText("⬆ Push via Local Git")

    def _push_individual(self):
        cfg = self._validate_sync_config()
        if not cfg:
            return
        repo_full, branch, _ = cfg
        client = self._get_client()
        if not client:
            return
        repo_obj = self._get_repo_for_sync()
        if not repo_obj:
            return
        reply = QMessageBox.question(
            self,
            "Push individual files",
            f"This will push each prompt as a separate Markdown file under <code>prompts/</code> in <b>{repo_full}@{branch}</b>.<br><br>Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.push_individual_btn.setEnabled(False)
        self.push_individual_btn.setText("Pushing…")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            from prompt_manager.core.github_sync import push_individual_prompts_via_api

            count = push_individual_prompts_via_api(repo_obj, client, repo_full, branch=branch, folder="prompts")
            QMessageBox.information(self, "Push complete", f"✅ Pushed {count} Markdown files to <code>prompts/</code>")
            self.sync_status_label.setText(f"Pushed {count} markdown files ✓")
            self.sync_completed.emit("push")
        except Exception as e:
            QMessageBox.critical(self, "Push failed", f"Failed to push markdown files:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self.push_individual_btn.setEnabled(True)
            self.push_individual_btn.setText("📄 Push as Markdown Files")

    def _on_close_attempt(self):
        # Ensure polling stopped
        if self._poll_thread and self._poll_thread.isRunning():
            self._cancel_device_flow()
        # Persist branch/path
        try:
            self._save_repo_settings()
        except Exception:
            pass
        self.reject()

    def closeEvent(self, event):
        self._cancel_device_flow(silent=True)
        super().closeEvent(event)
