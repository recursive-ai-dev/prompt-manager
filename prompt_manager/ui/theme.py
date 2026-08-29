"""Theme registry — 12 handcrafted QSS themes for Prompt Manager.

Each theme is built from a palette dict via _build_stylesheet(), so
adding a new theme is just a new palette entry.

Usage:
    from prompt_manager.ui.theme import get_stylesheet, list_themes, THEMES, DEFAULT_THEME

    app.setStyleSheet(get_stylesheet("dracula"))
    for t in list_themes():
        print(t.id, t.name, t.variant)

Palette keys expected by _build_stylesheet are documented inside the function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    variant: str  # "dark" | "light"
    description: str
    stylesheet: str

    @property
    def is_dark(self) -> bool:
        return self.variant == "dark"

    @property
    def is_light(self) -> bool:
        return self.variant == "light"


def _build_stylesheet(p: Dict[str, str]) -> str:
    """Generate the full QSS string from a palette dict.

    Required palette keys:
        bg_main, bg_sidebar, bg_list, bg_input, bg_input_focus,
        bg_button, bg_button_hover, bg_button_pressed,
        bg_menubar, bg_menu, bg_tab, bg_tab_selected,
        bg_scroll_handle, bg_scroll_handle_hover,
        bg_selected, bg_splitter, bg_splitter_hover,
        border, border_input, border_button, border_menu,
        text_primary, text_secondary, text_tertiary, text_input, text_selected,
        accent, accent_hover, accent_border, accent_active,
        danger_bg, danger_border, danger_hover, danger_text,
        selection_bg, selection_text,
        bg_preview  (optional, falls back to bg_main darker variant)
    """
    # fallback for preview bg if not provided
    bg_preview = p.get("bg_preview", p["bg_input"])

    return f"""
QMainWindow, QDialog {{
    background-color: {p['bg_main']};
    color: {p['text_primary']};
}}

QWidget {{
    color: {p['text_primary']};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", Ubuntu, Cantarell, sans-serif;
    font-size: 13px;
}}

QToolTip {{
    background-color: {p['bg_menu']};
    color: {p['text_primary']};
    border: 1px solid {p['border_menu']};
    border-radius: 4px;
    padding: 4px 6px;
}}

QSplitter::handle {{
    background-color: {p['bg_splitter']};
    width: 2px;
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {p['bg_splitter_hover']};
}}

QFrame#sidebarFrame {{
    background-color: {p['bg_sidebar']};
    border-right: 1px solid {p['border']};
}}

QFrame#listFrame {{
    background-color: {p['bg_list']};
    border-right: 1px solid {p['border']};
}}

QFrame#editorFrame, QFrame#previewFrame {{
    background-color: {p['bg_main']};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {p['bg_button']};
    border: 1px solid {p['border_button']};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    color: {p['text_primary']};
}}

QPushButton:hover {{
    background-color: {p['bg_button_hover']};
    border-color: {p['accent_border']};
}}

QPushButton:pressed {{
    background-color: {p['bg_button_pressed']};
}}

QPushButton:disabled {{
    background-color: {p['bg_input']};
    color: {p['text_tertiary']};
    border-color: {p['border']};
}}

QPushButton#primaryButton {{
    background-color: {p['accent']};
    border: 1px solid {p['accent_border']};
    color: {p['selection_text']};
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {p['accent_hover']};
    border-color: {p['accent_active']};
}}

QPushButton#primaryButton:pressed {{
    background-color: {p['accent_hover']};
}}

QPushButton#dangerButton {{
    background-color: {p['danger_bg']};
    border: 1px solid {p['danger_border']};
    color: {p['danger_text']};
}}

QPushButton#dangerButton:hover {{
    background-color: {p['danger_hover']};
}}

/* ── Inputs ── */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_input']};
    border-radius: 6px;
    padding: 6px 8px;
    color: {p['text_input']};
    selection-background-color: {p['selection_bg']};
    selection-color: {p['selection_text']};
}}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {p['accent_border']};
    background-color: {p['bg_input_focus']};
}}

QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
    background-color: {p['bg_main']};
    color: {p['text_tertiary']};
}}

/* Title Input specific */
QLineEdit#titleInput {{
    font-size: 16px;
    font-weight: 600;
    padding: 8px 10px;
    border: 1px solid transparent;
    background-color: transparent;
}}

QLineEdit#titleInput:hover {{
    border: 1px solid {p['border_input']};
    background-color: {p['bg_input']};
}}

