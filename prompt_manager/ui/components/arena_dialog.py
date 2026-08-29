"""Multi-Model Evaluation Arena Dialog for side-by-side LLM benchmarking."""

from __future__ import annotations

import time
from typing import List, Optional

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.arena import ArenaResult, run_arena_comparison
from prompt_manager.core.licensing import FEATURE_ARENA, get_license_manager
from prompt_manager.integrations.llm_providers import (
    MODEL_CATALOG,
    LLMClient,
    LLMResponse,
    get_model_info,
)


class _ArenaWorker(QObject):
    """Background worker for concurrent multi-model arena execution."""

    finished = pyqtSignal(object)  # ArenaResult
    error = pyqtSignal(str)

    def __init__(
        self,
        prompt: str,
        system_instruction: str,
        model_ids: List[str],
        temperature: float,
    ):
        super().__init__()
        self.prompt = prompt
        self.system_instruction = system_instruction
        self.model_ids = model_ids
        self.temperature = temperature
        self._is_cancelled = False

    def run(self):
        try:
            result = run_arena_comparison(
                prompt=self.prompt,
                model_ids=self.model_ids,
                system_instruction=self.system_instruction,
                temperature=self.temperature,
            )
            if not self._is_cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class ModelCard(QFrame):
    """Individual model output panel with metrics badges and copy button."""

    def __init__(self, slot_number: int, default_model_id: str, parent=None):
        super().__init__(parent)
        self.setObjectName("modelCard")
        self.slot_number = slot_number
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            #modelCard {
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header: Model selector & Enable checkbox
        header = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("Select LLM for this comparison slot")
        for m in MODEL_CATALOG:
            self.model_combo.addItem(f"[{m.provider.upper()}] {m.display_name.split(':', 1)[-1].strip()}", m.id)

        idx = self.model_combo.findData(default_model_id)
        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setCurrentIndex(min(slot_number - 1, len(MODEL_CATALOG) - 1))
        header.addWidget(self.model_combo, stretch=1)

        self.status_badge = QLabel("Ready")
        self.status_badge.setStyleSheet("font-size: 10px; font-weight: 600; color: #94a3b8;")
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        # Telemetry metrics row
        self.metrics_label = QLabel("Latency: -- | Tokens: -- | Cost: --")
        self.metrics_label.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self.metrics_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumHeight(3)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Output text edit
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setFont(QFont("monospace", 10))
        self.output_edit.setPlaceholderText(f"Model {slot_number} output will appear here...")
        layout.addWidget(self.output_edit, stretch=1)

        # Card Footer: Copy button
        footer = QHBoxLayout()
        footer.addStretch()
        self.copy_btn = QPushButton("📋 Copy Output")
        self.copy_btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.copy_btn.clicked.connect(self._copy_output)
        footer.addWidget(self.copy_btn)
        layout.addLayout(footer)

    def get_selected_model_id(self) -> str:
        return self.model_combo.currentData()

    def set_running(self):
        self.status_badge.setText("⏳ Generating...")
        self.status_badge.setStyleSheet("font-size: 10px; font-weight: 600; color: #38bdf8;")
        self.metrics_label.setText("Querying model API...")
        self.progress.show()
        self.output_edit.clear()

    def set_result(self, response: LLMResponse, is_fastest: bool = False, is_cheapest: bool = False):
        self.progress.hide()
        if response.is_success:
            self.output_edit.setPlainText(response.content)
            cost_str = "Free" if response.estimated_cost_usd == 0 else f"${response.estimated_cost_usd:.5f}"
            tags = []
            if is_fastest:
                tags.append("⚡ FASTEST")
            if is_cheapest and response.estimated_cost_usd > 0:
                tags.append("💰 CHEAPEST")
            tag_str = f" [{' | '.join(tags)}]" if tags else ""

            self.status_badge.setText(f"✓ Done{tag_str}")
            self.status_badge.setStyleSheet("font-size: 10px; font-weight: 700; color: #10b981;")
            self.metrics_label.setText(
                f"⏱ {response.elapsed_seconds:.2f}s  |  📊 {response.total_tokens:,} toks  |  💲 {cost_str}"
            )
        else:
            self.status_badge.setText("⚠ Error")
            self.status_badge.setStyleSheet("font-size: 10px; font-weight: 700; color: #ef4444;")
            self.output_edit.setPlainText(f"Error executing model request:\n{response.error}")
            self.metrics_label.setText("Request failed")

    def _copy_output(self):
        text = self.output_edit.toPlainText().strip()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.status_badge.setText("Copied! ✓")


