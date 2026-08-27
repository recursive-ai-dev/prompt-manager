"""Main application window uniting sidebar, prompt list, editor, and preview."""

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

from prompt_manager.config import APP_DISPLAY_NAME, APP_VERSION, DATABASE_PATH, APP_DATA_DIR
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
from prompt_manager.ui.theme import DARK_STYLESHEET


class MainWindow(QMainWindow):
    """Primary window layout for Prompt Manager."""

    def __init__(self, db: Optional[Database] = None):
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1280, 800)
        self.setStyleSheet(DARK_STYLESHEET)

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
        self._load_initial_state()

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

    def _update_status_bar(self, count: int = 0):
        self.status_bar.showMessage(f"Prompts: {count}  |  Database: {DATABASE_PATH}")

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
            "<tr><td><b>Ctrl + D</b></td><td>Duplicate current prompt</td></tr>"
            "<tr><td><b>Ctrl + Q</b></td><td>Exit Prompt Manager</td></tr>"
            "</table>"
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
