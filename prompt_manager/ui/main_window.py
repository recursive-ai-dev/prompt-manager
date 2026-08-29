"""Main application window uniting sidebar, prompt list, editor, and preview."""

from datetime import datetime
import json
from pathlib import Path
from typing import Optional
import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.config import (
    APP_DISPLAY_NAME,
    APP_VERSION,
    DATABASE_PATH,
    APP_DATA_DIR,
    get_theme_id,
    set_theme_id,
    get_github_config,
    is_github_connected,
)
from prompt_manager.core.exporter import (
    format_json_string,
    to_anthropic_payload,
    to_markdown_frontmatter,
    to_openai_payload,
    to_plain_text,
)
from prompt_manager.core.models import Folder, Prompt, PromptRevision
from prompt_manager.core.template_engine import extract_variables, hydrate_template
from prompt_manager.storage.backup import export_library_to_json, import_library_from_json
from prompt_manager.storage.database import Database
from prompt_manager.storage.repository import PromptRepository
from prompt_manager.ui.components.editor import PromptEditorPanel
from prompt_manager.ui.components.preview_panel import PreviewPanel
from prompt_manager.ui.components.prompt_list import PromptListPanel
from prompt_manager.ui.components.revision_modal import RevisionHistoryDialog
from prompt_manager.ui.components.sidebar import SidebarPanel
from prompt_manager.ui.components.toast import ToastNotification
from prompt_manager.ui.components.variable_form import VariableFormWidget
from prompt_manager.ui.theme import get_stylesheet, list_themes, get_theme