class ArenaDialog(QDialog):
    """Main Multi-Model Arena benchmarking dialog."""

    def __init__(self, prompt: str = "", system_instruction: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Multi-Model Evaluation Arena")
        self.resize(1100, 750)
        self._prompt = prompt
        self._system_instruction = system_instruction
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[_ArenaWorker] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Top Control & Configuration Bar ──────────────────────────
        top_bar = QHBoxLayout()
        title_label = QLabel("⚡ MULTI-MODEL ARENA BENCHMARK")
        title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8; letter-spacing: 0.5px;")
        top_bar.addWidget(title_label)
        top_bar.addStretch()

        # Temperature slider
        temp_layout = QHBoxLayout()
        temp_label = QLabel("Temp:")
        temp_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        temp_layout.addWidget(temp_label)

        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 150)  # 0.00 to 1.50
        self.temp_slider.setValue(70)
        self.temp_slider.setFixedWidth(100)
        self.temp_val_label = QLabel("0.70")
        self.temp_val_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #cbd5e1; min-width: 28px;")
        self.temp_slider.valueChanged.connect(lambda v: self.temp_val_label.setText(f"{v/100:.2f}"))
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_val_label)
        top_bar.addLayout(temp_layout)

        self.run_btn = QPushButton("⚡ Run Arena (Ctrl+Enter)")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.setStyleSheet("font-weight: 700; padding: 6px 14px;")
        self.run_btn.clicked.connect(self.run_arena)
        top_bar.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("dangerButton")
        self.stop_btn.setStyleSheet("padding: 6px 14px;")
        self.stop_btn.clicked.connect(self.cancel_arena)
        self.stop_btn.hide()
        top_bar.addWidget(self.stop_btn)

        main_layout.addLayout(top_bar)

        # ── Prompt Preview / Edit Drawer ─────────────────────────────
        prompt_box = QGroupBox("Prompt Under Test")
        prompt_layout = QVBoxLayout(prompt_box)
        prompt_layout.setContentsMargins(8, 8, 8, 8)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlainText(self._prompt)
        self.prompt_edit.setMaximumHeight(80)
        prompt_layout.addWidget(self.prompt_edit)
        main_layout.addWidget(prompt_box)

        # ── 3-Column Side-by-Side Model Cards ────────────────────────
        self.cards_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.card1 = ModelCard(1, "pollinations:openai-fast", self)
        self.card2 = ModelCard(2, "openai:gpt-4o", self)
        self.card3 = ModelCard(3, "anthropic:claude-3-7-sonnet-20250219", self)

        self.cards_splitter.addWidget(self.card1)
        self.cards_splitter.addWidget(self.card2)
        self.cards_splitter.addWidget(self.card3)
        self.cards_splitter.setSizes([350, 350, 350])

        main_layout.addWidget(self.cards_splitter, stretch=1)

        # ── Bottom Summary Banner ────────────────────────────────────
        self.summary_label = QLabel("Select models and click 'Run Arena' to benchmark responses side-by-side.")
        self.summary_label.setStyleSheet("font-size: 11px; color: #64748b; padding-top: 4px;")
        main_layout.addWidget(self.summary_label)

    def set_prompt_context(self, prompt: str, system_instruction: str = ""):
        self._prompt = prompt
        self._system_instruction = system_instruction
        self.prompt_edit.setPlainText(prompt)

    def run_arena(self):
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            return

        model_ids = [
            self.card1.get_selected_model_id(),
            self.card2.get_selected_model_id(),
            self.card3.get_selected_model_id(),
        ]
        temperature = self.temp_slider.value() / 100.0

        self.run_btn.hide()
        self.stop_btn.show()
        self.summary_label.setText("⚡ Dispatching concurrent requests to all provider endpoints...")

        self.card1.set_running()
        self.card2.set_running()
        self.card3.set_running()

        self._worker_thread = QThread(self)
        self._worker = _ArenaWorker(
            prompt=prompt_text,
            system_instruction=self._system_instruction,
            model_ids=model_ids,
            temperature=temperature,
        )
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_arena_finished)
        self._worker.error.connect(self._on_arena_error)
        self._worker_thread.start()

    def cancel_arena(self):
        if self._worker:
            self._worker._is_cancelled = True
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(300)
        self._worker = None
        self._worker_thread = None
        self.stop_btn.hide()
        self.run_btn.show()
        self.summary_label.setText("Benchmark cancelled.")

    def _on_arena_finished(self, result: ArenaResult):
        self.stop_btn.hide()
        self.run_btn.show()

        fastest = result.fastest_response
        cheapest = result.cheapest_response

        # Match results with cards
        cards = [self.card1, self.card2, self.card3]
        for i, card in enumerate(cards):
            if i < len(result.responses):
                resp = result.responses[i]
                is_fastest = fastest is not None and resp.model_id == fastest.model_id
                is_cheapest = cheapest is not None and resp.model_id == cheapest.model_id
                card.set_result(resp, is_fastest=is_fastest, is_cheapest=is_cheapest)

        summary_parts = []
        if fastest:
            summary_parts.append(f"⚡ Fastest: {get_model_info(fastest.model_id).display_name} ({fastest.elapsed_seconds:.2f}s)")
        if cheapest and cheapest.estimated_cost_usd > 0:
            summary_parts.append(f"💰 Most Efficient: {get_model_info(cheapest.model_id).display_name} (${cheapest.estimated_cost_usd:.5f})")

        if summary_parts:
            self.summary_label.setText("  •  ".join(summary_parts))
        else:
            self.summary_label.setText("Arena benchmark completed.")

        self._cleanup_thread()

    def _on_arena_error(self, err: str):
        self.stop_btn.hide()
        self.run_btn.show()
        self.summary_label.setText(f"⚠ Benchmark error: {err}")
        self._cleanup_thread()

    def _cleanup_thread(self):
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(200)
        self._worker = None
        self._worker_thread = None
