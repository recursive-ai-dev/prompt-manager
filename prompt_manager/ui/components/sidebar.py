"""Sidebar navigation panel for collections, folders, and tags."""

from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.models import Folder, Tag


class SidebarPanel(QFrame):
    """Left sidebar with folder hierarchy, favorites, and tags."""

    filter_changed = pyqtSignal(str, object)
    create_folder_requested = pyqtSignal(str)
    rename_folder_requested = pyqtSignal(str, str)  # folder_id, new_name
    delete_folder_requested = pyqtSignal(str)
    delete_tag_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)

        self._folders: List[Folder] = []
        self._tags: List[Tag] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        # App Brand Header
        header_layout = QHBoxLayout()
        header_title = QLabel("Prompt Manager")
        header_title.setStyleSheet("font-weight: 700; font-size: 15px; color: #f8fafc;")
        header_title.setToolTip("Prompt Manager — Organize and template your prompt library")
        header_layout.addWidget(header_title)
        layout.addLayout(header_layout)

        # Main Navigation List (All Prompts, Favorites)
        self.nav_list = QListWidget()
        self.nav_list.setMaximumHeight(85)
        self.nav_list.setToolTip("Quick filters for library prompts")

        self.item_all = QListWidgetItem("📋  All Prompts")
        self.item_all.setData(Qt.ItemDataRole.UserRole, ("all", None))
        self.item_all.setToolTip("Show all prompts in your library (Click to reset active filter)")
        self.nav_list.addItem(self.item_all)

        self.item_fav = QListWidgetItem("⭐  Favorites")
        self.item_fav.setData(Qt.ItemDataRole.UserRole, ("favorite", None))
        self.item_fav.setToolTip("Filter by starred favorite prompts")
        self.nav_list.addItem(self.item_fav)

        self.nav_list.setCurrentItem(self.item_all)
        self.nav_list.itemClicked.connect(self._on_nav_clicked)
        layout.addWidget(self.nav_list)

        # Folders Section Header
        folder_header = QHBoxLayout()
        folder_label = QLabel("FOLDERS")
        folder_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        folder_label.setToolTip("Hierarchical folder categories")
        folder_header.addWidget(folder_label)

        add_folder_btn = QPushButton("+")
        add_folder_btn.setFixedSize(22, 22)
        add_folder_btn.setToolTip("Create a new folder to categorize prompts")
        add_folder_btn.clicked.connect(self._prompt_new_folder)
        folder_header.addWidget(add_folder_btn)
        layout.addLayout(folder_header)

        # Folders List
        self.folder_list = QListWidget()
        self.folder_list.setToolTip("Click a folder to filter. Right-click to rename or delete.")
        self.folder_list.itemClicked.connect(self._on_folder_clicked)
        self.folder_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_list.customContextMenuRequested.connect(self._show_folder_context_menu)
        layout.addWidget(self.folder_list, stretch=1)

        # Tags Section Header
        tag_header = QHBoxLayout()
        tag_label = QLabel("TAGS")
        tag_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        tag_label.setToolTip("Multi-tag classification tags")
        tag_header.addWidget(tag_label)
        layout.addLayout(tag_header)

        # Tags List
        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(140)
        self.tag_list.setToolTip("Click a tag to filter prompts. Right-click to manage.")
        self.tag_list.itemClicked.connect(self._on_tag_clicked)
        self.tag_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self._show_tag_context_menu)
        layout.addWidget(self.tag_list)

    def set_data(self, folders: List[Folder], tags: List[Tag]):
        self._folders = folders
        self._tags = tags

        # Populate Folders
        self.folder_list.clear()
        for f in folders:
            item = QListWidgetItem(f"📁  {f.name}")
            item.setData(Qt.ItemDataRole.UserRole, f.id)
            item.setToolTip(f"Folder: {f.name}\nClick to filter, right-click to rename or delete.")
            self.folder_list.addItem(item)

        # Populate Tags
        self.tag_list.clear()
        for t in tags:
            item = QListWidgetItem(f"🏷️  #{t.name}")
            item.setData(Qt.ItemDataRole.UserRole, t.id)
            item.setToolTip(f"Tag: #{t.name}\nClick to filter, right-click to delete.")
            self.tag_list.addItem(item)

    def _on_nav_clicked(self, item: QListWidgetItem):
        self.folder_list.clearSelection()
        self.tag_list.clearSelection()
        filter_type, target_id = item.data(Qt.ItemDataRole.UserRole)
        self.filter_changed.emit(filter_type, target_id)

    def _on_folder_clicked(self, item: QListWidgetItem):
        self.nav_list.clearSelection()
        self.tag_list.clearSelection()
        folder_id = item.data(Qt.ItemDataRole.UserRole)
        self.filter_changed.emit("folder", folder_id)

    def _on_tag_clicked(self, item: QListWidgetItem):
        self.nav_list.clearSelection()
        self.folder_list.clearSelection()
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        self.filter_changed.emit("tag", tag_id)

    def _prompt_new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter new folder name:")
        if ok and name.strip():
            self.create_folder_requested.emit(name.strip())

    def _show_folder_context_menu(self, pos):
        item = self.folder_list.itemAt(pos)
        if not item:
            return
        folder_id = item.data(Qt.ItemDataRole.UserRole)
        folder = next((f for f in self._folders if f.id == folder_id), None)
        folder_name = folder.name if folder else "Folder"

        menu = QMenu(self)
        rename_act = menu.addAction("✏️ Rename Folder...")
        del_action = menu.addAction("🗑️ Delete Folder")
        action = menu.exec(self.folder_list.mapToGlobal(pos))

        if action == rename_act:
            new_name, ok = QInputDialog.getText(
                self, "Rename Folder", f"Rename '{folder_name}' to:", text=folder_name
            )
            if ok and new_name.strip() and new_name.strip() != folder_name:
                self.rename_folder_requested.emit(folder_id, new_name.strip())
        elif action == del_action:
            reply = QMessageBox.question(
                self,
                "Delete Folder",
                f"Are you sure you want to delete the folder '{folder_name}'?\n(Prompts inside will be moved to Root, not deleted)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_folder_requested.emit(folder_id)

    def _show_tag_context_menu(self, pos):
        item = self.tag_list.itemAt(pos)
        if not item:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag = next((t for t in self._tags if t.id == tag_id), None)
        tag_name = tag.name if tag else "tag"

        menu = QMenu(self)
        del_action = menu.addAction("🗑️ Delete Tag")
        action = menu.exec(self.tag_list.mapToGlobal(pos))
        if action == del_action:
            reply = QMessageBox.question(
                self,
                "Delete Tag",
                f"Delete tag '#{tag_name}' from library?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.delete_tag_requested.emit(tag_id)
