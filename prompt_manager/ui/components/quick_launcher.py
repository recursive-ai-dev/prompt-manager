"""Global Quick-Access Launcher HUD / Floating Command Palette."""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.models import Prompt
from prompt_manager.core.template_engine import extract_variables, hydrate_template
from prompt_manager.storage.repository import PromptRepository


class QuickLauncherHUD(QDialog):
    """Floating Spotlight/Raycast-style HUD for instant prompt searching, hydration, and clipboard dispatch."""

    open_in_editor_requested = pyqtSignal(str)  # prompt_id
    prompt_dispatched = pyqtSignal(str)  # hydrated text

    def __init__(self, repo: PromptRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self._all_prompts: List[Prompt] = []
        self._filtered_prompts: List[Prompt] = []
        self._active_prompt: Optional[Prompt] = None
        self._variable_values: Dict[str, str] = {}
        self._var_inputs: Dict[str, QLineEdit] = {}

        self.setWindowTitle("Prompt Manager Quick Launcher")
        self.resize(750, 520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(
            """
            QDialog {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLineEdit#hudSearch {
                background: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit#hudSearch:focus {
                border: 1px solid #38bdf8;
            }
            QListWidget#hudList {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 4px;
            }
            QListWidget#hudList::item {
                padding: 8px 10px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget#hudList::item:selected {
                background: #0284c7;
                color: #ffffff;
            }
            """
        )

        self._init_ui()
        self.refresh_prompts()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # ── Search Input ─────────────────────────────────────────────
        self.search_input = QLineEdit()
        self.search_input.setObjectName("hudSearch")
        self.search_input.setPlaceholderText("🔍 Search prompts (Title, tags, body, model)... [↑/↓ Navigate, Enter to Copy]")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)

        # ── Splitter: Prompt Results List + Live Variable/Preview Form ─
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Prompt List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("hudList")
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemDoubleClicked.connect(lambda: self.dispatch_active_prompt())
        self.splitter.addWidget(self.list_widget)

        # Right: Detail / Variable form / Preview container
        self.right_container = QWidget()
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(8)

        # Prompt Title & Target Model
        self.title_label = QLabel("Select a prompt")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8;")
        right_layout.addWidget(self.title_label)

        # Variables Scroll Area
        self.var_container = QWidget()
        self.var_layout = QVBoxLayout(self.var_container)
        self.var_layout.setContentsMargins(0, 0, 0, 0)
        self.var_layout.setSpacing(6)
        right_layout.addWidget(self.var_container)

        # Preview output
        preview_header = QLabel("Preview")
        preview_header.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        right_layout.addWidget(preview_header)

        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFont(QFont("monospace", 9))
        self.preview_edit.setStyleSheet("background: #090d16; border: 1px solid #1e293b; color: #94a3b8; border-radius: 4px;")
        right_layout.addWidget(self.preview_edit, stretch=1)

        self.splitter.addWidget(self.right_container)
        self.splitter.setSizes([320, 400])
        layout.addWidget(self.splitter, stretch=1)

        # ── Bottom Action & Shortcut Bar ─────────────────────────────
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 11px; color: #64748b;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.edit_btn = QPushButton("✏ Edit (Ctrl+O)")
        self.edit_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        footer_layout.addWidget(self.edit_btn)

        self.copy_btn = QPushButton("📋 Copy to Clipboard (Enter)")
        self.copy_btn.setObjectName("primaryButton")
        self.copy_btn.setStyleSheet("font-size: 11px; font-weight: 700; padding: 4px 12px;")
        self.copy_btn.clicked.connect(self.dispatch_active_prompt)
        footer_layout.addWidget(self.copy_btn)

        layout.addLayout(footer_layout)

    def refresh_prompts(self):
        """Fetch all prompts from DB and populate initial list."""
        try:
            self._all_prompts = self.repo.list_prompts()
            self._filter_and_render()
        except Exception:
            self._all_prompts = []

    def _filter_and_render(self):
        query = self.search_input.text().strip().lower()
        self.list_widget.clear()

        if not query:
            self._filtered_prompts = list(self._all_prompts)
        else:
            self._filtered_prompts = [
                p for p in self._all_prompts
                if query in p.title.lower()
                or query in p.description.lower()
                or query in p.template_content.lower()
                or any(query in t.lower() for t in p.tags)
            ]

        for p in self._filtered_prompts:
            item = QListWidgetItem()
            fav_icon = "★ " if p.is_favorite else ""
            item.setText(f"{fav_icon}{p.title}\n[{p.target_model}]")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.list_widget.addItem(item)

        if self._filtered_prompts:
            self.list_widget.setCurrentRow(0)
        else:
            self._active_prompt = None
            self.title_label.setText("No matching prompts found")
            self.preview_edit.clear()

    def _on_search_text_changed(self):
        self._filter_and_render()

    def _on_row_changed(self, row: int):
        if row < 0 or row >= len(self._filtered_prompts):
            self._active_prompt = None
            return

        self._active_prompt = self._filtered_prompts[row]
        self._render_prompt_detail(self._active_prompt)

    def _render_prompt_detail(self, prompt: Prompt):
        self.title_label.setText(f"{prompt.title} ({prompt.target_model})")
        self._variable_values.clear()
        self._var_inputs.clear()

        # Clear existing dynamic variable inputs
        while self.var_layout.count():
            child = self.var_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Extract variables
        vars_list = extract_variables(f"{prompt.template_content}\n{prompt.system_instruction}")
        if vars_list:
            var_box = QFrame()
            var_box.setStyleSheet("background: #1e293b; border-radius: 6px; padding: 6px;")
            vb_layout = QVBoxLayout(var_box)
            vb_layout.setContentsMargins(6, 6, 6, 6)
            vb_layout.setSpacing(4)

            for v in vars_list:
                row = QHBoxLayout()
                lbl = QLabel(f"{v.name}:")
                lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; min-width: 70px;")
                row.addWidget(lbl)

                inp = QLineEdit()
                inp.setText(v.default_value)
                inp.setStyleSheet("background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 3px 6px; font-size: 11px;")
                inp.textChanged.connect(lambda text, name=v.name: self._on_var_changed(name, text))
                self._variable_values[v.name] = v.default_value
                self._var_inputs[v.name] = inp
                row.addWidget(inp, stretch=1)
                vb_layout.addLayout(row)

            self.var_layout.addWidget(var_box)
            self.var_container.show()
        else:
            self.var_container.hide()

        self._update_preview()

    def _on_var_changed(self, var_name: str, value: str):
        self._variable_values[var_name] = value
        self._update_preview()

    def _get_hydrated_full_text(self) -> str:
        if not self._active_prompt:
            return ""
        hydrated_user = hydrate_template(self._active_prompt.template_content, self._variable_values).strip()
        hydrated_system = hydrate_template(self._active_prompt.system_instruction, self._variable_values).strip()
        if hydrated_system:
            return f"[SYSTEM INSTRUCTION]\n{hydrated_system}\n\n[USER PROMPT]\n{hydrated_user}"
        return hydrated_user

    def _update_preview(self):
        if not self._active_prompt:
            self.preview_edit.clear()
            return
        self.preview_edit.setPlainText(self._get_hydrated_full_text())

    def dispatch_active_prompt(self):
        """Copy hydrated prompt to system clipboard, increment use count, and close/hide."""
        if not self._active_prompt:
            return

        full_text = self._get_hydrated_full_text()
        QGuiApplication.clipboard().setText(full_text)

        try:
            self.repo.increment_use_count(self._active_prompt.id)
        except Exception:
            pass

        self.prompt_dispatched.emit(full_text)
        self.status_label.setText("Copied to clipboard! ✓")
        self.accept()

    def _on_edit_clicked(self):
        if self._active_prompt:
            self.open_in_editor_requested.emit(self._active_prompt.id)
            self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            # If search input is focused and enter pressed, copy
            self.dispatch_active_prompt()
        elif key == Qt.Key.Key_Down:
            if self.search_input.hasFocus():
                self.list_widget.setFocus()
                if self.list_widget.count() > 0 and self.list_widget.currentRow() == -1:
                    self.list_widget.setCurrentRow(0)
            else:
                super().keyPressEvent(event)
        elif key == Qt.Key.Key_Up:
            if self.list_widget.hasFocus() and self.list_widget.currentRow() <= 0:
                self.search_input.setFocus()
            else:
                super().keyPressEvent(event)
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_O:
            self._on_edit_clicked()
        else:
            super().keyPressEvent(event)
