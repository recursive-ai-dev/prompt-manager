"""Modern Dark & Light Themes with KDE Plasma / Breeze Dark alignment."""

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #121417;
    color: #e2e8f0;
}

QWidget {
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", Ubuntu, Cantarell, sans-serif;
    font-size: 13px;
}

QSplitter::handle {
    background-color: #1f242d;
    width: 2px;
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

QFrame#sidebarFrame {
    background-color: #16191f;
    border-right: 1px solid #232833;
}

QFrame#listFrame {
    background-color: #1a1d24;
    border-right: 1px solid #232833;
}

QFrame#editorFrame, QFrame#previewFrame {
    background-color: #121417;
}

/* PushButtons */
QPushButton {
    background-color: #232833;
    border: 1px solid #333a47;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    color: #f1f5f9;
}

QPushButton:hover {
    background-color: #2e3544;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #1c2029;
}

QPushButton#primaryButton {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton#dangerButton {
    background-color: #7f1d1d;
    border: 1px solid #991b1b;
    color: #fecaca;
}

QPushButton#dangerButton:hover {
    background-color: #991b1b;
}

/* LineEdits and PlainTextEdits */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #1a1e26;
    border: 1px solid #2d3340;
    border-radius: 6px;
    padding: 6px 8px;
    color: #f8fafc;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #1e222c;
}

/* Title Input specific */
QLineEdit#titleInput {
    font-size: 16px;
    font-weight: 600;
    padding: 8px 10px;
    border: 1px solid transparent;
    background-color: transparent;
}

QLineEdit#titleInput:hover {
    border: 1px solid #2d3340;
    background-color: #1a1e26;
}

QLineEdit#titleInput:focus {
    border: 1px solid #3b82f6;
    background-color: #1a1e26;
}

/* ComboBox */
QComboBox {
    background-color: #1a1e26;
    border: 1px solid #2d3340;
    border-radius: 6px;
    padding: 5px 10px;
    color: #f8fafc;
}

QComboBox:hover {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #1e222c;
    border: 1px solid #333a47;
    selection-background-color: #2563eb;
    color: #f8fafc;
    border-radius: 4px;
    padding: 4px;
}

/* QListWidget and QTreeWidget */
QListWidget, QTreeWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item, QTreeWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #232833;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #333a47;
    min-height: 25px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #333a47;
    min-width: 25px;
    border-radius: 4px;
}

/* ToolBar & Menu */
QMenuBar {
    background-color: #16191f;
    border-bottom: 1px solid #232833;
    padding: 2px 6px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background: #232833;
}

QMenu {
    background-color: #1e222c;
    border: 1px solid #333a47;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QStatusBar {
    background-color: #16191f;
    border-top: 1px solid #232833;
    color: #94a3b8;
    font-size: 12px;
}

QTabWidget::pane {
    border: 1px solid #232833;
    background-color: #121417;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #1a1d24;
    border: 1px solid #232833;
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #94a3b8;
}

QTabBar::tab:selected {
    background-color: #121417;
    border-color: #3b82f6;
    color: #f1f5f9;
    font-weight: bold;
}
"""