class MainWindow(QMainWindow):
    """Primary window layout for Prompt Manager."""

    def __init__(self, db: Optional[Database] = None):
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1280, 800)
        # Load persisted theme, fall back to default
        self._current_theme_id: str = get_theme_id()
        from prompt_manager.ui.theme import THEMES as _THEMES, DEFAULT_THEME as _DEFAULT_THEME

        if self._current_theme_id not in _THEMES:
            self._current_theme_id = _DEFAULT_THEME
        self.setStyleSheet(get_stylesheet(self._current_theme_id))

        # Set App Icon
        icon_path = Path(__file__).parent / "assets" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.db = db or Database()
        self.repo = PromptRepository(self.db)

        self._active_prompt: Optional[Prompt] = None
        self._current_filter_type = "all"
        self._current_filter_id: Optional[str] = None
        self._current_search_query = ""

        self._init_ui()
        self._create_menus()
        self._setup_shortcuts()
        # Sync highlighter to persisted theme (editor created in _init_ui)
        try:
            from prompt_manager.ui.theme import get_highlighter_palette

            palette = get_highlighter_palette(self._current_theme_id)
            if hasattr(self.editor.highlighter, "apply_palette"):
                self.editor.highlighter.apply_palette(palette)
        except Exception:
            pass
        self._load_initial_state()
        # Init GitHub menu enabled state
        try:
            self._update_github_menu_state()
        except Exception:
            pass

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main 3-column Splitter: Sidebar | List | (Editor & Preview)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Sidebar
        self.sidebar = SidebarPanel(self)
        self.sidebar.filter_changed.connect(self._on_filter_changed)
        self.sidebar.create_folder_requested.connect(self._on_create_folder)
        self.sidebar.rename_folder_requested.connect(self._on_rename_folder)
        self.sidebar.delete_folder_requested.connect(self._on_delete_folder)
        self.sidebar.delete_tag_requested.connect(self._on_delete_tag)
        self.main_splitter.addWidget(self.sidebar)

        # 2. Prompt List
        self.prompt_list = PromptListPanel(self)
        self.prompt_list.prompt_selected.connect(self._on_prompt_selected)
        self.prompt_list.new_prompt_requested.connect(self._on_new_prompt)
        self.prompt_list.delete_prompt_requested.connect(self._on_delete_prompt)
        self.prompt_list.duplicate_prompt_requested.connect(self._on_duplicate_prompt)
        self.prompt_list.favorite_toggled.connect(self._on_toggle_favorite)
        self.prompt_list.search_query_changed.connect(self._on_search_changed)
        self.main_splitter.addWidget(self.prompt_list)

        # 3. Editor & Preview container
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Editor Panel
        self.editor = PromptEditorPanel(self)
        self.editor.content_changed.connect(self._on_editor_content_changed)
        self.editor.save_requested.connect(self._on_save_prompt)
        self.editor.delete_requested.connect(lambda: self._on_delete_prompt(self._active_prompt.id if self._active_prompt else None))
        self.editor.history_requested.connect(self._show_revision_history)
        self.content_splitter.addWidget(self.editor)

        # Right-hand variable & preview column
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.var_form = VariableFormWidget(self)
        self.var_form.values_changed.connect(self._on_variables_changed)
        self.right_splitter.addWidget(self.var_form)

        self.preview_panel = PreviewPanel(self)
        self.preview_panel.copy_prompt_requested.connect(self._on_copy_prompt)
        self.preview_panel.copy_json_requested.connect(self._on_copy_json)
        self.preview_panel.export_requested.connect(self._on_export_prompt)
        self.right_splitter.addWidget(self.preview_panel)

        self.right_splitter.setSizes([260, 480])
        right_layout.addWidget(self.right_splitter)

        self.content_splitter.addWidget(right_panel)
        self.content_splitter.setSizes([550, 420])

        self.main_splitter.addWidget(self.content_splitter)
        self.main_splitter.setSizes([220, 280, 780])

        main_layout.addWidget(self.main_splitter)

        # Toast Overlay
        self.toast = ToastNotification(self)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar()

    def _create_menus(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        new_act = QAction("&New Prompt", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.setStatusTip("Create a new prompt template (Ctrl+N)")
        new_act.triggered.connect(self._on_new_prompt)
        file_menu.addAction(new_act)

        save_act = QAction("&Save Revision", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.setStatusTip("Save prompt modifications and record an immutable revision snapshot (Ctrl+S)")
        save_act.triggered.connect(lambda: self._on_save_prompt(create_revision=True))
        file_menu.addAction(save_act)

        file_menu.addSeparator()

        export_lib_act = QAction("Export Library to JSON...", self)
        export_lib_act.setStatusTip("Export all prompts, folders, and tags to a portable JSON file")
        export_lib_act.triggered.connect(self._export_library)
        file_menu.addAction(export_lib_act)

        import_lib_act = QAction("Import Library from JSON...", self)
        import_lib_act.setStatusTip("Import and merge prompts from a JSON backup file")
        import_lib_act.triggered.connect(self._import_library)
        file_menu.addAction(import_lib_act)

        file_menu.addSeparator()

        # ── GitHub Sync submenu (also top-level GitHub menu later) ──
        github_sub = file_menu.addMenu("🔗 GitHub Sync")
        gh_connect = QAction("Connect / Manage GitHub...", self)
        gh_connect.setStatusTip("Connect via OAuth or PAT, choose repository, and configure sync")
        gh_connect.triggered.connect(self._show_github_dialog)
        github_sub.addAction(gh_connect)

        github_sub.addSeparator()

        self.gh_push_act = QAction("⬆ Push Library to GitHub", self)
        self.gh_push_act.setShortcut(QKeySequence("Ctrl+G"))
        self.gh_push_act.setStatusTip("Push entire prompt library to configured GitHub repo (Ctrl+G)")
        self.gh_push_act.triggered.connect(self._github_quick_push)
        github_sub.addAction(self.gh_push_act)

        self.gh_pull_act = QAction("⬇ Pull Library from GitHub", self)
        self.gh_pull_act.setShortcut(QKeySequence("Ctrl+Shift+G"))
        self.gh_pull_act.setStatusTip("Pull library JSON from GitHub and merge (Ctrl+Shift+G)")
        self.gh_pull_act.triggered.connect(self._github_quick_pull)
        github_sub.addAction(self.gh_pull_act)

        github_sub.addSeparator()

        gh_create = QAction("✨ Create New GitHub Repo...", self)
        gh_create.setStatusTip("Create a new repository on GitHub and set it as sync target")
        gh_create.triggered.connect(self._show_github_dialog)
        github_sub.addAction(gh_create)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence("Ctrl+Q"))
        exit_act.setStatusTip("Exit Prompt Manager (Ctrl+Q)")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        search_act = QAction("Search Prompts...", self)
        search_act.setShortcut(QKeySequence("Ctrl+K"))
        search_act.setStatusTip("Focus the prompt search box (Ctrl+K or Ctrl+F)")
        search_act.triggered.connect(self.prompt_list.focus_search)
        edit_menu.addAction(search_act)

        copy_prompt_act = QAction("Copy Hydrated Prompt", self)
        copy_prompt_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_prompt_act.setStatusTip("Copy the compiled prompt text with all variables filled (Ctrl+Shift+C)")
        copy_prompt_act.triggered.connect(self._on_copy_prompt)
        edit_menu.addAction(copy_prompt_act)

        dup_act = QAction("Duplicate Current Prompt", self)
        dup_act.setShortcut(QKeySequence("Ctrl+D"))
        dup_act.setStatusTip("Clone active prompt as a new copy (Ctrl+D)")
        dup_act.triggered.connect(lambda: self._on_duplicate_prompt(self._active_prompt.id if self._active_prompt else None))
        edit_menu.addAction(dup_act)

        edit_menu.addSeparator()

        run_ai_act = QAction("⚡ Run with Free AI (Pollinations)", self)
        run_ai_act.setShortcut(QKeySequence("Ctrl+R"))
        run_ai_act.setStatusTip("Execute the compiled prompt against Pollinations.ai free text endpoint (Ctrl+R)")
        run_ai_act.triggered.connect(self.preview_panel.run_pollinations)
        edit_menu.addAction(run_ai_act)

        # ── Templates Menu — infrastructure for different templates ───
        self.templates_menu = menubar.addMenu("&Templates")
        manage_tmpl_act = QAction("Manage Templates...", self)
        manage_tmpl_act.setShortcut(QKeySequence("Ctrl+Shift+T"))
        manage_tmpl_act.setStatusTip("Open template manager — create/edit/delete reusable prompt templates (infrastructure only, starts empty)")
        manage_tmpl_act.triggered.connect(self._show_template_manager)
        self.templates_menu.addAction(manage_tmpl_act)

        new_tmpl_act = QAction("New Template...", self)
        new_tmpl_act.setStatusTip("Create a new prompt template")
        new_tmpl_act.triggered.connect(self._new_template)
        self.templates_menu.addAction(new_tmpl_act)

        self.templates_menu.addSeparator()

        # Dynamic submenu: Create Prompt from Template (populated on aboutToShow)
        self.use_template_menu = self.templates_menu.addMenu("Use Template → New Prompt")
        self.use_template_menu.setToolTip("Instantiate a new prompt from an existing template")
        # Placeholder; real items populated on show
        self.use_template_menu.aboutToShow.connect(self._populate_use_template_menu)
        self._populate_use_template_menu()  # initial empty state

        self.templates_menu.addSeparator()

        export_tmpl_act = QAction("Export Templates...", self)
        export_tmpl_act.setStatusTip("Export templates to JSON (no prompts)")
        export_tmpl_act.triggered.connect(self._export_templates)
        self.templates_menu.addAction(export_tmpl_act)

        import_tmpl_act = QAction("Import Templates...", self)
        import_tmpl_act.setStatusTip("Import templates from JSON")
        import_tmpl_act.triggered.connect(self._import_templates)
        self.templates_menu.addAction(import_tmpl_act)

        # ── View Menu — Theme selector ───────────────────────────────
        view_menu = menubar.addMenu("&View")
        theme_menu = view_menu.addMenu("🎨 &Theme")

        from PyQt6.QtGui import QActionGroup

        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions: dict = {}

        # Group themes by variant for nicer submenu
        dark_menu = theme_menu.addMenu("🌙 Dark Themes")
        light_menu = theme_menu.addMenu("☀️ Light Themes")

        for theme in list_themes():
            act = QAction(theme.name, self)
            act.setCheckable(True)
            act.setChecked(theme.id == self._current_theme_id)
            act.setStatusTip(theme.description)
            # Use lambda with default arg to capture theme id
            act.triggered.connect(lambda checked, tid=theme.id: self._apply_theme(tid))
            self._theme_group.addAction(act)
            self._theme_actions[theme.id] = act
            if theme.variant == "dark":
                dark_menu.addAction(act)
            else:
                light_menu.addAction(act)

        view_menu.addSeparator()
        # Quick toggle light/dark fallback
        toggle_act = QAction("Toggle Light/Dark", self)
        toggle_act.setShortcut(QKeySequence("Ctrl+T"))
        toggle_act.setStatusTip("Quick toggle between Midnight Dark and Midnight Light (Ctrl+T)")
        toggle_act.triggered.connect(self._toggle_light_dark)
        view_menu.addAction(toggle_act)

        # ── GitHub Menu ───────────────────────────────────────────────
        github_menu = menubar.addMenu("🔗 &GitHub")

        gh_manage_act = QAction("Connect / Manage GitHub...", self)
        gh_manage_act.setStatusTip("Open GitHub connection dialog — OAuth or PAT, repository & sync settings")
        gh_manage_act.triggered.connect(self._show_github_dialog)
        github_menu.addAction(gh_manage_act)

        github_menu.addSeparator()

        # Reuse same actions for top-level menu (Qt supports adding same QAction to multiple menus)
        github_menu.addAction(self.gh_push_act)
        github_menu.addAction(self.gh_pull_act)

        github_menu.addSeparator()

        gh_status_act = QAction("Sync Status...", self)
        gh_status_act.setStatusTip("Show last sync time, target repo, and branch")
        gh_status_act.triggered.connect(self._show_github_status)
        github_menu.addAction(gh_status_act)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        shortcuts_act = QAction("Keyboard &Shortcuts", self)
        shortcuts_act.setStatusTip("Show list of keyboard shortcuts")
        shortcuts_act.triggered.connect(self._show_shortcuts_dialog)
        help_menu.addAction(shortcuts_act)

        about_act = QAction("&About Prompt Manager", self)
        about_act.setStatusTip("View application version and system storage details")
        about_act.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_act)

    def _setup_shortcuts(self):
        # Additional search shortcut Ctrl+F
        search_f = QAction(self)
        search_f.setShortcut(QKeySequence("Ctrl+F"))
        search_f.triggered.connect(self.prompt_list.focus_search)
        self.addAction(search_f)

    # ── Theme handling ───────────────────────────────────────────────
    def _apply_theme(self, theme_id: str) -> None:
        """Apply a theme stylesheet, persist choice, and refresh highlighter."""
        self._current_theme_id = theme_id
        self.setStyleSheet(get_stylesheet(theme_id))
        # Persist
        try:
            set_theme_id(theme_id)
        except Exception:
            pass
        # Update syntax highlighter colors to match theme
        try:
            from prompt_manager.ui.theme import get_highlighter_palette

            palette = get_highlighter_palette(theme_id)
            if hasattr(self.editor, "highlighter") and hasattr(self.editor.highlighter, "apply_palette"):
                self.editor.highlighter.apply_palette(palette)
            elif hasattr(self.editor, "highlighter"):
                self.editor.highlighter.rehighlight()
        except Exception:
            pass
        # Update checked state in menu
        try:
            for tid, act in self._theme_actions.items():
                act.setChecked(tid == theme_id)
        except Exception:
            pass

        theme_name = get_theme(theme_id).name
        self.toast.show_message(f"Theme: {theme_name} ✨")
        self._update_status_bar()

    def _toggle_light_dark(self) -> None:
        """Quick toggle between the default dark and light themes."""
        if self._current_theme_id == "midnight_dark":
            self._apply_theme("midnight_light")
        elif self._current_theme_id == "midnight_light":
            self._apply_theme("midnight_dark")
        else:
            # Toggle based on current variant
            current = get_theme(self._current_theme_id)
            if current.variant == "dark":
                self._apply_theme("midnight_light")
            else:
                self._apply_theme("midnight_dark")

    def get_current_theme_id(self) -> str:
        return self._current_theme_id

    def _load_initial_state(self):
        self._refresh_folders_and_tags()
        self._refresh_prompts_list()

    def _refresh_folders_and_tags(self):
        folders = self.repo.list_folders()
        tags = self.repo.list_tags()
        self.sidebar.set_data(folders, tags)
        self.editor.set_folders(folders)

    def _refresh_prompts_list(self, select_id: Optional[str] = None):
        folder_id = self._current_filter_id if self._current_filter_type == "folder" else None
        tag_id = self._current_filter_id if self._current_filter_type == "tag" else None
        fav_only = self._current_filter_type == "favorite"

        prompts = self.repo.list_prompts(
            folder_id=folder_id,
            tag_id=tag_id,
            favorite_only=fav_only,
            search_query=self._current_search_query,
        )

        target_select = select_id or (self._active_prompt.id if self._active_prompt else None)
        self.prompt_list.set_prompts(prompts, select_id=target_select)
        self._update_status_bar(len(prompts))

    def _update_status_bar(self, count: Optional[int] = None):
        if count is None and hasattr(self, "repo"):
            try:
                count = len(self.repo.list_prompts())
            except Exception:
                count = 0
        elif count is None:
            count = 0
        gh = get_github_config()
        gh_part = ""
        if gh.get("repo"):
            gh_part = f"  |  GitHub: {gh['repo']}@{gh.get('branch','main')} {'●' if gh.get('connected') else '○'}"
            if gh.get("last_sync"):
                gh_part += f" (last sync {gh['last_sync'][:16]})"
        self.status_bar.showMessage(f"Prompts: {count}  |  Database: {DATABASE_PATH}{gh_part}")

    # ------------------ Slot Handlers ------------------

    def _on_filter_changed(self, filter_type: str, target_id: Optional[str]):
        self._current_filter_type = filter_type
        self._current_filter_id = target_id
        self._refresh_prompts_list()

    def _on_search_changed(self, query: str):
        self._current_search_query = query
        self._refresh_prompts_list()

    def _on_prompt_selected(self, prompt_id: str):
        prompt = self.repo.get_prompt_by_id(prompt_id)
        if prompt:
            self._active_prompt = prompt
            self.editor.load_prompt(prompt)
            self._update_preview()

    def _on_new_prompt(self):
        new_p = Prompt(
            id=str(uuid.uuid4()),
            title="New Prompt",
            folder_id=self._current_filter_id if self._current_filter_type == "folder" else None,
            template_content="Write your prompt here {{variable_name}}...",
            system_instruction="",
            target_model="General",
        )
        self.repo.save_prompt(new_p)
        self._active_prompt = new_p
        self._refresh_prompts_list(select_id=new_p.id)
        self.editor.title_input.setFocus()
        self.editor.title_input.selectAll()
        self.toast.show_message("Created new prompt")

    def _on_save_prompt(self, create_revision: bool = False):
        if not self._active_prompt:
            return
        self.editor.update_prompt_model(self._active_prompt)
        self.repo.save_prompt(self._active_prompt, create_revision=create_revision)
        self.editor.mark_saved()
        if create_revision:
            self._refresh_prompts_list(select_id=self._active_prompt.id)
            self.toast.show_message("Saved snapshot revision!")
        else:
            self.prompt_list.update_prompt_item(self._active_prompt)

    def _on_delete_prompt(self, prompt_id: Optional[str]):
        target_id = prompt_id or (self._active_prompt.id if self._active_prompt else None)
        if not target_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this prompt?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete_prompt(target_id)
            self._active_prompt = None
            self._refresh_prompts_list()
            self.toast.show_message("Prompt deleted")

    def _on_duplicate_prompt(self, prompt_id: Optional[str]):
        target_id = prompt_id or (self._active_prompt.id if self._active_prompt else None)
        if not target_id:
            return
        original = self.repo.get_prompt_by_id(target_id)
        if not original:
            return

        duplicated = Prompt(
            id=str(uuid.uuid4()),
            title=f"{original.title} (Copy)",
            description=original.description,
            folder_id=original.folder_id,
            template_content=original.template_content,
            system_instruction=original.system_instruction,
            target_model=original.target_model,
            temperature=original.temperature,
            tags=list(original.tags),
        )
        self.repo.save_prompt(duplicated)
        self._refresh_prompts_list(select_id=duplicated.id)
        self.toast.show_message("Prompt duplicated")

    def _on_toggle_favorite(self, prompt_id: str):
        is_fav = self.repo.toggle_favorite(prompt_id)
        self._refresh_prompts_list(select_id=prompt_id)
        msg = "Added to favorites ⭐" if is_fav else "Removed from favorites"
        self.toast.show_message(msg)

    def _on_editor_content_changed(self):
        if not self._active_prompt:
            return
        template = self.editor.get_template_content()
        specs = extract_variables(template)
        self.var_form.set_variables(specs)
        self._update_preview()

    def _on_variables_changed(self, values: dict):
        self._update_preview()

    def _update_preview(self):
        if not self._active_prompt:
            self.preview_panel.set_content("")
            return
        template = self.editor.get_template_content()
        values = self.var_form.get_values()
        hydrated = hydrate_template(template, values, fallback_to_defaults=True)
        self.preview_panel.set_content(hydrated)
        self.preview_panel.set_context_metadata(
            system_instruction=self.editor.get_system_instruction(),
            temperature=float(self.editor.temp_spin.value()),
        )

    def _on_copy_prompt(self):
        hydrated = self.preview_panel.get_content()
        if not hydrated:
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(hydrated)
        if self._active_prompt:
            self.repo.increment_use_count(self._active_prompt.id)
        self.toast.show_message("Prompt copied to clipboard! 📋")

    def _on_copy_json(self):
        if not self._active_prompt:
            return
        hydrated = self.preview_panel.get_content()
        if "claude" in self._active_prompt.target_model.lower():
            payload = to_anthropic_payload(self._active_prompt, hydrated)
        else:
            payload = to_openai_payload(self._active_prompt, hydrated)
        formatted_json = format_json_string(payload)
        QGuiApplication.clipboard().setText(formatted_json)
        self.toast.show_message("API JSON payload copied! 📋")

    def _on_export_prompt(self, format_type: str):
        if not self._active_prompt:
            return
        hydrated = self.preview_panel.get_content()

        filters = {
            "markdown": "Markdown Files (*.md)",
            "openai": "JSON Files (*.json)",
            "anthropic": "JSON Files (*.json)",
            "text": "Text Files (*.txt)",
        }
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Prompt",
            f"{self._active_prompt.title}.{'md' if format_type == 'markdown' else 'json' if 'json' in format_type or format_type in ('openai', 'anthropic') else 'txt'}",
            filters.get(format_type, "All Files (*)"),
        )
        if not filename:
            return

        if format_type == "markdown":
            data = to_markdown_frontmatter(self._active_prompt, hydrated)
        elif format_type == "openai":
            data = format_json_string(to_openai_payload(self._active_prompt, hydrated))
        elif format_type == "anthropic":
            data = format_json_string(to_anthropic_payload(self._active_prompt, hydrated))
        else:
            data = to_plain_text(self._active_prompt, hydrated)

        Path(filename).write_text(data, encoding="utf-8")
        self.toast.show_message("Exported successfully!")

    def _show_revision_history(self):
        if not self._active_prompt:
            return
        revisions = self.repo.get_revisions(self._active_prompt.id)
        dialog = RevisionHistoryDialog(revisions, self)
        dialog.revision_restored.connect(self._restore_revision)
        dialog.exec()

    def _restore_revision(self, rev: PromptRevision):
        if not self._active_prompt:
            return
        self._active_prompt.title = rev.title
        self._active_prompt.system_instruction = rev.system_instruction
        self._active_prompt.template_content = rev.template_content
        self.editor.load_prompt(self._active_prompt)
        self.repo.save_prompt(self._active_prompt, create_revision=True)
        self.toast.show_message(f"Restored revision #{rev.revision_number}")

    def _on_create_folder(self, folder_name: str):
        new_folder = Folder(name=folder_name)
        self.repo.save_folder(new_folder)
        self._refresh_folders_and_tags()
        self.toast.show_message(f"Created folder '{folder_name}'")

    def _on_rename_folder(self, folder_id: str, new_name: str):
        folders = self.repo.list_folders()
        target = next((f for f in folders if f.id == folder_id), None)
        if target:
            target.name = new_name
            self.repo.save_folder(target)
            self._refresh_folders_and_tags()
            self._refresh_prompts_list()
            self.toast.show_message(f"Renamed folder to '{new_name}'")

    def _on_delete_folder(self, folder_id: str):
        self.repo.delete_folder(folder_id)
        self._refresh_folders_and_tags()
        self._refresh_prompts_list()
        self.toast.show_message("Folder deleted")

    def _on_delete_tag(self, tag_id: str):
        self.repo.delete_tag(tag_id)
        self._refresh_folders_and_tags()
        self._refresh_prompts_list()
        self.toast.show_message("Tag deleted")

    def _export_library(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Prompt Library", "prompt_library.json", "JSON Files (*.json)"
        )
        if filename:
            count = export_library_to_json(self.repo, Path(filename))
            self.toast.show_message(f"Exported {count} prompts!")

    def _import_library(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Prompt Library", "", "JSON Files (*.json)"
        )
        if filename:
            count = import_library_from_json(self.repo, Path(filename))
            self._refresh_folders_and_tags()
            self._refresh_prompts_list()
            self.toast.show_message(f"Imported {count} prompts!")

    # ── GitHub Integration ──────────────────────────────────────────

    def _show_github_dialog(self):
        """Open the GitHub connection & sync dialog."""
        try:
            from prompt_manager.ui.components.github_dialog import GithubDialog

            dialog = GithubDialog(self, repo=self.repo)
            dialog.sync_completed.connect(self._on_github_sync_completed)
            dialog.exec()
            self._update_status_bar()
            self._update_github_menu_state()
        except Exception as e:
            QMessageBox.critical(self, "GitHub dialog error", f"Failed to open GitHub dialog:\n{e}")

    def _on_github_sync_completed(self, action: str):
        """Refresh UI after push/pull via dialog."""
        self._refresh_folders_and_tags()
        self._refresh_prompts_list()
        self._update_status_bar()
        if action == "pull":
            self.toast.show_message("GitHub pull merged ✓")
        elif action == "push":
            self.toast.show_message("GitHub push complete ✓")

    def _github_quick_push(self):
        """Quick push without opening dialog — uses stored config; prompts for dialog if not configured."""
        gh = get_github_config()
        if not gh.get("token") or not gh.get("repo"):
            reply = QMessageBox.question(
                self,
                "GitHub not configured",
                "No GitHub repository configured.\n\nOpen GitHub connection dialog to set up push target?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._show_github_dialog()
            return
        # Validate config
        from prompt_manager.core.github_sync import validate_github_config, push_library_via_api
        from prompt_manager.integrations.github_client import GithubClient, GithubError

        err = validate_github_config(gh["repo"], gh.get("branch", "main"), gh.get("file_path", "prompt-library.json"))
        if err:
            QMessageBox.warning(self, "GitHub config error", err + "\n\nOpen GitHub dialog to fix.")
            self._show_github_dialog()
            return

        reply = QMessageBox.question(
            self,
            "Push to GitHub",
            f"Push <b>{len(self.repo.list_prompts())} prompts</b> to <b>{gh['repo']}</b><br>"
            f"Branch: <code>{gh.get('branch','main')}</code> • Path: <code>{gh.get('file_path','prompt-library.json')}</code><br><br>"
            "This will create or update the file on GitHub.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_bar.showMessage("Pushing to GitHub…")
        try:
            client = GithubClient(gh["token"])
            result = push_library_via_api(
                self.repo,
                client,
                gh["repo"],
                branch=gh.get("branch", "main"),
                file_path=gh.get("file_path", "prompt-library.json"),
            )
            sha = ""
            if isinstance(result.get("commit"), dict):
                sha = result["commit"].get("sha", "")[:7]
            elif isinstance(result.get("content"), dict):
                sha = result["content"].get("sha", "")[:7]
            set_github_config({"last_sync": datetime.now().isoformat(), "last_sync_sha": sha})
            self.toast.show_message(f"Pushed to GitHub @ {sha} ✓")
            self._update_status_bar()
        except GithubError as e:
            QMessageBox.critical(self, "Push failed", f"GitHub push failed:\n{e}\nStatus: {e.status or '—'}\n\nCheck token scope (needs `repo`) and network connectivity.")
        except Exception as e:
            QMessageBox.critical(self, "Push failed", f"Unexpected error:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._update_status_bar()

    def _github_quick_pull(self):
        gh = get_github_config()
        if not gh.get("token") or not gh.get("repo"):
            reply = QMessageBox.question(
                self,
                "GitHub not configured",
                "No GitHub repository configured.\n\nOpen GitHub connection dialog to set up?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._show_github_dialog()
            return
        from prompt_manager.core.github_sync import validate_github_config, pull_library_via_api
        from prompt_manager.integrations.github_client import GithubClient, GithubError

        err = validate_github_config(gh["repo"], gh.get("branch", "main"), gh.get("file_path", "prompt-library.json"))
        if err:
            QMessageBox.warning(self, "GitHub config error", err)
            return

        reply = QMessageBox.question(
            self,
            "Pull from GitHub",
            f"Pull library from <b>{gh['repo']}</b><br>"
            f"Branch: <code>{gh.get('branch','main')}</code> • Path: <code>{gh.get('file_path','prompt-library.json')}</code><br><br>"
            "This will merge prompts from GitHub into your local library.<br>Existing IDs will be overwritten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_bar.showMessage("Pulling from GitHub…")
        try:
            client = GithubClient(gh["token"])
            count, info = pull_library_via_api(
                self.repo,
                client,
                gh["repo"],
                branch=gh.get("branch", "main"),
                file_path=gh.get("file_path", "prompt-library.json"),
            )
            self._refresh_folders_and_tags()
            self._refresh_prompts_list()
            self.toast.show_message(f"Pulled {count} prompts from GitHub ✓")
            self._update_status_bar()
            QMessageBox.information(self, "Pull complete", f"✅ Imported {count} prompts from GitHub.")
        except GithubError as e:
            QMessageBox.critical(self, "Pull failed", f"GitHub pull failed:\n{e}\nStatus: {e.status or '—'}")
        except Exception as e:
            QMessageBox.critical(self, "Pull failed", f"Unexpected error:\n{e}")
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._update_status_bar()

    def _show_github_status(self):
        gh = get_github_config()
        if not gh.get("token"):
            msg = (
                "<h3>GitHub Sync — Not Connected</h3>"
                "<p>No token configured. Connect via <b>GitHub → Connect / Manage</b></p>"
                f"<p><b>Database:</b> {DATABASE_PATH}</p>"
            )
        else:
            user = gh.get("username", "unknown")
            repo = gh.get("repo", "— none selected —")
            branch = gh.get("branch", "main")
            path = gh.get("file_path", "prompt-library.json")
            last = gh.get("last_sync", "never")
            sha = gh.get("last_sync_sha", "")
            avatar = gh.get("avatar_url", "")
            msg = (
                f"<h3>GitHub Sync — Connected as {user}</h3>"
                f"<p><b>Repository:</b> <code>{repo}</code><br>"
                f"<b>Branch:</b> <code>{branch}</code><br>"
                f"<b>File:</b> <code>{path}</code><br>"
                f"<b>Last sync:</b> {last} {f'(@{sha})' if sha else ''}</p>"
                f"<p><b>Token type:</b> {gh.get('token_type','—')} • <b>Local prompts:</b> {len(self.repo.list_prompts())}</p>"
            )
            if avatar:
                msg += f"<p><a href='https://github.com/{user}'>View {user} on GitHub</a></p>"
        msg += (
            "<hr><p style='font-size:11px;color:#64748b;'>"
            "Push updates your GitHub file, Pull merges remote into local.<br>"
            "Use <b>GitHub → Connect / Manage</b> to change repo, use OAuth or rotate PAT.</p>"
        )
        QMessageBox.information(self, "GitHub Sync Status", msg)

    def _update_github_menu_state(self):
        """Enable/disable push/pull actions based on connection."""
        gh = get_github_config()
        connected = bool(gh.get("token") and gh.get("repo"))
        try:
            self.gh_push_act.setEnabled(connected)
            self.gh_pull_act.setEnabled(connected)
        except Exception:
            pass

    # ── Template Infrastructure ───────────────────────────────────

    def _show_template_manager(self):
        """Open the template manager dialog (infrastructure only, no seed data)."""
        try:
            from prompt_manager.ui.components.template_manager import TemplateManagerDialog

            dialog = TemplateManagerDialog(self.repo, self)
            dialog.use_template_requested.connect(self._instantiate_prompt_from_template)
            dialog.exec()
            # Refresh dynamic menu after dialog closes (templates may have been added/renamed)
            self._populate_use_template_menu()
            self._update_status_bar()
        except Exception as e:
            QMessageBox.critical(self, "Template manager error", f"Failed to open template manager:\n{e}")

    def _new_template(self):
        """Shortcut: open manager and immediately trigger 'New Template'."""
        try:
            from prompt_manager.ui.components.template_manager import TemplateManagerDialog

            dialog = TemplateManagerDialog(self.repo, self)
            dialog.use_template_requested.connect(self._instantiate_prompt_from_template)
            # Trigger new immediately after showing
            dialog.show()
            dialog._on_new()
            dialog.exec()
            self._populate_use_template_menu()
            self._update_status_bar()
        except Exception as e:
            QMessageBox.critical(self, "New template error", str(e))

    def _populate_use_template_menu(self):
        """Rebuild 'Use Template → New Prompt' submenu from DB (empty if no templates)."""
        try:
            self.use_template_menu.clear()
            templates = self.repo.list_templates()
            if not templates:
                placeholder = QAction("(no templates — Create one via Manage Templates)", self)
                placeholder.setEnabled(False)
                self.use_template_menu.addAction(placeholder)
                return
            # Group by category
            from collections import defaultdict

            by_cat: dict[str, list] = defaultdict(list)
            for t in templates:
                by_cat[t.category].append(t)
            for cat in sorted(by_cat.keys()):
                if len(by_cat) > 1:
                    cat_menu = self.use_template_menu.addMenu(f"{cat.title()}")
                    for tmpl in sorted(by_cat[cat], key=lambda x: x.name.lower()):
                        act = QAction(tmpl.name, self)
                        act.setToolTip(f"{tmpl.description}\nCategory: {tmpl.category}\nClick to create a new prompt from this template")
                        act.triggered.connect(lambda checked, tid=tmpl.id: self._instantiate_prompt_from_template(tid))
                        cat_menu.addAction(act)
                else:
                    for tmpl in sorted(by_cat[cat], key=lambda x: x.name.lower()):
                        act = QAction(f"{tmpl.name}  [{tmpl.category}]", self)
                        act.setToolTip(tmpl.description or f"Category: {tmpl.category}")
                        act.triggered.connect(lambda checked, tid=tmpl.id: self._instantiate_prompt_from_template(tid))
                        self.use_template_menu.addAction(act)
        except Exception:
            pass

    def _instantiate_prompt_from_template(self, template_id: str) -> None:
        """Create a new Prompt from a Template and open it in the editor."""
        try:
            prompt = self.repo.create_prompt_from_template(template_id)
            self._active_prompt = prompt
            self._refresh_prompts_list(select_id=prompt.id)
            self.editor.load_prompt(prompt)
            self._update_preview()
            # Select the new prompt's folder if any
            tmpl = self.repo.get_template_by_id(template_id)
            name = tmpl.name if tmpl else template_id
            self.toast.show_message(f"Created prompt from template '{name}' ✨")
        except Exception as e:
            QMessageBox.warning(self, "Instantiate failed", str(e))

    def _export_templates(self):
        """Export templates only to JSON."""
        import json as _json

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Templates", "prompt_templates.json", "JSON Files (*.json)"
        )
        if not filename:
            return
        templates = self.repo.list_templates()
        data = {
            "version": "1.1",
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "content": t.content,
                    "system_instruction": t.system_instruction,
                    "category": t.category,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                }
                for t in templates
            ],
        }
        Path(filename).write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.toast.show_message(f"Exported {len(templates)} templates")

    def _import_templates(self):
        import json as _json

        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Templates", "", "JSON Files (*.json)"
        )
        if not filename:
            return
        try:
            data = _json.loads(Path(filename).read_text(encoding="utf-8"))
            items = data.get("templates") if "templates" in data else data if isinstance(data, list) else []
            count = 0
            for td in items or []:
                from prompt_manager.core.models import PromptTemplate

                # Support both wrapped and plain list formats
                if not isinstance(td, dict) or "name" not in td:
                    continue
                try:
                    self.repo.save_template(
                        PromptTemplate(
                            id=td.get("id") or str(uuid.uuid4()),
                            name=td.get("name", "Untitled"),
                            description=td.get("description", ""),
                            content=td.get("content", ""),
                            system_instruction=td.get("system_instruction", ""),
                            category=td.get("category", "general"),
                            created_at=td.get("created_at", ""),
                            updated_at=td.get("updated_at", ""),
                        )
                    )
                    count += 1
                except Exception:
                    continue
            self._populate_use_template_menu()
            self._update_status_bar()
            QMessageBox.information(self, "Import complete", f"Imported {count} templates")
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))

    def import_file_from_cli(self, filepath: Path):
        """Open or import a file passed as a CLI argument."""
        if not filepath.exists():
            return
        try:
            content = filepath.read_text(encoding="utf-8")
            if filepath.suffix.lower() == ".json":
                try:
                    data = json.loads(content)
                    if "prompts" in data:
                        count = import_library_from_json(self.repo, filepath)
                        self._refresh_folders_and_tags()
                        self._refresh_prompts_list()
                        self.toast.show_message(f"Imported library ({count} prompts)")
                        return
                except Exception:
                    pass

            title = filepath.stem.replace("-", " ").replace("_", " ").title()
            prompt = Prompt(
                id=str(uuid.uuid4()),
                title=title,
                template_content=content,
            )
            self.repo.save_prompt(prompt)
            self._refresh_prompts_list(select_id=prompt.id)
            self.toast.show_message(f"Loaded prompt: {title}")
        except Exception as e:
            self.toast.show_message(f"Failed to open file: {e}")

    def _show_shortcuts_dialog(self):
        msg = (
            "<h3>Keyboard Shortcuts</h3>"
            "<table border='0' cellpadding='4' cellspacing='2'>"
            "<tr><td><b>Ctrl + N</b></td><td>Create a new prompt</td></tr>"
            "<tr><td><b>Ctrl + S</b></td><td>Save prompt revision snapshot</td></tr>"
            "<tr><td><b>Ctrl + K</b> or <b>Ctrl + F</b></td><td>Focus search bar</td></tr>"
            "<tr><td><b>Ctrl + Shift + C</b></td><td>Copy compiled prompt to clipboard</td></tr>"
            "<tr><td><b>Ctrl + R</b></td><td>Run / test prompt with free AI (Pollinations)</td></tr>"
            "<tr><td><b>Ctrl + D</b></td><td>Duplicate current prompt</td></tr>"
            "<tr><td><b>Ctrl + Shift + T</b></td><td>Manage prompt templates</td></tr>"
            "<tr><td><b>Ctrl + G</b></td><td>Push library to GitHub</td></tr>"
            "<tr><td><b>Ctrl + Shift + G</b></td><td>Pull library from GitHub</td></tr>"
            "<tr><td><b>Ctrl + T</b></td><td>Toggle light / dark theme</td></tr>"
            "<tr><td><b>Ctrl + Q</b></td><td>Exit Prompt Manager</td></tr>"
            "</table>"
            "<p style='font-size:11px; color:#64748b;'>Templates: <b>Templates → Manage Templates</b> (starts empty). "
            "Themes via <b>View → Theme</b> (13 themes). Current: <b>"
            + get_theme(self._current_theme_id).name
            + "</b></p>"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", msg)

    def _show_about_dialog(self):
        msg = (
            f"<h3>{APP_DISPLAY_NAME} v{APP_VERSION}</h3>"
            "<p>A native Linux desktop application to store, organize, template, and deploy AI prompts.</p>"
            f"<p><b>Database:</b><br><code>{DATABASE_PATH}</code></p>"
            f"<p><b>Data Directory:</b><br><code>{APP_DATA_DIR}</code></p>"
            "<p>Built with Python 3 and PyQt6 for KDE Plasma / Wayland / X11.</p>"
        )
        QMessageBox.information(self, f"About {APP_DISPLAY_NAME}", msg)
