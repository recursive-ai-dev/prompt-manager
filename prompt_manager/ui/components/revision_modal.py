"""Modal dialog to inspect and restore prompt revision snapshots."""

from typing import List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from prompt_manager.core.models import PromptRevision


class RevisionHistoryDialog(QDialog):
    """Dialog for viewing past revisions and restoring snapshots."""

    revision_restored = pyqtSignal(PromptRevision)

    def __init__(self, revisions: List[PromptRevision], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Revision History")
        self.resize(750, 480)
        self.revisions = revisions

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel("Prompt Revision Snapshots")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        title.setToolTip("Chronological immutable snapshots of this prompt")
        main_layout.addWidget(title)

        content_layout = QHBoxLayout()

        # Left list of revisions
        self.rev_list = QListWidget()
        self.rev_list.setMaximumWidth(220)
        self.rev_list.setToolTip("Click a snapshot to inspect its past content")
        self.rev_list.itemClicked.connect(self._on_revision_selected)
        content_layout.addWidget(self.rev_list)

        # Right preview
        right_layout = QVBoxLayout()
        self.preview_box = QPlainTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setToolTip("Historical snapshot preview")
        right_layout.addWidget(self.preview_box)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.restore_btn = QPushButton("Restore This Version")
        self.restore_btn.setObjectName("primaryButton")
        self.restore_btn.setToolTip("Rollback active prompt to this selected revision snapshot")
        self.restore_btn.clicked.connect(self._restore_current)
        self.restore_btn.setEnabled(False)
        btn_row.addWidget(self.restore_btn)

        close_btn = QPushButton("Close")
        close_btn.setToolTip("Close dialog without rolling back")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        right_layout.addLayout(btn_row)
        content_layout.addLayout(right_layout, stretch=1)
        main_layout.addLayout(content_layout)

        self._populate()

    def _populate(self):
        self.rev_list.clear()
        if not self.revisions:
            item = QListWidgetItem("No saved revisions")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.rev_list.addItem(item)
            return

        for rev in self.revisions:
            label = f"Rev #{rev.revision_number} — {rev.created_at[:16]}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, rev)
            item.setToolTip(f"Revision #{rev.revision_number}\nRecorded at {rev.created_at}")
            self.rev_list.addItem(item)

        self.rev_list.setCurrentRow(0)
        self._on_revision_selected(self.rev_list.item(0))

    def _on_revision_selected(self, item: QListWidgetItem):
        rev = item.data(Qt.ItemDataRole.UserRole)
        if rev:
            self.preview_box.setPlainText(
                f"Title: {rev.title}\n"
                f"Date: {rev.created_at}\n\n"
                f"--- System Instruction ---\n{rev.system_instruction}\n\n"
                f"--- Template Content ---\n{rev.template_content}"
            )
            self.restore_btn.setEnabled(True)

    def _restore_current(self):
        item = self.rev_list.currentItem()
        if item:
            rev = item.data(Qt.ItemDataRole.UserRole)
            if rev:
                self.revision_restored.emit(rev)
                self.accept()