QLineEdit#titleInput:focus {{
    border: 1px solid {p['accent_border']};
    background-color: {p['bg_input']};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {p['bg_input']};
    border: 1px solid {p['border_input']};
    border-radius: 6px;
    padding: 5px 10px;
    color: {p['text_input']};
}}

QComboBox:hover {{
    border-color: {p['accent_border']};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {p['bg_menu']};
    border: 1px solid {p['border_menu']};
    selection-background-color: {p['accent']};
    selection-color: {p['selection_text']};
    color: {p['text_input']};
    border-radius: 4px;
    padding: 4px;
}}

/* ── SpinBox buttons ── */
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {p['bg_button']};
    border: 1px solid {p['border_button']};
    border-radius: 3px;
    width: 14px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {p['bg_button_hover']};
    border-color: {p['accent_border']};
}}

/* ── Lists ── */
QListWidget, QTreeWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    margin: 2px 4px;
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {p['bg_button']};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {p['bg_selected']};
    color: {p['text_selected']};
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {p['bg_scroll_handle']};
    min-height: 25px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p['bg_scroll_handle_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {p['bg_scroll_handle']};
    min-width: 25px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {p['bg_scroll_handle_hover']};
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── ToolBar & Menu ── */
QMenuBar {{
    background-color: {p['bg_menubar']};
    border-bottom: 1px solid {p['border']};
    padding: 2px 6px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
    color: {p['text_primary']};
}}

QMenuBar::item:selected {{
    background: {p['bg_button']};
}}

QMenu {{
    background-color: {p['bg_menu']};
    border: 1px solid {p['border_menu']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
    color: {p['text_primary']};
}}

QMenu::item:selected {{
    background-color: {p['accent']};
    color: {p['selection_text']};
}}

QMenu::separator {{
    height: 1px;
    background: {p['border']};
    margin: 4px 8px;
}}

QStatusBar {{
    background-color: {p['bg_sidebar']};
    border-top: 1px solid {p['border']};
    color: {p['text_tertiary']};
    font-size: 12px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {p['border']};
    background-color: {p['bg_main']};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {p['bg_tab']};
    border: 1px solid {p['border_tab']};
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {p['text_tertiary']};
}}

QTabBar::tab:selected {{
    background-color: {p['bg_tab_selected']};
    border-color: {p['accent_border']};
    color: {p['text_primary']};
    font-weight: bold;
}}

QTabBar::tab:hover {{
    background-color: {p['bg_button_hover']};
    color: {p['text_primary']};
}}

/* ── Preview pane specific ── */
QFrame#previewFrame QPlainTextEdit {{
    background-color: {bg_preview};
    border: 1px solid {p['border']};
    border-radius: 6px;
    color: {p['text_primary']};
    padding: 10px;
}}

/* ── Editor template area ── */
QFrame#editorFrame QPlainTextEdit {{
    background-color: {p['bg_input']};
}}

/* ── Labels inside side panels ── */
QLabel {{
    color: {p['text_primary']};
}}

/* ── CheckBox / Radio (if used later) ── */
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p['border_input']};
    border-radius: 3px;
    background-color: {p['bg_input']};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {p['accent']};
    border-color: {p['accent_border']};
}}

/* ── Dialog buttons ── */
QDialogButtonBox QPushButton {{
    min-width: 70px;
}}

