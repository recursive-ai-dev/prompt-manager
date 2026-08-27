"""Live compiled preview pane with token metrics and dispatch actions."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from prompt_manager.core.token_counter import calculate_metrics


class PreviewPanel(QFrame):
    """Right-hand side preview pane displaying the compiled/hydrated prompt with export actions."""

    copy_prompt_requested = pyqtSignal()
    copy_json_requested = pyqtSignal()
    export_requested = pyqtSignal(str)  # 'markdown', 'openai', 'anthropic', 'text'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header Bar with Actions
        header_layout = QHBoxLayout()
        preview_label = QLabel("LIVE OUTPUT PREVIEW")
        preview_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        preview_label.setToolTip("Live preview of the fully compiled and hydrated prompt")
        header_layout.addWidget(preview_label)
        header_layout.addStretch()

        self.copy_btn = QPushButton("📋 Copy Prompt")
        self.copy_btn.setObjectName("primaryButton")
        self.copy_btn.setToolTip("Copy hydrated prompt text to clipboard (Ctrl+Shift+C)")
        self.copy_btn.clicked.connect(self.copy_prompt_requested.emit)
        header_layout.addWidget(self.copy_btn)

        self.copy_json_btn = QPushButton("JSON API")
        self.copy_json_btn.setToolTip("Copy prompt formatted as an OpenAI / Anthropic chat completion JSON payload")
        self.copy_json_btn.clicked.connect(self.copy_json_requested.emit)
        header_layout.addWidget(self.copy_json_btn)

        self.export_menu_btn = QPushButton("Export ▾")
        self.export_menu_btn.setToolTip("Export this prompt as Markdown, OpenAI JSON, Anthropic JSON, or Plain Text")
        self.export_menu = QMenu(self)
        self.export_menu.addAction("Markdown (.md)", lambda: self.export_requested.emit("markdown"))
        self.export_menu.addAction("OpenAI Payload (.json)", lambda: self.export_requested.emit("openai"))
        self.export_menu.addAction("Anthropic Payload (.json)", lambda: self.export_requested.emit("anthropic"))
        self.export_menu.addAction("Plain Text (.txt)", lambda: self.export_requested.emit("text"))
        self.export_menu_btn.setMenu(self.export_menu)
        header_layout.addWidget(self.export_menu_btn)

        layout.addLayout(header_layout)

        # Preview Text Viewer
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setToolTip("Compiled output viewer (read-only live preview)")
        mono_font = QFont("monospace", 10)
        self.preview_edit.setFont(mono_font)
        self.preview_edit.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0f1115;
                border: 1px solid #232833;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 10px;
            }
            """
        )
        layout.addWidget(self.preview_edit, stretch=1)

        # Footer Metrics Bar
        self.metrics_label = QLabel("Tokens: ~0  |  Words: 0  |  Chars: 0")
        self.metrics_label.setStyleSheet(
            "font-size: 11px; color: #64748b; padding-top: 4px;"
        )
        self.metrics_label.setToolTip("Real-time metrics: Estimated BPE tokens, word count, and character count")
        layout.addWidget(self.metrics_label)

    def set_content(self, text: str):
        self.preview_edit.setPlainText(text)
        metrics = calculate_metrics(text)
        self.metrics_label.setText(
            f"Tokens: ~{metrics.estimated_tokens:,}  |  Words: {metrics.words:,}  |  Chars: {metrics.characters:,}"
        )

    def get_content(self) -> str:
        return self.preview_edit.toPlainText()
