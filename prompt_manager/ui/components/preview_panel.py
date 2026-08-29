"""Live compiled preview pane with token metrics, dispatch actions, and Pollinations AI execution."""

from __future__ import annotations

import time
from typing import Dict, Optional

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.config import (
    DEFAULT_POLLINATIONS_MODEL,
    POLLINATIONS_MODELS,
    get_pollinations_config,
    set_pollinations_config,
)
from prompt_manager.core.token_counter import calculate_metrics
from prompt_manager.integrations.pollinations_client import PollinationsClient, PollinationsError


class _PollinationsWorker(QObject):
    """Background worker for non-blocking Pollinations API requests."""

    finished = pyqtSignal(str, float)  # response_text, elapsed_seconds
    error = pyqtSignal(str)

    def __init__(
        self,
        prompt: str,
        system_instruction: str = "",
        model: str = DEFAULT_POLLINATIONS_MODEL,
        temperature: float = 0.7,
        api_key: str = "",
        timeout: int = 45,
    ):
        super().__init__()
        self.prompt = prompt
        self.system_instruction = system_instruction
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.timeout = timeout
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        start_time = time.time()
        client = PollinationsClient(api_key=self.api_key, timeout=self.timeout)
        try:
            result = client.generate(
                prompt=self.prompt,
                system_instruction=self.system_instruction,
                model=self.model,
                temperature=self.temperature,
            )
            elapsed = time.time() - start_time
            if not self._is_cancelled:
                self.finished.emit(result, elapsed)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class PreviewPanel(QFrame):
    """Preview pane displaying compiled prompt with export actions and live Pollinations AI testing."""

    copy_prompt_requested = pyqtSignal()
    copy_json_requested = pyqtSignal()
    export_requested = pyqtSignal(str)  # 'markdown', 'openai', 'anthropic', 'text', 'langchain', 'llamaindex'
    test_ai_requested = pyqtSignal()
    arena_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewFrame")
        self._system_instruction = ""
        self._temperature = 0.7
        self._poll_thread: Optional[QThread] = None
        self._poll_worker: Optional[_PollinationsWorker] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ── Header Bar with Actions ──────────────────────────────────
        header_layout = QHBoxLayout()
        preview_label = QLabel("LIVE OUTPUT PREVIEW")
        preview_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        preview_label.setToolTip("Live preview of the fully compiled and hydrated prompt")
        header_layout.addWidget(preview_label)
        header_layout.addStretch()

        # Pollinations Model Selector & Test Button
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Select Pollinations free model (no API key needed)")
        for m in POLLINATIONS_MODELS:
            self.model_combo.addItem(m, m)
        pol_cfg = get_pollinations_config()
        saved_model = pol_cfg.get("model", DEFAULT_POLLINATIONS_MODEL)
        idx = self.model_combo.findData(saved_model)
        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        header_layout.addWidget(self.model_combo)

        self.run_ai_btn = QPushButton("⚡ Run Free AI")
        self.run_ai_btn.setObjectName("primaryButton")
        self.run_ai_btn.setToolTip("Run prompt directly against Pollinations.ai free text endpoint (Ctrl+R)")
        self.run_ai_btn.clicked.connect(self.run_pollinations)
        header_layout.addWidget(self.run_ai_btn)

        self.arena_btn = QPushButton("⚡ Arena")
        self.arena_btn.setToolTip("Open Multi-Model Evaluation Arena to benchmark side-by-side (Ctrl+Shift+A)")
        self.arena_btn.clicked.connect(self.arena_requested.emit)
        header_layout.addWidget(self.arena_btn)

        self.cancel_ai_btn = QPushButton("⏹ Stop")
        self.cancel_ai_btn.setObjectName("dangerButton")
        self.cancel_ai_btn.setToolTip("Cancel the in-flight AI request")
        self.cancel_ai_btn.clicked.connect(self.cancel_pollinations)
        self.cancel_ai_btn.hide()
        header_layout.addWidget(self.cancel_ai_btn)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setToolTip("Copy hydrated prompt text to clipboard (Ctrl+Shift+C)")
        self.copy_btn.clicked.connect(self.copy_prompt_requested.emit)
        header_layout.addWidget(self.copy_btn)

        self.export_menu_btn = QPushButton("Export ▾")
        self.export_menu_btn.setToolTip("Export this prompt as Markdown, OpenAI JSON, Anthropic JSON, LangChain, or Plain Text")
        self.export_menu = QMenu(self)
        self.export_menu.addAction("JSON API Payload", self.copy_json_requested.emit)
        self.export_menu.addSeparator()
        self.export_menu.addAction("Markdown (.md)", lambda: self.export_requested.emit("markdown"))
        self.export_menu.addAction("OpenAI Payload (.json)", lambda: self.export_requested.emit("openai"))
        self.export_menu.addAction("Anthropic Payload (.json)", lambda: self.export_requested.emit("anthropic"))
        self.export_menu.addAction("LangChain Code (.py)", lambda: self.export_requested.emit("langchain"))
        self.export_menu.addAction("LlamaIndex Code (.py)", lambda: self.export_requested.emit("llamaindex"))
        self.export_menu.addAction("Plain Text (.txt)", lambda: self.export_requested.emit("text"))
        self.export_menu_btn.setMenu(self.export_menu)
        header_layout.addWidget(self.export_menu_btn)

        layout.addLayout(header_layout)

        # ── Splitter: Hydrated Prompt Preview + AI Response Area ─────
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: Hydrated Prompt Viewer
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setObjectName("previewOutput")
        self.preview_edit.setToolTip("Compiled output viewer (read-only live preview)")
        mono_font = QFont("monospace", 10)
        self.preview_edit.setFont(mono_font)
        self.splitter.addWidget(self.preview_edit)

        # Bottom: AI Response Box (Collapsible / Dynamic)
        self.ai_response_container = QWidget()
        ai_layout = QVBoxLayout(self.ai_response_container)
        ai_layout.setContentsMargins(0, 4, 0, 0)
        ai_layout.setSpacing(4)

        ai_header = QHBoxLayout()
        self.ai_title_label = QLabel("🤖 AI RESPONSE (Pollinations.ai)")
        self.ai_title_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981; letter-spacing: 0.5px;")
        ai_header.addWidget(self.ai_title_label)

        self.ai_status_label = QLabel("")
        self.ai_status_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        ai_header.addWidget(self.ai_status_label)
        ai_header.addStretch()

        self.copy_ai_btn = QPushButton("📋 Copy Response")
        self.copy_ai_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.copy_ai_btn.clicked.connect(self._on_copy_ai_response)
        ai_header.addWidget(self.copy_ai_btn)

        self.hide_ai_btn = QPushButton("✕")
        self.hide_ai_btn.setFixedSize(20, 20)
        self.hide_ai_btn.setStyleSheet("font-size: 11px; border: none; background: transparent; color: #64748b;")
        self.hide_ai_btn.clicked.connect(self.hide_ai_response)
        ai_header.addWidget(self.hide_ai_btn)

        ai_layout.addLayout(ai_header)

        self.ai_progress = QProgressBar()
        self.ai_progress.setRange(0, 0)
        self.ai_progress.setMaximumHeight(4)
        self.ai_progress.hide()
        ai_layout.addWidget(self.ai_progress)

        self.ai_response_edit = QPlainTextEdit()
        self.ai_response_edit.setReadOnly(True)
        self.ai_response_edit.setFont(mono_font)
        self.ai_response_edit.setPlaceholderText("AI response will appear here...")
        ai_layout.addWidget(self.ai_response_edit)

        self.splitter.addWidget(self.ai_response_container)
        self.ai_response_container.hide()

        layout.addWidget(self.splitter, stretch=1)

        # ── Footer Metrics Bar ───────────────────────────────────────
        self.metrics_label = QLabel("Tokens: ~0  |  Words: 0  |  Chars: 0")
        self.metrics_label.setStyleSheet(
            "font-size: 11px; color: #64748b; padding-top: 4px;"
        )
        self.metrics_label.setToolTip("Real-time metrics: Estimated BPE tokens, word count, and character count")
        layout.addWidget(self.metrics_label)

    # ── Content & Configuration ─────────────────────────────────────

    def set_content(self, text: str):
        self.preview_edit.setPlainText(text)
        metrics = calculate_metrics(text)
        self.metrics_label.setText(
            f"Tokens: ~{metrics.estimated_tokens:,}  |  Words: {metrics.words:,}  |  Chars: {metrics.characters:,}"
        )

    def get_content(self) -> str:
        return self.preview_edit.toPlainText()

    def set_context_metadata(self, system_instruction: str = "", temperature: float = 0.7):
        self._system_instruction = system_instruction
        self._temperature = temperature

    def _on_model_changed(self):
        model = self.model_combo.currentData()
        if model:
            set_pollinations_config({"model": model})

    # ── Pollinations Execution ──────────────────────────────────────

    def run_pollinations(self):
        prompt_text = self.get_content().strip()
        if not prompt_text:
            return

        model = self.model_combo.currentData() or DEFAULT_POLLINATIONS_MODEL
        pol_cfg = get_pollinations_config()
        api_key = pol_cfg.get("api_key", "")
        timeout = int(pol_cfg.get("timeout", 45))

        # Show UI in generating state
        self.ai_response_container.show()
        self.ai_response_edit.clear()
        self.ai_title_label.setText(f"🤖 AI RESPONSE ({model})")
        self.ai_status_label.setText("Connecting to Pollinations.ai...")
        self.ai_progress.show()
        self.run_ai_btn.hide()
        self.cancel_ai_btn.show()

        # Allocate splitter sizes if newly opened
        self.splitter.setSizes([300, 300])

        # Clean previous worker if running
        self.cancel_pollinations(silent=True)

        self._poll_thread = QThread(self)
        self._poll_worker = _PollinationsWorker(
            prompt=prompt_text,
            system_instruction=self._system_instruction,
            model=model,
            temperature=self._temperature,
            api_key=api_key,
            timeout=timeout,
        )
        self._poll_worker.moveToThread(self._poll_thread)
        self._poll_thread.started.connect(self._poll_worker.run)
        self._poll_worker.finished.connect(self._on_ai_finished)
        self._poll_worker.error.connect(self._on_ai_error)
        self._poll_thread.start()

    def cancel_pollinations(self, silent: bool = False):
        if self._poll_worker:
            self._poll_worker.cancel()
        if self._poll_thread:
            self._poll_thread.quit()
            self._poll_thread.wait(500)
        self._poll_worker = None
        self._poll_thread = None
        if not silent:
            self.ai_progress.hide()
            self.ai_status_label.setText("Cancelled")
            self.cancel_ai_btn.hide()
            self.run_ai_btn.show()

    def _on_ai_finished(self, response: str, elapsed: float):
        self.ai_progress.hide()
        self.cancel_ai_btn.hide()
        self.run_ai_btn.show()
        self.ai_response_edit.setPlainText(response)
        metrics = calculate_metrics(response)
        self.ai_status_label.setText(
            f"✅ {elapsed:.2f}s  |  ~{metrics.estimated_tokens:,} tokens, {metrics.words:,} words"
        )
        self._clean_thread()

    def _on_ai_error(self, err_msg: str):
        self.ai_progress.hide()
        self.cancel_ai_btn.hide()
        self.run_ai_btn.show()
        self.ai_response_edit.setPlainText(f"Error: {err_msg}")
        self.ai_status_label.setText("⚠ Request failed")
        self._clean_thread()

    def _clean_thread(self):
        if self._poll_thread:
            self._poll_thread.quit()
            self._poll_thread.wait(200)
        self._poll_worker = None
        self._poll_thread = None

    def _on_copy_ai_response(self):
        text = self.ai_response_edit.toPlainText().strip()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.ai_status_label.setText("Copied response to clipboard ✓")

    def hide_ai_response(self):
        self.cancel_pollinations(silent=True)
        self.ai_response_container.hide()