/* ── QMessageBox ── */
QMessageBox {{
    background-color: {p['bg_main']};
}}
"""


# ---------------------------------------------------------------------------
# Palette definitions — each theme is a dict of color tokens
# ---------------------------------------------------------------------------

_PALETTES: Dict[str, Dict] = {
    # 1. Midnight Dark — original Breeze / KDE aligned dark (default)
    "midnight_dark": {
        "name": "Midnight Dark",
        "variant": "dark",
        "description": "Original KDE Breeze-inspired slate dark — deep, calm, blue-accented",
        "palette": {
            "bg_main": "#121417",
            "bg_sidebar": "#16191f",
            "bg_list": "#1a1d24",
            "bg_input": "#1a1e26",
            "bg_input_focus": "#1e222c",
            "bg_button": "#232833",
            "bg_button_hover": "#2e3544",
            "bg_button_pressed": "#1c2029",
            "bg_menubar": "#16191f",
            "bg_menu": "#1e222c",
            "bg_tab": "#1a1d24",
            "bg_tab_selected": "#121417",
            "bg_scroll_handle": "#333a47",
            "bg_scroll_handle_hover": "#475569",
            "bg_selected": "#2563eb",
            "bg_splitter": "#1f242d",
            "bg_splitter_hover": "#3b82f6",
            "bg_preview": "#0f1115",
            "border": "#232833",
            "border_input": "#2d3340",
            "border_button": "#333a47",
            "border_menu": "#333a47",
            "border_tab": "#232833",
            "text_primary": "#e2e8f0",
            "text_secondary": "#94a3b8",
            "text_tertiary": "#64748b",
            "text_input": "#f8fafc",
            "text_selected": "#ffffff",
            "accent": "#2563eb",
            "accent_hover": "#1d4ed8",
            "accent_border": "#3b82f6",
            "accent_active": "#60a5fa",
            "danger_bg": "#7f1d1d",
            "danger_border": "#991b1b",
            "danger_hover": "#991b1b",
            "danger_text": "#fecaca",
            "selection_bg": "#2563eb",
            "selection_text": "#ffffff",
        },
    },
    # 2. Midnight Light — airy light counterpart
    "midnight_light": {
        "name": "Midnight Light",
        "variant": "light",
        "description": "Clean light theme — soft slate, white cards, same blue accent",
        "palette": {
            "bg_main": "#f8fafc",
            "bg_sidebar": "#f1f5f9",
            "bg_list": "#ffffff",
            "bg_input": "#ffffff",
            "bg_input_focus": "#f1f5f9",
            "bg_button": "#e2e8f0",
            "bg_button_hover": "#cbd5e1",
            "bg_button_pressed": "#94a3b8",
            "bg_menubar": "#f1f5f9",
            "bg_menu": "#ffffff",
            "bg_tab": "#f1f5f9",
            "bg_tab_selected": "#ffffff",
            "bg_scroll_handle": "#cbd5e1",
            "bg_scroll_handle_hover": "#94a3b8",
            "bg_selected": "#2563eb",
            "bg_splitter": "#e2e8f0",
            "bg_splitter_hover": "#3b82f6",
            "bg_preview": "#ffffff",
            "border": "#e2e8f0",
            "border_input": "#cbd5e1",
            "border_button": "#cbd5e1",
            "border_menu": "#e2e8f0",
            "border_tab": "#e2e8f0",
            "text_primary": "#0f172a",
            "text_secondary": "#475569",
            "text_tertiary": "#64748b",
            "text_input": "#0f172a",
            "text_selected": "#ffffff",
            "accent": "#2563eb",
            "accent_hover": "#1d4ed8",
            "accent_border": "#3b82f6",
            "accent_active": "#60a5fa",
            "danger_bg": "#fef2f2",
            "danger_border": "#fecaca",
            "danger_hover": "#fecaca",
            "danger_text": "#991b1b",
            "selection_bg": "#2563eb",
            "selection_text": "#ffffff",
        },
    },
    # 3. Nord — Arctic, north-bluish polar night
    "nord": {
        "name": "Nord",
        "variant": "dark",
        "description": "Arctic-inspired — Polar Night blues with Frost accent",
        "palette": {
            "bg_main": "#2e3440",
            "bg_sidebar": "#2e3440",
            "bg_list": "#3b4252",
            "bg_input": "#3b4252",
            "bg_input_focus": "#434c5e",
            "bg_button": "#434c5e",
            "bg_button_hover": "#4c566a",
            "bg_button_pressed": "#2e3440",
            "bg_menubar": "#2e3440",
            "bg_menu": "#3b4252",
            "bg_tab": "#3b4252",
            "bg_tab_selected": "#2e3440",
            "bg_scroll_handle": "#4c566a",
            "bg_scroll_handle_hover": "#616e88",
            "bg_selected": "#88c0d0",
            "bg_splitter": "#3b4252",
            "bg_splitter_hover": "#88c0d0",
            "bg_preview": "#2e3440",
            "border": "#3b4252",
            "border_input": "#4c566a",
            "border_button": "#4c566a",
            "border_menu": "#4c566a",
            "border_tab": "#3b4252",
            "text_primary": "#eceff4",
            "text_secondary": "#d8dee9",
            "text_tertiary": "#7b88a1",
            "text_input": "#eceff4",
            "text_selected": "#2e3440",
            "accent": "#88c0d0",
            "accent_hover": "#81a1c1",
            "accent_border": "#81a1c1",
            "accent_active": "#8fbcbb",
            "danger_bg": "#4c1a1f",
            "danger_border": "#bf616a",
            "danger_hover": "#bf616a",
            "danger_text": "#eceff4",
            "selection_bg": "#88c0d0",
            "selection_text": "#2e3440",
        },
    },
    # 4. Dracula — purple-cyan, the classic
    "dracula": {
        "name": "Dracula",
        "variant": "dark",
        "description": "Vampire-favourite — deep purple-gray with pink & cyan pops",
        "palette": {
            "bg_main": "#282a36",
            "bg_sidebar": "#21222c",
            "bg_list": "#343746",
            "bg_input": "#44475a",
            "bg_input_focus": "#52556a",
            "bg_button": "#44475a",
            "bg_button_hover": "#6272a4",
            "bg_button_pressed": "#21222c",
            "bg_menubar": "#21222c",
            "bg_menu": "#343746",
            "bg_tab": "#44475a",
            "bg_tab_selected": "#282a36",
            "bg_scroll_handle": "#6272a4",
            "bg_scroll_handle_hover": "#8a94b8",
            "bg_selected": "#bd93f9",
            "bg_splitter": "#44475a",
            "bg_splitter_hover": "#bd93f9",
            "bg_preview": "#21222c",
            "border": "#44475a",
            "border_input": "#6272a4",
            "border_button": "#6272a4",
            "border_menu": "#44475a",
            "border_tab": "#44475a",
            "text_primary": "#f8f8f2",
            "text_secondary": "#c0c0d0",
            "text_tertiary": "#6272a4",
            "text_input": "#f8f8f2",
            "text_selected": "#ffffff",
            "accent": "#bd93f9",
            "accent_hover": "#ff79c6",
            "accent_border": "#bd93f9",
            "accent_active": "#ff79c6",
            "danger_bg": "#7a2530",
            "danger_border": "#ff5555",
            "danger_hover": "#ff5555",
            "danger_text": "#f8f8f2",
            "selection_bg": "#bd93f9",
            "selection_text": "#ffffff",
        },
    },
    # 5. Catppuccin Mocha — cozy pastel dark
    "catppuccin_mocha": {
        "name": "Catppuccin Mocha",
        "variant": "dark",
        "description": "Soothing pastel dark — Mocha base with sky-blue accent",
        "palette": {
            "bg_main": "#1e1e2e",
            "bg_sidebar": "#181825",
            "bg_list": "#181825",
            "bg_input": "#313244",
            "bg_input_focus": "#45475a",
            "bg_button": "#313244",
            "bg_button_hover": "#45475a",
            "bg_button_pressed": "#181825",
            "bg_menubar": "#181825",
            "bg_menu": "#313244",
            "bg_tab": "#313244",
            "bg_tab_selected": "#1e1e2e",
            "bg_scroll_handle": "#45475a",
            "bg_scroll_handle_hover": "#585b70",
            "bg_selected": "#89b4fa",
            "bg_splitter": "#313244",
            "bg_splitter_hover": "#89b4fa",
            "bg_preview": "#181825",
            "border": "#313244",
            "border_input": "#45475a",
            "border_button": "#585b70",
            "border_menu": "#45475a",
            "border_tab": "#313244",
            "text_primary": "#cdd6f4",
            "text_secondary": "#bac2de",
            "text_tertiary": "#7f849c",
            "text_input": "#cdd6f4",
            "text_selected": "#1e1e2e",
            "accent": "#89b4fa",
            "accent_hover": "#74c7ec",
            "accent_border": "#89b4fa",
            "accent_active": "#74c7ec",
            "danger_bg": "#5a2a3a",
            "danger_border": "#f38ba8",
            "danger_hover": "#f38ba8",
            "danger_text": "#f5c2e7",
            "selection_bg": "#89b4fa",
            "selection_text": "#1e1e2e",
        },
    },
    # 6. Catppuccin Latte — bright, warm light
    "catppuccin_latte": {
        "name": "Catppuccin Latte",
        "variant": "light",
        "description": "Warm light — creamy Latte with blue accent",
        "palette": {
            "bg_main": "#eff1f5",
            "bg_sidebar": "#e6e9ef",
            "bg_list": "#ffffff",
            "bg_input": "#ffffff",
            "bg_input_focus": "#e6e9ef",
            "bg_button": "#ccd0da",
            "bg_button_hover": "#bcc0cc",
            "bg_button_pressed": "#acb0be",
            "bg_menubar": "#e6e9ef",
            "bg_menu": "#ffffff",
            "bg_tab": "#e6e9ef",
            "bg_tab_selected": "#eff1f5",
            "bg_scroll_handle": "#bcc0cc",
            "bg_scroll_handle_hover": "#acb0be",
            "bg_selected": "#1e66f5",
            "bg_splitter": "#ccd0da",
            "bg_splitter_hover": "#1e66f5",
            "bg_preview": "#ffffff",
            "border": "#ccd0da",
            "border_input": "#bcc0cc",
            "border_button": "#bcc0cc",
            "border_menu": "#ccd0da",
            "border_tab": "#ccd0da",
            "text_primary": "#4c4f69",
            "text_secondary": "#5c5f77",
            "text_tertiary": "#8c8fa1",
            "text_input": "#4c4f69",
            "text_selected": "#ffffff",
            "accent": "#1e66f5",
            "accent_hover": "#04a5e5",
            "accent_border": "#1e66f5",
            "accent_active": "#209fb5",
            "danger_bg": "#f9d5d9",
            "danger_border": "#d20f39",
            "danger_hover": "#d20f39",
            "danger_text": "#4c4f69",
            "selection_bg": "#1e66f5",
            "selection_text": "#ffffff",
        },
    },
    # 7. Gruvbox Dark — retro groove, warm brown-yellow
    "gruvbox_dark": {
        "name": "Gruvbox Dark",
        "variant": "dark",
        "description": "Retro groove — warm dark wood with vibrant yellow accent",
        "palette": {
            "bg_main": "#282828",
            "bg_sidebar": "#1d2021",
            "bg_list": "#3c3836",
            "bg_input": "#3c3836",
            "bg_input_focus": "#504945",
            "bg_button": "#3c3836",
            "bg_button_hover": "#504945",
            "bg_button_pressed": "#1d2021",
            "bg_menubar": "#1d2021",
            "bg_menu": "#3c3836",
            "bg_tab": "#3c3836",
            "bg_tab_selected": "#282828",
            "bg_scroll_handle": "#504945",
            "bg_scroll_handle_hover": "#665c54",
            "bg_selected": "#fabd2f",
            "bg_splitter": "#3c3836",
            "bg_splitter_hover": "#fabd2f",
            "bg_preview": "#1d2021",
            "border": "#3c3836",
            "border_input": "#504945",
            "border_button": "#665c54",
            "border_menu": "#504945",
            "border_tab": "#3c3836",
            "text_primary": "#ebdbb2",
            "text_secondary": "#d5c4a1",
            "text_tertiary": "#928374",
            "text_input": "#fbf1c7",
            "text_selected": "#282828",
            "accent": "#fabd2f",
            "accent_hover": "#fe8019",
            "accent_border": "#fabd2f",
            "accent_active": "#fe8019",
            "danger_bg": "#7a2a1f",
            "danger_border": "#fb4934",
            "danger_hover": "#fb4934",
            "danger_text": "#fbf1c7",
            "selection_bg": "#fabd2f",
            "selection_text": "#282828",
        },
    },
    # 8. Gruvbox Light — soft warm light
    "gruvbox_light": {
        "name": "Gruvbox Light",
        "variant": "light",
        "description": "Warm paper light — Gruvbox's sunny side",
        "palette": {
            "bg_main": "#fbf1c7",
            "bg_sidebar": "#ebdbb2",
            "bg_list": "#fbf1c7",
            "bg_input": "#ffffff",
            "bg_input_focus": "#ebdbb2",
            "bg_button": "#ebdbb2",
            "bg_button_hover": "#d5c4a1",
            "bg_button_pressed": "#bdae93",
            "bg_menubar": "#ebdbb2",
            "bg_menu": "#fbf1c7",
            "bg_tab": "#ebdbb2",
            "bg_tab_selected": "#fbf1c7",
            "bg_scroll_handle": "#bdae93",
            "bg_scroll_handle_hover": "#928374",
            "bg_selected": "#d65d0e",
            "bg_splitter": "#ebdbb2",
            "bg_splitter_hover": "#d65d0e",
            "bg_preview": "#ffffff",
            "border": "#d5c4a1",
            "border_input": "#bdae93",
            "border_button": "#bdae93",
            "border_menu": "#d5c4a1",
            "border_tab": "#d5c4a1",
            "text_primary": "#3c3836",
            "text_secondary": "#504945",
            "text_tertiary": "#7c6f64",
            "text_input": "#282828",
            "text_selected": "#ffffff",
            "accent": "#d65d0e",
            "accent_hover": "#af3a03",
            "accent_border": "#d65d0e",
            "accent_active": "#af3a03",
            "danger_bg": "#f9d0cc",
            "danger_border": "#cc241d",
            "danger_hover": "#cc241d",
            "danger_text": "#3c3836",
            "selection_bg": "#d65d0e",
            "selection_text": "#ffffff",
        },
    },
    # 9. Solarized Dark — precision, low-contrast etched
    "solarized_dark": {
        "name": "Solarized Dark",
        "variant": "dark",
        "description": "Precision optics — deep teal with Solarized precision",
        "palette": {
            "bg_main": "#002b36",
            "bg_sidebar": "#073642",
            "bg_list": "#002b36",
            "bg_input": "#073642",
            "bg_input_focus": "#0a4a5a",
            "bg_button": "#073642",
            "bg_button_hover": "#586e75",
            "bg_button_pressed": "#002b36",
            "bg_menubar": "#073642",
            "bg_menu": "#073642",
            "bg_tab": "#073642",
            "bg_tab_selected": "#002b36",
            "bg_scroll_handle": "#586e75",
            "bg_scroll_handle_hover": "#657b83",
            "bg_selected": "#268bd2",
            "bg_splitter": "#073642",
            "bg_splitter_hover": "#268bd2",
            "bg_preview": "#073642",
            "border": "#073642",
            "border_input": "#586e75",
            "border_button": "#586e75",
            "border_menu": "#586e75",
            "border_tab": "#073642",
            "text_primary": "#eee8d5",
            "text_secondary": "#93a1a1",
            "text_tertiary": "#586e75",
            "text_input": "#fdf6e3",
            "text_selected": "#ffffff",
            "accent": "#268bd2",
            "accent_hover": "#2aa198",
            "accent_border": "#268bd2",
            "accent_active": "#2aa198",
            "danger_bg": "#5a1f1a",
            "danger_border": "#dc322f",
            "danger_hover": "#dc322f",
            "danger_text": "#fdf6e3",
            "selection_bg": "#268bd2",
            "selection_text": "#ffffff",
        },
    },
    # 10. Solarized Light — warm paper, complementary
    "solarized_light": {
        "name": "Solarized Light",
        "variant": "light",
        "description": "Warm paper — Solarized light with gentle blue accent",
        "palette": {
            "bg_main": "#fdf6e3",
            "bg_sidebar": "#eee8d5",
            "bg_list": "#ffffff",
            "bg_input": "#ffffff",
            "bg_input_focus": "#eee8d5",
            "bg_button": "#eee8d5",
            "bg_button_hover": "#93a1a1",
            "bg_button_pressed": "#93a1a1",
            "bg_menubar": "#eee8d5",
            "bg_menu": "#fdf6e3",
            "bg_tab": "#eee8d5",
            "bg_tab_selected": "#fdf6e3",
            "bg_scroll_handle": "#93a1a1",
            "bg_scroll_handle_hover": "#586e75",
            "bg_selected": "#268bd2",
            "bg_splitter": "#eee8d5",
            "bg_splitter_hover": "#268bd2",
            "bg_preview": "#ffffff",
            "border": "#eee8d5",
            "border_input": "#93a1a1",
            "border_button": "#93a1a1",
            "border_menu": "#eee8d5",
            "border_tab": "#eee8d5",
            "text_primary": "#002b36",
            "text_secondary": "#586e75",
            "text_tertiary": "#93a1a1",
            "text_input": "#073642",
            "text_selected": "#ffffff",
            "accent": "#268bd2",
            "accent_hover": "#2aa198",
            "accent_border": "#268bd2",
            "accent_active": "#2aa198",
            "danger_bg": "#fbe3e1",
            "danger_border": "#dc322f",
            "danger_hover": "#dc322f",
            "danger_text": "#002b36",
            "selection_bg": "#268bd2",
            "selection_text": "#ffffff",
        },
    },
    # 11. Tokyo Night — neon night city
    "tokyo_night": {
        "name": "Tokyo Night",
        "variant": "dark",
        "description": "Neon night city — deep navy with electric blue-purple",
        "palette": {
            "bg_main": "#1a1b26",
            "bg_sidebar": "#16161e",
            "bg_list": "#24283b",
            "bg_input": "#24283b",
            "bg_input_focus": "#414868",
            "bg_button": "#24283b",
            "bg_button_hover": "#414868",
            "bg_button_pressed": "#16161e",
            "bg_menubar": "#16161e",
            "bg_menu": "#24283b",
            "bg_tab": "#24283b",
            "bg_tab_selected": "#1a1b26",
            "bg_scroll_handle": "#414868",
            "bg_scroll_handle_hover": "#565f89",
            "bg_selected": "#7aa2f7",
            "bg_splitter": "#24283b",
            "bg_splitter_hover": "#7aa2f7",
            "bg_preview": "#16161e",
            "border": "#24283b",
            "border_input": "#414868",
            "border_button": "#414868",
            "border_menu": "#414868",
            "border_tab": "#24283b",
            "text_primary": "#c0caf5",
            "text_secondary": "#a9b1d6",
            "text_tertiary": "#565f89",
            "text_input": "#c0caf5",
            "text_selected": "#1a1b26",
            "accent": "#7aa2f7",
            "accent_hover": "#7dcfff",
            "accent_border": "#7aa2f7",
            "accent_active": "#bb9af7",
            "danger_bg": "#5a1f2a",
            "danger_border": "#f7768e",
            "danger_hover": "#f7768e",
            "danger_text": "#c0caf5",
            "selection_bg": "#7aa2f7",
            "selection_text": "#1a1b26",
        },
    },
    # 12. Rosé Pine — soft, muted, warm
    "rose_pine": {
        "name": "Rosé Pine",
        "variant": "dark",
        "description": "Soft bloom — muted pine with rose & iris accents",
        "palette": {
            "bg_main": "#191724",
            "bg_sidebar": "#1f1d2e",
            "bg_list": "#26233a",
            "bg_input": "#26233a",
            "bg_input_focus": "#403d52",
            "bg_button": "#26233a",
            "bg_button_hover": "#403d52",
            "bg_button_pressed": "#191724",
            "bg_menubar": "#1f1d2e",
            "bg_menu": "#26233a",
            "bg_tab": "#26233a",
            "bg_tab_selected": "#191724",
            "bg_scroll_handle": "#6e6a86",
            "bg_scroll_handle_hover": "#908caa",
            "bg_selected": "#eb6f92",
            "bg_splitter": "#26233a",
            "bg_splitter_hover": "#eb6f92",
            "bg_preview": "#1f1d2e",
            "border": "#26233a",
            "border_input": "#403d52",
            "border_button": "#6e6a86",
            "border_menu": "#403d52",
            "border_tab": "#26233a",
            "text_primary": "#e0def4",
            "text_secondary": "#908caa",
            "text_tertiary": "#6e6a86",
            "text_input": "#e0def4",
            "text_selected": "#191724",
            "accent": "#c4a7e7",
            "accent_hover": "#eb6f92",
            "accent_border": "#c4a7e7",
            "accent_active": "#eb6f92",
            "danger_bg": "#5a2d3a",
            "danger_border": "#eb6f92",
            "danger_hover": "#eb6f92",
            "danger_text": "#e0def4",
            "selection_bg": "#eb6f92",
            "selection_text": "#191724",
        },
    },
    # 13. Everforest — green, comfortable, organic dark
    "everforest": {
        "name": "Everforest Dark",
        "variant": "dark",
        "description": "Forest comfort — muted teal-green, eye-friendly dark",
        "palette": {
            "bg_main": "#2b3339",
            "bg_sidebar": "#272e33",
            "bg_list": "#323c41",
            "bg_input": "#323c41",
            "bg_input_focus": "#3a454a",
            "bg_button": "#323c41",
            "bg_button_hover": "#425047",
            "bg_button_pressed": "#272e33",
            "bg_menubar": "#272e33",
            "bg_menu": "#323c41",
            "bg_tab": "#323c41",
            "bg_tab_selected": "#2b3339",
            "bg_scroll_handle": "#4f5858",
            "bg_scroll_handle_hover": "#859289",
            "bg_selected": "#83c092",
            "bg_splitter": "#323c41",
            "bg_splitter_hover": "#83c092",
            "bg_preview": "#272e33",
            "border": "#323c41",
            "border_input": "#4f5858",
            "border_button": "#4f5858",
            "border_menu": "#4f5858",
            "border_tab": "#323c41",
            "text_primary": "#d3c6aa",
            "text_secondary": "#9da9a0",
            "text_tertiary": "#859289",
            "text_input": "#d3c6aa",
            "text_selected": "#2b3339",
            "accent": "#83c092",
            "accent_hover": "#a7c080",
            "accent_border": "#83c092",
            "accent_active": "#a7c080",
            "danger_bg": "#543331",
            "danger_border": "#e67e80",
            "danger_hover": "#e67e80",
            "danger_text": "#d3c6aa",
            "selection_bg": "#83c092",
            "selection_text": "#2b3339",
        },
    },
}


# Build Theme objects eagerly
_THEMES: Dict[str, Theme] = {}
for _tid, _info in _PALETTES.items():
    _p = _info["palette"]
    _ss = _build_stylesheet(_p)
    _THEMES[_tid] = Theme(
        id=_tid,
        name=_info["name"],
        variant=_info["variant"],
        description=_info["description"],
        stylesheet=_ss,
    )

# Convenience collections
THEMES: Dict[str, Theme] = _THEMES
THEME_IDS: List[str] = list(_THEMES.keys())
DEFAULT_THEME: str = "midnight_dark"

# Backwards-compat aliases — old code imported DARK_STYLESHEET
DARK_STYLESHEET: str = _THEMES["midnight_dark"].stylesheet
LIGHT_STYLESHEET: str = _THEMES["midnight_light"].stylesheet

# Highlighter palette per theme (used by highlighter.py)
# Each entry maps syntax element -> hex color
HIGHLIGHTER_PALETTES: Dict[str, Dict[str, str]] = {
    "midnight_dark": {
        "variable_fg": "#fbbf24",
        "variable_bg": "#2d2415",
        "heading": "#60a5fa",
        "role": "#34d399",
        "code": "#f472b6",
        "error": "#f87171",
    },
    "midnight_light": {
        "variable_fg": "#b45309",
        "variable_bg": "#fef3c7",
        "heading": "#2563eb",
        "role": "#059669",
        "code": "#db2777",
        "error": "#dc2626",
    },
    "nord": {
        "variable_fg": "#ebcb8b",
        "variable_bg": "#4c566a",
        "heading": "#81a1c1",
        "role": "#a3be8c",
        "code": "#b48ead",
        "error": "#bf616a",
    },
    "dracula": {
        "variable_fg": "#f1fa8c",
        "variable_bg": "#44475a",
        "heading": "#bd93f9",
        "role": "#50fa7b",
        "code": "#ff79c6",
        "error": "#ff5555",
    },
    "catppuccin_mocha": {
        "variable_fg": "#f9e2af",
        "variable_bg": "#45475a",
        "heading": "#89b4fa",
        "role": "#a6e3a1",
        "code": "#f38ba8",
        "error": "#f38ba8",
    },
    "catppuccin_latte": {
        "variable_fg": "#df8e1d",
        "variable_bg": "#ccd0da",
        "heading": "#1e66f5",
        "role": "#40a02b",
        "code": "#ea76cb",
        "error": "#d20f39",
    },
    "gruvbox_dark": {
        "variable_fg": "#fabd2f",
        "variable_bg": "#504945",
        "heading": "#83a598",
        "role": "#b8bb26",
        "code": "#d3869b",
        "error": "#fb4934",
    },
    "gruvbox_light": {
        "variable_fg": "#b57614",
        "variable_bg": "#ebdbb2",
        "heading": "#076678",
        "role": "#79740e",
        "code": "#8f3f71",
        "error": "#9d0006",
    },
    "solarized_dark": {
        "variable_fg": "#b58900",
        "variable_bg": "#073642",
        "heading": "#268bd2",
        "role": "#859900",
        "code": "#d33682",
        "error": "#dc322f",
    },
    "solarized_light": {
        "variable_fg": "#b58900",
        "variable_bg": "#eee8d5",
        "heading": "#268bd2",
        "role": "#859900",
        "code": "#d33682",
        "error": "#dc322f",
    },
    "tokyo_night": {
        "variable_fg": "#e0af68",
        "variable_bg": "#414868",
        "heading": "#7aa2f7",
        "role": "#9ece6a",
        "code": "#bb9af7",
        "error": "#f7768e",
    },
    "rose_pine": {
        "variable_fg": "#f6c177",
        "variable_bg": "#403d52",
        "heading": "#c4a7e7",
        "role": "#9ccfd8",
        "code": "#eb6f92",
        "error": "#eb6f92",
    },
    "everforest": {
        "variable_fg": "#dbbc7f",
        "variable_bg": "#3a454a",
        "heading": "#83c092",
        "role": "#a7c080",
        "code": "#d699b6",
        "error": "#e67e80",
    },
}


def get_theme(theme_id: str) -> Theme:
    """Return Theme by id, falling back to default."""
    return _THEMES.get(theme_id, _THEMES[DEFAULT_THEME])


def get_stylesheet(theme_id: str) -> str:
    """Return QSS string for a theme id, falling back to default."""
    return get_theme(theme_id).stylesheet


def list_themes() -> List[Theme]:
    """Return all themes in definition order."""
    return list(_THEMES.values())


def get_highlighter_palette(theme_id: str) -> Dict[str, str]:
    """Return highlighter color dict for a theme."""
    return HIGHLIGHTER_PALETTES.get(theme_id, HIGHLIGHTER_PALETTES[DEFAULT_THEME])


def is_dark_theme(theme_id: str) -> bool:
    return get_theme(theme_id).is_dark


def is_light_theme(theme_id: str) -> bool:
    return get_theme(theme_id).is_light
