"""Central prompt editor with syntax highlighting, metadata inputs, and autosave signals."""

from typing import List, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.config import DEFAULT_TARGET_MODELS
from prompt_manager.core.models import Folder, Prompt
from prompt_manager.core.template_engine import check_syntax_errors
from prompt_manager.ui.components.highlighter import PromptSyntaxHighlighter


class PromptEditorPanel(QFrame):
    """Middle-right editor panel for editing prompt template, system prompt, and metadata."""

    content_changed = pyqtSignal()
    save_requested = pyqtSignal(bool)  # create_revision: bool
    delete_requested = pyqtSignal()
    history_requested = pyqtSignal()
    favorite_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editorFrame")
        self._current_prompt: Optional[Prompt] = None
        self._is_dirty = False
        self._suppress_signals = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top Action & Status Bar
        top_bar = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setObjectName("titleInput")
        self.title_input.setPlaceholderText("Prompt Title...")
        self.title_input.textChanged.connect(self._on_content_modified)
        top_bar.addWidget(self.title_input, stretch=1)

        self.save_status = QLabel("Saved")
        self.save_status.setStyleSheet("color: #64748b; font-size: 11px; margin-right: 8px;")
        top_bar.addWidget(self.save_status)

        self.save_btn = QPushButton("Save (Ctrl+S)")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(lambda: self.save_requested.emit(True))
        top_bar.addWidget(self.save_btn)

        self.history_btn = QPushButton("🕒 History")
        self.history_btn.setToolTip("View revision history snapshots")
        self.history_btn.clicked.connect(self.history_requested.emit)
        top_bar.addWidget(self.history_btn)

        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.setToolTip("Delete this prompt")
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        top_bar.addWidget(self.delete_btn)

        layout.addLayout(top_bar)

        # Metadata Row: Target Model, Folder, Tags
        meta_bar = QHBoxLayout()
        meta_bar.setSpacing(10)

        # Target Model
        model_box = QHBoxLayout()
        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        model_box.addWidget(model_lbl)
        self.model_combo = QComboBox()
        self.model_combo.addItems(DEFAULT_TARGET_MODELS)
        self.model_combo.setEditable(True)
        self.model_combo.currentTextChanged.connect(self._on_content_modified)
        model_box.addWidget(self.model_combo)
        meta_bar.addLayout(model_box)

        # Folder
        folder_box = QHBoxLayout()
        folder_lbl = QLabel("Folder:")
        folder_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        folder_box.addWidget(folder_lbl)
        self.folder_combo = QComboBox()
        self.folder_combo.currentIndexChanged.connect(self._on_content_modified)
        folder_box.addWidget(self.folder_combo)
        meta_bar.addLayout(folder_box)

        # Tags
        tag_box = QHBoxLayout()
        tag_lbl = QLabel("Tags:")
        tag_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        tag_box.addWidget(tag_lbl)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g. coding, refactor, python")
        self.tags_input.textChanged.connect(self._on_content_modified)
        tag_box.addWidget(self.tags_input)
        meta_bar.addLayout(tag_box, stretch=1)

        layout.addLayout(meta_bar)

        # System Instruction Collapsible Section
        sys_header = QHBoxLayout()
        self.sys_toggle_btn = QPushButton("▶ System Instruction (Optional)")
        self.sys_toggle_btn.setStyleSheet(
            "text-align: left; border: none; background: transparent; color: #94a3b8; font-weight: 600; padding: 2px 0;"
        )
        self.sys_toggle_btn.clicked.connect(self._toggle_system_instruction)
        sys_header.addWidget(self.sys_toggle_btn)
        sys_header.addStretch()
        layout.addLayout(sys_header)

        self.system_edit = QPlainTextEdit()
        self.system_edit.setPlaceholderText("Enter system instructions, persona constraints, or background context...")
        self.system_edit.setMaximumHeight(85)
        self.system_edit.textChanged.connect(self._on_content_modified)
        self.system_edit.hide()
        layout.addWidget(self.system_edit)

        # Prompt Template Label & Syntax Error Alert
        tpl_header = QHBoxLayout()
        tpl_label = QLabel("PROMPT TEMPLATE")
        tpl_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        tpl_header.addWidget(tpl_label)

        self.syntax_alert = QLabel("")
        self.syntax_alert.setStyleSheet("color: #f87171; font-size: 11px;")
        tpl_header.addWidget(self.syntax_alert)
        tpl_header.addStretch()
        layout.addLayout(tpl_header)

        # Prompt Template Editor
        self.template_edit = QPlainTextEdit()
        self.template_edit.setPlaceholderText(
            "Write your prompt template here...\nUse {{variable}} for inputs, or {{var:default|options:a,b}}."
        )
        mono_font = QFont("monospace", 10)
        self.template_edit.setFont(mono_font)
        self.template_edit.textChanged.connect(self._on_template_text_changed)

        # Attach Highlighter
        self.highlighter = PromptSyntaxHighlighter(self.template_edit.document())
        layout.addWidget(self.template_edit, stretch=1)

        # Autosave debouncer (400ms)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(400)
        self.autosave_timer.timeout.connect(lambda: self.save_requested.emit(False))

    def set_folders(self, folders: List[Folder]):
        self._suppress_signals = True
        self.folder_combo.clear()
        self.folder_combo.addItem("None (Root)", None)
        for f in folders:
            self.folder_combo.addItem(f"📁 {f.name}", f.id)
        self._suppress_signals = False

    def load_prompt(self, prompt: Prompt):
        self._suppress_signals = True
        self._current_prompt = prompt
        self._is_dirty = False

        self.title_input.setText(prompt.title)
        self.model_combo.setCurrentText(prompt.target_model or "General")

        # Set folder combo
        idx = self.folder_combo.findData(prompt.folder_id)
        self.folder_combo.setCurrentIndex(idx if idx != -1 else 0)

        self.tags_input.setText(", ".join(prompt.tags))

        # System instruction
        if prompt.system_instruction:
            self.system_edit.setPlainText(prompt.system_instruction)
            self.system_edit.show()
            self.sys_toggle_btn.setText("▼ System Instruction (Optional)")
        else:
            self.system_edit.setPlainText("")
            self.system_edit.hide()
            self.sys_toggle_btn.setText("▶ System Instruction (Optional)")

        self.template_edit.setPlainText(prompt.template_content)
        self.save_status.setText("Saved")
        self.save_status.setStyleSheet("color: #64748b; font-size: 11px;")
        self._check_syntax()

        self._suppress_signals = False
        self.content_changed.emit()

    def update_prompt_model(self, prompt: Prompt):
        """Update prompt fields from current form values."""
        prompt.title = self.title_input.text().strip() or "Untitled Prompt"
        prompt.target_model = self.model_combo.currentText()
        prompt.folder_id = self.folder_combo.currentData()

        # Parse tags
        raw_tags = self.tags_input.text().split(",")
        prompt.tags = [t.strip().lstrip("#") for t in raw_tags if t.strip()]

        prompt.system_instruction = self.system_edit.toPlainText().strip()
        prompt.template_content = self.template_edit.toPlainText()

    def get_template_content(self) -> str:
        return self.template_edit.toPlainText()

    def get_system_instruction(self) -> str:
        return self.system_edit.toPlainText()

    def mark_saved(self):
        self._is_dirty = False
        self.save_status.setText("Saved")
        self.save_status.setStyleSheet("color: #10b981; font-size: 11px;")

    def _toggle_system_instruction(self):
        if self.system_edit.isVisible():
            self.system_edit.hide()
            self.sys_toggle_btn.setText("▶ System Instruction (Optional)")
        else:
            self.system_edit.show()
            self.sys_toggle_btn.setText("▼ System Instruction (Optional)")
            self.system_edit.setFocus()

    def _on_content_modified(self):
        if self._suppress_signals:
            return
        self._is_dirty = True
        self.save_status.setText("Unsaved changes*")
        self.save_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
        self.content_changed.emit()
        self.autosave_timer.start()

    def _on_template_text_changed(self):
        self._check_syntax()
        self._on_content_modified()

    def _check_syntax(self):
        errors = check_syntax_errors(self.template_edit.toPlainText())
        if errors:
            self.syntax_alert.setText(f"⚠ {errors[0]}")
        else:
            self.syntax_alert.setText("")
