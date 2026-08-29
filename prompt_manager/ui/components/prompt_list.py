"""Prompt list panel with instant search, cards, and action triggers."""

from typing import List, Optional
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.models import Prompt


class PromptCardWidget(QWidget):
    """Custom widget rendered inside each prompt list item."""

    favorite_clicked = pyqtSignal(str)

    def __init__(self, prompt: Prompt, parent=None):
        super().__init__(parent)
        self.prompt = prompt

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Top row: Title + Star
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        title_label = QLabel(prompt.title or "Untitled Prompt")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        # Color inherited from theme via QWidget palette (avoids hard-coded dark/light mismatch)
        title_label.setStyleSheet("font-weight: 700;")
        top_row.addWidget(title_label, stretch=1)

        star_text = "★" if prompt.is_favorite else "☆"
        star_color = "#f59e0b" if prompt.is_favorite else "#64748b"
        self.star_btn = QPushButton(star_text)
        self.star_btn.setFixedSize(22, 22)
        self.star_btn.setStyleSheet(
            f"border: none; background: transparent; color: {star_color}; font-size: 14px; padding: 0;"
        )
        self.star_btn.setToolTip("Click to toggle favorite (Pin to top)")
        self.star_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.prompt.id))
        top_row.addWidget(self.star_btn)

        layout.addLayout(top_row)

        # Middle row: Description or content preview
        desc_text = prompt.description or (prompt.template_content.splitlines()[0] if prompt.template_content else "")
        if desc_text:
            snippet_label = QLabel(desc_text[:65] + ("..." if len(desc_text) > 65 else ""))
            snippet_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
            layout.addWidget(snippet_label)

        # Bottom row: Model badge & tags
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        badge = QLabel(prompt.target_model or "General")
        badge.setStyleSheet(
            """
            background-color: #1e293b;
            color: #38bdf8;
            border: 1px solid #0284c7;
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 10px;
            font-weight: 600;
            """
        )
        badge.setToolTip(f"Target AI model: {prompt.target_model}")
        bottom_row.addWidget(badge)

        if prompt.tags:
            first_tags = " ".join([f"#{t}" for t in prompt.tags[:2]])
            tags_label = QLabel(first_tags)
            tags_label.setStyleSheet("color: #64748b; font-size: 10px;")
            tags_label.setToolTip(f"Tags: {', '.join(prompt.tags)}")
            bottom_row.addWidget(tags_label)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        tags_info = f"\nTags: {', '.join(prompt.tags)}" if prompt.tags else ""
        desc_info = f"\n{prompt.description}" if prompt.description else ""
        self.setToolTip(
            f"<b>{prompt.title}</b>{desc_info}\nModel: {prompt.target_model}{tags_info}\nUpdated: {prompt.updated_at[:16]}"
        )


class PromptListPanel(QFrame):
    """Middle panel displaying the searchable list of prompts."""

    prompt_selected = pyqtSignal(str)
    new_prompt_requested = pyqtSignal()
    delete_prompt_requested = pyqtSignal(str)
    duplicate_prompt_requested = pyqtSignal(str)
    favorite_toggled = pyqtSignal(str)
    search_query_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("listFrame")
        self.setMinimumWidth(260)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(8)

        # New Prompt Primary Button
        self.new_btn = QPushButton("+ New Prompt")
        self.new_btn.setObjectName("primaryButton")
        self.new_btn.setFixedHeight(34)
        self.new_btn.setToolTip("Create a new prompt template in active category (Ctrl+N)")
        self.new_btn.clicked.connect(self.new_prompt_requested.emit)
        layout.addWidget(self.new_btn)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search prompts... (Ctrl+K)")
        self.search_input.setToolTip("Full-text search across titles, templates, descriptions, and system instructions (Ctrl+K or Ctrl+F)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(32)
        layout.addWidget(self.search_input)

        # Debounce timer for search
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self._emit_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start())

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(4)
        self.list_widget.setToolTip("Prompt list. Click to edit, right-click for quick actions.")
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

    def set_prompts(self, prompts: List[Prompt], select_id: Optional[str] = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        target_item = None
        for p in prompts:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            card = PromptCardWidget(p)
            card.favorite_clicked.connect(self.favorite_toggled.emit)

            item.setSizeHint(card.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

            if select_id and p.id == select_id:
                target_item = item

        self.list_widget.blockSignals(False)

        if target_item:
            self.list_widget.setCurrentItem(target_item)
        elif self.list_widget.count() > 0 and select_id is None:
            self.list_widget.setCurrentRow(0)

    def update_prompt_item(self, prompt: Prompt):
        """Update existing card widget in place without rebuilding list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == prompt.id:
                card = PromptCardWidget(prompt)
                card.favorite_clicked.connect(self.favorite_toggled.emit)
                item.setSizeHint(card.sizeHint())
                self.list_widget.setItemWidget(item, card)
                break

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _emit_search(self):
        self.search_query_changed.emit(self.search_input.text().strip())

    def _on_selection_changed(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            prompt_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.prompt_selected.emit(prompt_id)

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        prompt_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        dup_action = menu.addAction("📋 Duplicate Prompt (Ctrl+D)")
        fav_action = menu.addAction("⭐ Toggle Favorite")
        menu.addSeparator()
        del_action = menu.addAction("🗑️ Delete Prompt (Del)")

        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == dup_action:
            self.duplicate_prompt_requested.emit(prompt_id)
        elif action == fav_action:
            self.favorite_toggled.emit(prompt_id)
        elif action == del_action:
            self.delete_prompt_requested.emit(prompt_id)
