"""Template Manager dialog — infrastructure for creating different prompt templates.

No default templates are seeded; the dialog starts empty and provides full
CRUD (create, rename, edit, delete, duplicate, search) plus instantiation
of a Prompt from a Template (`Use Template → New Prompt`).

This module deliberately contains only infrastructure — no prepopulated data.
The `prompt_templates` table is created empty via `Database._init_db` and
`Repository.list_templates()` will return [] on a fresh install.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.models import PromptTemplate
from prompt_manager.core.template_engine import check_syntax_errors
from prompt_manager.storage.repository import PromptRepository
from prompt_manager.ui.components.highlighter import PromptSyntaxHighlighter
from prompt_manager.ui.components.toast import ToastNotification


CATEGORY_CHOICES = [
    "general",
    "coding",
    "writing",
    "chat",
    "summarization",
    "analysis",
    "creative",
    "tool-use",
    "custom",
]


class TemplateEditorWidget(QWidget):
    """Right-hand editor for a single PromptTemplate (name, category, content, etc.)."""

    content_changed = pyqtSignal()
    save_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current: Optional[PromptTemplate] = None
        self._suppress = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top bar: name + save/delete
        top = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Template name (unique, e.g. 'code-review')")
        self.name_input.setObjectName("titleInput")
        self.name_input.textChanged.connect(self._on_modified)
        top.addWidget(self.name_input, stretch=1)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self.save_requested.emit)
        top.addWidget(self.save_btn)

        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        top.addWidget(self.delete_btn)

        layout.addLayout(top)

        # Description + category row
        meta = QHBoxLayout()
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Brief description (optional, searchable)")
        self.desc_input.textChanged.connect(self._on_modified)
        meta.addWidget(self.desc_input, stretch=1)

        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        meta.addWidget(cat_lbl)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(CATEGORY_CHOICES)
        self.category_combo.currentTextChanged.connect(self._on_modified)
        meta.addWidget(self.category_combo)

        layout.addLayout(meta)

        # System instruction (collapsible)
        self.sys_toggle = QPushButton("▶ System Instruction (Optional)")
        self.sys_toggle.setStyleSheet("text-align: left; border: none; background: transparent; color: #94a3b8; font-weight: 600;")
        self.sys_toggle.clicked.connect(self._toggle_system)
        layout.addWidget(self.sys_toggle)

        self.system_edit = QPlainTextEdit()
        self.system_edit.setPlaceholderText("System instruction / persona for this template (optional)...")
        self.system_edit.setMaximumHeight(80)
        self.system_edit.textChanged.connect(self._on_modified)
        self.system_edit.hide()
        layout.addWidget(self.system_edit)

        # Content label + syntax alert
        hdr = QHBoxLayout()
        lbl = QLabel("TEMPLATE CONTENT")
        lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        hdr.addWidget(lbl)
        self.syntax_alert = QLabel("")
        self.syntax_alert.setStyleSheet("color: #f87171; font-size: 11px;")
        hdr.addWidget(self.syntax_alert)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText(
            "Template body with {{variables}}.\n"
            "Examples: {{topic}}, {{tone:formal|options:casual,formal,brief}}, {{code|multiline}}"
        )
        mono = QFont("monospace", 10)
        self.content_edit.setFont(mono)
        self.content_edit.textChanged.connect(self._on_content_modified)
        # Theme-aware highlighter (fallback to default if theme unavailable)
        try:
            from prompt_manager.config import get_theme_id
            from prompt_manager.ui.theme import get_highlighter_palette

            _pal = get_highlighter_palette(get_theme_id())
        except Exception:
            _pal = None
        self.highlighter = PromptSyntaxHighlighter(self.content_edit.document(), palette=_pal)
        layout.addWidget(self.content_edit, stretch=1)

        # Variable hint line (auto-extracted)
        self.vars_hint = QLabel("")
        self.vars_hint.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        self.vars_hint.setWordWrap(True)
        layout.addWidget(self.vars_hint)

        self.setEnabled(False)

    def load_template(self, tmpl: PromptTemplate) -> None:
        self._suppress = True
        self._current = tmpl
        self.setEnabled(True)
        self.name_input.setText(tmpl.name)
        self.desc_input.setText(tmpl.description or "")
        # Ensure category appears in combo
        if tmpl.category and tmpl.category not in [self.category_combo.itemText(i) for i in range(self.category_combo.count())]:
            self.category_combo.addItem(tmpl.category)
        self.category_combo.setCurrentText(tmpl.category or "general")
        if tmpl.system_instruction:
            self.system_edit.setPlainText(tmpl.system_instruction)
            self.system_edit.show()
            self.sys_toggle.setText("▼ System Instruction (Optional)")
        else:
            self.system_edit.setPlainText("")
            self.system_edit.hide()
            self.sys_toggle.setText("▶ System Instruction (Optional)")
        self.content_edit.setPlainText(tmpl.content or "")
        self._update_vars_hint()
        self._check_syntax()
        self._suppress = False

    def clear(self) -> None:
        self._suppress = True
        self._current = None
        self.setEnabled(False)
        self.name_input.clear()
        self.desc_input.clear()
        self.category_combo.setCurrentText("general")
        self.system_edit.clear()
        self.system_edit.hide()
        self.content_edit.clear()
        self.vars_hint.clear()
        self.syntax_alert.clear()
        self._suppress = False

    def update_model(self, tmpl: PromptTemplate) -> None:
        tmpl.name = self.name_input.text().strip()
        tmpl.description = self.desc_input.text().strip()
        tmpl.category = self.category_combo.currentText().strip().lower() or "general"
        tmpl.system_instruction = self.system_edit.toPlainText().strip()
        tmpl.content = self.content_edit.toPlainText()

    def _toggle_system(self) -> None:
        if self.system_edit.isVisible():
            self.system_edit.hide()
            self.sys_toggle.setText("▶ System Instruction (Optional)")
        else:
            self.system_edit.show()
            self.sys_toggle.setText("▼ System Instruction (Optional)")
            self.system_edit.setFocus()

    def _on_modified(self) -> None:
        if self._suppress:
            return
        self.content_changed.emit()

    def _on_content_modified(self) -> None:
        self._check_syntax()
        self._update_vars_hint()
        self._on_modified()

    def _check_syntax(self) -> None:
        errors = check_syntax_errors(self.content_edit.toPlainText())
        self.syntax_alert.setText(f"⚠ {errors[0]}" if errors else "")

    def _update_vars_hint(self) -> None:
        from prompt_manager.core.template_engine import extract_variables

        specs = extract_variables(self.content_edit.toPlainText() + "\n" + self.system_edit.toPlainText())
        if not specs:
            self.vars_hint.setText("No variables detected — add {{variable}} to parameterize.")
        else:
            parts = []
            for s in specs:
                frag = s.name
                if s.default_value:
                    frag += f":{s.default_value}"
                if s.is_multiline:
                    frag += "|multiline"
                if s.options:
                    frag += f"|options:{','.join(s.options)}"
                parts.append(f"{{{{{frag}}}}}")
            self.vars_hint.setText(f"Variables ({len(specs)}): " + ", ".join(parts))


class TemplateManagerDialog(QDialog):
    """Modal dialog for managing PromptTemplates (CRUD infrastructure).

    - Left: searchable list, new/duplicate/delete.
    - Right: editor form.
    - Signals: template_selected, prompt_create_requested (instantiate).
    """

    # Emitted when user chooses "Use Template → New Prompt"
    use_template_requested = pyqtSignal(str)  # template_id

    def __init__(self, repo: PromptRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self._current_id: Optional[str] = None
        self.setWindowTitle("Manage Templates — Prompt Manager")
        self.resize(920, 580)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  Templates — reusable skeletons for prompts (infrastructure only, starts empty)")
        header.setStyleSheet("padding: 8px 12px; font-weight: 600; color: #94a3b8; border-bottom: 1px solid #232833;")
        header.setWordWrap(True)
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left panel: list + search + buttons
        left = QWidget()
        left.setObjectName("listFrame")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("+ New Template")
        self.new_btn.setObjectName("primaryButton")
        self.new_btn.clicked.connect(self._on_new)
        btn_row.addWidget(self.new_btn)
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._on_duplicate)
        btn_row.addWidget(self.duplicate_btn)
        left_layout.addLayout(btn_row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search templates (name, description, category)...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._refresh_list)
        left_layout.addWidget(self.search_input)

        # Category filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories", "all")
        for c in CATEGORY_CHOICES:
            self.category_filter.addItem(c, c)
        self.category_filter.currentIndexChanged.connect(self._refresh_list)
        filter_row.addWidget(self.category_filter, stretch=1)
        left_layout.addLayout(filter_row)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget, stretch=1)

        # Use template button
        self.use_btn = QPushButton("Use Template → New Prompt")
        self.use_btn.setToolTip("Instantiate a new Prompt from the selected Template (template_id will be stored on the Prompt)")
        self.use_btn.setObjectName("primaryButton")
        self.use_btn.clicked.connect(self._on_use_template)
        self.use_btn.setEnabled(False)
        left_layout.addWidget(self.use_btn)

        splitter.addWidget(left)

        # Right panel: editor
        self.editor = TemplateEditorWidget(self)
        self.editor.content_changed.connect(self._on_editor_dirty)
        self.editor.save_requested.connect(self._on_save)
        self.editor.delete_requested.connect(self._on_delete)
        splitter.addWidget(self.editor)

        splitter.setSizes([300, 620])
        layout.addWidget(splitter, stretch=1)

        # Toast for feedback inside dialog
        self.toast = ToastNotification(self)

        self._refresh_list()

    # ── List handling ───────────────────────────────────────────

    def _refresh_list(self) -> None:
        query = self.search_input.text().strip()
        category = self.category_filter.currentData()
        templates = self.repo.list_templates(category=category, search_query=query)

        # Preserve selection
        prev_id = self._current_id
        self.list_widget.clear()
        target_item = None
        for tmpl in templates:
            label = f"{tmpl.name}  [{tmpl.category}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, tmpl.id)
            # Tooltip with description + vars
            vars_list = ", ".join(s.name for s in tmpl.variable_specs()) or "no variables"
            item.setToolTip(f"{tmpl.name}\n{tmpl.description}\nCategory: {tmpl.category}\nVars: {vars_list}")
            self.list_widget.addItem(item)
            if tmpl.id == prev_id:
                target_item = item

        if target_item:
            self.list_widget.setCurrentItem(target_item)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        else:
            self.editor.clear()
            self._current_id = None
            self.use_btn.setEnabled(False)
            # Empty-state hint
            if not query and (category in (None, "all")):
                # No templates yet — keep editor disabled, user can click New
                pass

    def _on_selection_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if not current:
            self._current_id = None
            self.editor.clear()
            self.use_btn.setEnabled(False)
            return
        tid = current.data(Qt.ItemDataRole.UserRole)
        tmpl = self.repo.get_template_by_id(tid)
        if tmpl:
            self._current_id = tmpl.id
            self.editor.load_template(tmpl)
            self.use_btn.setEnabled(True)

    def _on_editor_dirty(self) -> None:
        # Could enable Save button state; for now we autosave on Save click only
        pass

    # ── CRUD actions ────────────────────────────────────────────

    def _on_new(self) -> None:
        # Default name must be unique — generate incremental
        base = "New Template"
        name = base
        idx = 1
        existing_names = {t.name for t in self.repo.list_templates()}
        while name in existing_names:
            idx += 1
            name = f"{base} {idx}"
        tmpl = PromptTemplate(name=name, description="", content="Hello {{name}}!", category="general")
        try:
            self.repo.save_template(tmpl)
            self._refresh_list()
            # Select the new one
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == tmpl.id:
                    self.list_widget.setCurrentItem(item)
                    break
            self.toast.show_message(f"Created template '{name}'")
        except Exception as e:
            QMessageBox.warning(self, "Create failed", str(e))

    def _on_save(self) -> None:
        if not self._current_id:
            return
        tmpl = self.repo.get_template_by_id(self._current_id)
        if not tmpl:
            return
        old_name = tmpl.name
        self.editor.update_model(tmpl)
        try:
            self.repo.save_template(tmpl)
            self._refresh_list()
            self.toast.show_message(f"Saved '{tmpl.name}'")
        except ValueError as e:
            # Unique name violation etc.
            QMessageBox.warning(self, "Save failed", str(e))
            tmpl.name = old_name  # revert in-memory
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        tmpl = self.repo.get_template_by_id(self._current_id)
        if not tmpl:
            return
        reply = QMessageBox.question(
            self, "Delete Template", f"Delete template '{tmpl.name}'?\n\nPrompts using it will keep their content but lose the link.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.repo.delete_template(tmpl.id):
            self._refresh_list()
            self.toast.show_message("Template deleted")

    def _on_duplicate(self) -> None:
        if not self._current_id:
            QMessageBox.information(self, "Duplicate", "Select a template first.")
            return
        src = self.repo.get_template_by_id(self._current_id)
        if not src:
            return
        # Generate unique name
        base = f"{src.name} (Copy)"
        name = base
        idx = 1
        existing = {t.name for t in self.repo.list_templates()}
        while name in existing:
            idx += 1
            name = f"{base} {idx}"
        copy = PromptTemplate(
            name=name,
            description=src.description,
            content=src.content,
            system_instruction=src.system_instruction,
            category=src.category,
        )
        try:
            self.repo.save_template(copy)
            self._refresh_list()
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == copy.id:
                    self.list_widget.setCurrentItem(self.list_widget.item(i))
                    break
            self.toast.show_message(f"Duplicated as '{name}'")
        except Exception as e:
            QMessageBox.warning(self, "Duplicate failed", str(e))

    def _on_use_template(self) -> None:
        if not self._current_id:
            return
        self.use_template_requested.emit(self._current_id)
        # Keep dialog open so user can continue managing; caller may close or switch to editor

    def _show_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        use_act = menu.addAction("→ Use Template → New Prompt")
        menu.addSeparator()
        dup_act = menu.addAction("Duplicate")
        del_act = menu.addAction("Delete")
        act = menu.exec(self.list_widget.mapToGlobal(pos))
        if act == use_act:
            self._on_use_template()
        elif act == dup_act:
            self._on_duplicate()
        elif act == del_act:
            self._on_delete()
