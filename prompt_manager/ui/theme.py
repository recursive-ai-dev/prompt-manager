"""Theme registry — Expanded library of handcrafted, atmospheric, and designer QSS themes.

Categories:
- Core & Popular (Midnight, Nord, Dracula, Catppuccin, Gruvbox, Solarized, Tokyo Night, Rose Pine, Everforest)
- Glow & Neon (Cyberpunk Neon, Synthwave Glow, Matrix Glow)
- Bland / Professional (Corporate Slate, Office Paper, Enterprise Light)
- High Contrast (High Contrast Dark, High Contrast Light, Amber OLED)
- Retro Computing (Macintosh System 7, Windows 95, Commodore 64, IBM VGA 80s)
- Psychological Horror (Silent Hill Fog, Blood Moon Eldritch, Liminal Asylum)
- Terminal & CRT (VT100 Amber CRT, Monokai Pro, Ubuntu Terminal, DOS Matrix)
- Minimalist (Pure Monolith, Ghost Paper, Tokyo Minimal)
- Cartoonish & Playful (Bubblegum Pop, Comic Book Ink, Arcade 8-Bit)
- Blackened Atmospheric (Burzum Forest, Darkthrone Frost, Behemoth Obsidian, Cascadian Gloom)
- Unique Designer (Bauhaus Geometric, Swiss Typography, Art Deco Gold, Solar Flare)

Each theme is cross-platform OS font-aware (macOS, Windows, Linux) and built from palette definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from prompt_manager.ui.fonts import get_ui_font_css


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    variant: str  # "dark" | "light"
    category: str  # e.g. "Glow", "Retro", "Horror", "Professional", "Blackened", etc.
    description: str
    stylesheet: str

    @property
    def is_dark(self) -> bool:
        return self.variant == "dark"

    @property
    def is_light(self) -> bool:
        return self.variant == "light"


def _build_stylesheet(p: Dict[str, str]) -> str:
    """Generate the full QSS string from a palette dict with OS-aware typography and custom rules."""
    font_cat = p.get("font_category", "sans")
    font_size = p.get("font_size", "13px")
    font_css = get_ui_font_css(font_cat, font_size)

    bg_preview = p.get("bg_preview", p["bg_input"])
    custom_qss = p.get("custom_css", "")

    return f"""
QMainWindow, QDialog {{
    background-color: {p['bg_main']};
    color: {p['text_primary']};
}}

QWidget {{
    color: {p['text_primary']};
    {font_css}
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

/* Title Input */
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

/* ── SpinBox ── */
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

/* ── Lists & Trees ── */
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

/* ── Menus & MenuBar ── */
QMenuBar {{
    background-color: {p['bg_menubar']};
    border-bottom: 1px solid {p['border']};
    padding: 2px 6px;
    color: {p['text_primary']};
}}

QMenuBar::item {{
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {p['bg_button']};
    color: {p['text_primary']};
}}

QMenuBar::item:pressed {{
    background-color: {p['bg_selected']};
}}

QMenu {{
    background-color: {p['bg_menu']};
    border: 1px solid {p['border_menu']};
    border-radius: 8px;
    padding: 4px;
    color: {p['text_primary']};
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {p['bg_selected']};
    color: {p['text_selected']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {p['border']};
    margin: 4px 8px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {p['bg_sidebar']};
    border-top: 1px solid {p['border']};
    color: {p['text_secondary']};
    font-size: 11px;
    padding: 2px 8px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {p['border']};
    border-radius: 6px;
    background-color: {p['bg_main']};
}}

QTabBar::tab {{
    background-color: {p['bg_tab']};
    color: {p['text_secondary']};
    border: 1px solid {p['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 14px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {p['bg_tab_selected']};
    color: {p['text_primary']};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background-color: {p['bg_button_hover']};
    color: {p['text_primary']};
}}

/* ── Preview Output Panel ── */
QPlainTextEdit#previewOutput {{
    background-color: {bg_preview};
    border: 1px solid {p['border_input']};
    border-radius: 6px;
    padding: 8px;
    color: {p['text_input']};
}}

/* ── Custom Theme Enhancements ── */
{custom_qss}
"""


# ── Palette Definitions ──────────────────────────────────────────────────

PALETTES: Dict[str, Dict[str, str]] = {
    # ── 1. Core Favorites ───────────────────────────────────────────────
    "midnight_dark": {
        "bg_main": "#0f172a",
        "bg_sidebar": "#1e293b",
        "bg_list": "#0f172a",
        "bg_input": "#1e293b",
        "bg_input_focus": "#0f172a",
        "bg_preview": "#0a0f1d",
        "bg_button": "#334155",
        "bg_button_hover": "#475569",
        "bg_button_pressed": "#1e293b",
        "bg_menubar": "#1e293b",
        "bg_menu": "#1e293b",
        "bg_tab": "#1e293b",
        "bg_tab_selected": "#0f172a",
        "bg_scroll_handle": "#475569",
        "bg_scroll_handle_hover": "#64748b",
        "bg_selected": "#0284c7",
        "bg_splitter": "#334155",
        "bg_splitter_hover": "#38bdf8",
        "border": "#334155",
        "border_input": "#475569",
        "border_button": "#475569",
        "border_menu": "#334155",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_tertiary": "#64748b",
        "text_input": "#f8fafc",
        "text_selected": "#ffffff",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "accent_border": "#38bdf8",
        "accent_active": "#0284c7",
        "danger_bg": "#dc2626",
        "danger_border": "#b91c1c",
        "danger_hover": "#ef4444",
        "danger_text": "#ffffff",
        "selection_bg": "#0284c7",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "midnight_light": {
        "bg_main": "#f8fafc",
        "bg_sidebar": "#f1f5f9",
        "bg_list": "#f8fafc",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#f1f5f9",
        "bg_button": "#e2e8f0",
        "bg_button_hover": "#cbd5e1",
        "bg_button_pressed": "#e2e8f0",
        "bg_menubar": "#f1f5f9",
        "bg_menu": "#ffffff",
        "bg_tab": "#e2e8f0",
        "bg_tab_selected": "#f8fafc",
        "bg_scroll_handle": "#cbd5e1",
        "bg_scroll_handle_hover": "#94a3b8",
        "bg_selected": "#0284c7",
        "bg_splitter": "#e2e8f0",
        "bg_splitter_hover": "#0284c7",
        "border": "#e2e8f0",
        "border_input": "#cbd5e1",
        "border_button": "#cbd5e1",
        "border_menu": "#e2e8f0",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_tertiary": "#94a3b8",
        "text_input": "#0f172a",
        "text_selected": "#ffffff",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "accent_border": "#0284c7",
        "accent_active": "#0369a1",
        "danger_bg": "#ef4444",
        "danger_border": "#dc2626",
        "danger_hover": "#dc2626",
        "danger_text": "#ffffff",
        "selection_bg": "#0284c7",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "nord": {
        "bg_main": "#2e3440",
        "bg_sidebar": "#242933",
        "bg_list": "#2e3440",
        "bg_input": "#3b4252",
        "bg_input_focus": "#434c5e",
        "bg_preview": "#242933",
        "bg_button": "#434c5e",
        "bg_button_hover": "#4c566a",
        "bg_button_pressed": "#3b4252",
        "bg_menubar": "#242933",
        "bg_menu": "#3b4252",
        "bg_tab": "#3b4252",
        "bg_tab_selected": "#2e3440",
        "bg_scroll_handle": "#4c566a",
        "bg_scroll_handle_hover": "#d8dee9",
        "bg_selected": "#88c0d0",
        "bg_splitter": "#3b4252",
        "bg_splitter_hover": "#88c0d0",
        "border": "#3b4252",
        "border_input": "#4c566a",
        "border_button": "#4c566a",
        "border_menu": "#434c5e",
        "text_primary": "#eceff4",
        "text_secondary": "#d8dee9",
        "text_tertiary": "#4c566a",
        "text_input": "#eceff4",
        "text_selected": "#2e3440",
        "accent": "#88c0d0",
        "accent_hover": "#81a1c1",
        "accent_border": "#8fbcbb",
        "accent_active": "#5e81ac",
        "danger_bg": "#bf616a",
        "danger_border": "#a54e56",
        "danger_hover": "#d08770",
        "danger_text": "#eceff4",
        "selection_bg": "#88c0d0",
        "selection_text": "#2e3440",
        "font_category": "sans",
    },
    "dracula": {
        "bg_main": "#282a36",
        "bg_sidebar": "#21222c",
        "bg_list": "#282a36",
        "bg_input": "#343746",
        "bg_input_focus": "#44475a",
        "bg_preview": "#1e1f29",
        "bg_button": "#44475a",
        "bg_button_hover": "#6272a4",
        "bg_button_pressed": "#343746",
        "bg_menubar": "#21222c",
        "bg_menu": "#343746",
        "bg_tab": "#343746",
        "bg_tab_selected": "#282a36",
        "bg_scroll_handle": "#44475a",
        "bg_scroll_handle_hover": "#6272a4",
        "bg_selected": "#bd93f9",
        "bg_splitter": "#44475a",
        "bg_splitter_hover": "#bd93f9",
        "border": "#44475a",
        "border_input": "#6272a4",
        "border_button": "#6272a4",
        "border_menu": "#44475a",
        "text_primary": "#f8f8f2",
        "text_secondary": "#6272a4",
        "text_tertiary": "#44475a",
        "text_input": "#f8f8f2",
        "text_selected": "#282a36",
        "accent": "#bd93f9",
        "accent_hover": "#ff79c6",
        "accent_border": "#bd93f9",
        "accent_active": "#ff79c6",
        "danger_bg": "#ff5555",
        "danger_border": "#e04444",
        "danger_hover": "#ff6e6e",
        "danger_text": "#f8f8f2",
        "selection_bg": "#bd93f9",
        "selection_text": "#282a36",
        "font_category": "sans",
    },
    "tokyo_night": {
        "bg_main": "#1a1b26",
        "bg_sidebar": "#16161e",
        "bg_list": "#1a1b26",
        "bg_input": "#24283b",
        "bg_input_focus": "#2f3549",
        "bg_preview": "#13141c",
        "bg_button": "#24283b",
        "bg_button_hover": "#414868",
        "bg_button_pressed": "#1f2335",
        "bg_menubar": "#16161e",
        "bg_menu": "#24283b",
        "bg_tab": "#24283b",
        "bg_tab_selected": "#1a1b26",
        "bg_scroll_handle": "#414868",
        "bg_scroll_handle_hover": "#565f89",
        "bg_selected": "#7aa2f7",
        "bg_splitter": "#24283b",
        "bg_splitter_hover": "#7aa2f7",
        "border": "#24283b",
        "border_input": "#414868",
        "border_button": "#414868",
        "border_menu": "#24283b",
        "text_primary": "#c0caf5",
        "text_secondary": "#7aa2f7",
        "text_tertiary": "#565f89",
        "text_input": "#c0caf5",
        "text_selected": "#1a1b26",
        "accent": "#7aa2f7",
        "accent_hover": "#bb9af7",
        "accent_border": "#7aa2f7",
        "accent_active": "#bb9af7",
        "danger_bg": "#f7768e",
        "danger_border": "#db5069",
        "danger_hover": "#ff8e9e",
        "danger_text": "#1a1b26",
        "selection_bg": "#7aa2f7",
        "selection_text": "#1a1b26",
        "font_category": "sans",
    },

    # ── 2. Glow & Neon Themes ──────────────────────────────────────────
    "cyberpunk_neon": {
        "bg_main": "#05050d",
        "bg_sidebar": "#0b0c1b",
        "bg_list": "#05050d",
        "bg_input": "#121324",
        "bg_input_focus": "#181a33",
        "bg_preview": "#040409",
        "bg_button": "#1a1c36",
        "bg_button_hover": "#26294f",
        "bg_button_pressed": "#101222",
        "bg_menubar": "#0b0c1b",
        "bg_menu": "#121324",
        "bg_tab": "#121324",
        "bg_tab_selected": "#05050d",
        "bg_scroll_handle": "#00f0ff",
        "bg_scroll_handle_hover": "#ff007f",
        "bg_selected": "#00f0ff",
        "bg_splitter": "#ff007f",
        "bg_splitter_hover": "#00f0ff",
        "border": "#26294f",
        "border_input": "#00f0ff",
        "border_button": "#ff007f",
        "border_menu": "#00f0ff",
        "text_primary": "#f0f6fc",
        "text_secondary": "#00f0ff",
        "text_tertiary": "#ff007f",
        "text_input": "#00f0ff",
        "text_selected": "#05050d",
        "accent": "#00f0ff",
        "accent_hover": "#ff007f",
        "accent_border": "#00f0ff",
        "accent_active": "#ffe600",
        "danger_bg": "#ff0055",
        "danger_border": "#ff007f",
        "danger_hover": "#ff3377",
        "danger_text": "#ffffff",
        "selection_bg": "#00f0ff",
        "selection_text": "#05050d",
        "font_category": "mono",
    },
    "synthwave_glow": {
        "bg_main": "#181425",
        "bg_sidebar": "#120e1f",
        "bg_list": "#181425",
        "bg_input": "#261d3b",
        "bg_input_focus": "#352752",
        "bg_preview": "#0f0b1a",
        "bg_button": "#352752",
        "bg_button_hover": "#ff388b",
        "bg_button_pressed": "#261d3b",
        "bg_menubar": "#120e1f",
        "bg_menu": "#261d3b",
        "bg_tab": "#261d3b",
        "bg_tab_selected": "#181425",
        "bg_scroll_handle": "#ff388b",
        "bg_scroll_handle_hover": "#fed766",
        "bg_selected": "#ff388b",
        "bg_splitter": "#ff388b",
        "bg_splitter_hover": "#fed766",
        "border": "#3b295e",
        "border_input": "#ff388b",
        "border_button": "#674ab3",
        "border_menu": "#ff388b",
        "text_primary": "#fff0f5",
        "text_secondary": "#fed766",
        "text_tertiary": "#8a75b8",
        "text_input": "#fff0f5",
        "text_selected": "#ffffff",
        "accent": "#ff388b",
        "accent_hover": "#fed766",
        "accent_border": "#ff388b",
        "accent_active": "#00f0ff",
        "danger_bg": "#e63946",
        "danger_border": "#ff388b",
        "danger_hover": "#f72585",
        "danger_text": "#ffffff",
        "selection_bg": "#ff388b",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "matrix_glow": {
        "bg_main": "#030804",
        "bg_sidebar": "#010402",
        "bg_list": "#030804",
        "bg_input": "#061307",
        "bg_input_focus": "#0c260f",
        "bg_preview": "#020503",
        "bg_button": "#0d2810",
        "bg_button_hover": "#134219",
        "bg_button_pressed": "#061307",
        "bg_menubar": "#010402",
        "bg_menu": "#061307",
        "bg_tab": "#061307",
        "bg_tab_selected": "#030804",
        "bg_scroll_handle": "#00ff66",
        "bg_scroll_handle_hover": "#33ff88",
        "bg_selected": "#00ff66",
        "bg_splitter": "#00ff66",
        "bg_splitter_hover": "#33ff88",
        "border": "#0e3312",
        "border_input": "#00ff66",
        "border_button": "#00cc52",
        "border_menu": "#00ff66",
        "text_primary": "#00ff66",
        "text_secondary": "#55ff99",
        "text_tertiary": "#1a662e",
        "text_input": "#00ff66",
        "text_selected": "#030804",
        "accent": "#00ff66",
        "accent_hover": "#33ff88",
        "accent_border": "#00ff66",
        "accent_active": "#ffffff",
        "danger_bg": "#cc1122",
        "danger_border": "#ff3344",
        "danger_hover": "#ff4455",
        "danger_text": "#ffffff",
        "selection_bg": "#00ff66",
        "selection_text": "#030804",
        "font_category": "terminal",
    },

    # ── 3. Bland / Professional Themes ─────────────────────────────────
    "corporate_slate": {
        "bg_main": "#1e222b",
        "bg_sidebar": "#161920",
        "bg_list": "#1e222b",
        "bg_input": "#252a36",
        "bg_input_focus": "#2e3442",
        "bg_preview": "#181b22",
        "bg_button": "#2b313e",
        "bg_button_hover": "#363d4d",
        "bg_button_pressed": "#202530",
        "bg_menubar": "#161920",
        "bg_menu": "#252a36",
        "bg_tab": "#252a36",
        "bg_tab_selected": "#1e222b",
        "bg_scroll_handle": "#3b4354",
        "bg_scroll_handle_hover": "#4f5a70",
        "bg_selected": "#4b6584",
        "bg_splitter": "#2b313e",
        "bg_splitter_hover": "#4b6584",
        "border": "#2b313e",
        "border_input": "#3b4354",
        "border_button": "#3b4354",
        "border_menu": "#2b313e",
        "text_primary": "#d1d8e0",
        "text_secondary": "#a5b1c2",
        "text_tertiary": "#778ca3",
        "text_input": "#f1f2f6",
        "text_selected": "#ffffff",
        "accent": "#4b6584",
        "accent_hover": "#596e79",
        "accent_border": "#778ca3",
        "accent_active": "#2d98da",
        "danger_bg": "#eb3b5a",
        "danger_border": "#fc5c65",
        "danger_hover": "#fc5c65",
        "danger_text": "#ffffff",
        "selection_bg": "#4b6584",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "office_paper": {
        "bg_main": "#f7f7f7",
        "bg_sidebar": "#ebebeb",
        "bg_list": "#f7f7f7",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#f0f0f0",
        "bg_button": "#e0e0e0",
        "bg_button_hover": "#d4d4d4",
        "bg_button_pressed": "#cccccc",
        "bg_menubar": "#ebebeb",
        "bg_menu": "#ffffff",
        "bg_tab": "#e0e0e0",
        "bg_tab_selected": "#f7f7f7",
        "bg_scroll_handle": "#c4c4c4",
        "bg_scroll_handle_hover": "#a8a8a8",
        "bg_selected": "#2c3e50",
        "bg_splitter": "#e0e0e0",
        "bg_splitter_hover": "#2c3e50",
        "border": "#d8d8d8",
        "border_input": "#cccccc",
        "border_button": "#cccccc",
        "border_menu": "#d8d8d8",
        "text_primary": "#2d3436",
        "text_secondary": "#636e72",
        "text_tertiary": "#b2bec3",
        "text_input": "#2d3436",
        "text_selected": "#ffffff",
        "accent": "#2c3e50",
        "accent_hover": "#34495e",
        "accent_border": "#2c3e50",
        "accent_active": "#1abc9c",
        "danger_bg": "#d63031",
        "danger_border": "#b71540",
        "danger_hover": "#e74c3c",
        "danger_text": "#ffffff",
        "selection_bg": "#2c3e50",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "enterprise_light": {
        "bg_main": "#ffffff",
        "bg_sidebar": "#f4f6f8",
        "bg_list": "#ffffff",
        "bg_input": "#ffffff",
        "bg_input_focus": "#f8f9fa",
        "bg_preview": "#f8f9fa",
        "bg_button": "#e9ecef",
        "bg_button_hover": "#dee2e6",
        "bg_button_pressed": "#ced4da",
        "bg_menubar": "#f4f6f8",
        "bg_menu": "#ffffff",
        "bg_tab": "#e9ecef",
        "bg_tab_selected": "#ffffff",
        "bg_scroll_handle": "#ced4da",
        "bg_scroll_handle_hover": "#adb5bd",
        "bg_selected": "#0d6efd",
        "bg_splitter": "#dee2e6",
        "bg_splitter_hover": "#0d6efd",
        "border": "#dee2e6",
        "border_input": "#ced4da",
        "border_button": "#ced4da",
        "border_menu": "#dee2e6",
        "text_primary": "#212529",
        "text_secondary": "#6c757d",
        "text_tertiary": "#adb5bd",
        "text_input": "#212529",
        "text_selected": "#ffffff",
        "accent": "#0d6efd",
        "accent_hover": "#0b5ed7",
        "accent_border": "#0d6efd",
        "accent_active": "#0a58ca",
        "danger_bg": "#dc3545",
        "danger_border": "#b02a37",
        "danger_hover": "#bb2d3b",
        "danger_text": "#ffffff",
        "selection_bg": "#0d6efd",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },

    # ── 4. High Contrast Themes ─────────────────────────────────────────
    "high_contrast_dark": {
        "bg_main": "#000000",
        "bg_sidebar": "#000000",
        "bg_list": "#000000",
        "bg_input": "#000000",
        "bg_input_focus": "#111111",
        "bg_preview": "#000000",
        "bg_button": "#1a1a1a",
        "bg_button_hover": "#ffff00",
        "bg_button_pressed": "#333333",
        "bg_menubar": "#000000",
        "bg_menu": "#000000",
        "bg_tab": "#000000",
        "bg_tab_selected": "#222222",
        "bg_scroll_handle": "#ffffff",
        "bg_scroll_handle_hover": "#ffff00",
        "bg_selected": "#ffff00",
        "bg_splitter": "#ffffff",
        "bg_splitter_hover": "#ffff00",
        "border": "#ffffff",
        "border_input": "#ffffff",
        "border_button": "#ffffff",
        "border_menu": "#ffffff",
        "text_primary": "#ffffff",
        "text_secondary": "#ffff00",
        "text_tertiary": "#00ffff",
        "text_input": "#ffffff",
        "text_selected": "#000000",
        "accent": "#ffff00",
        "accent_hover": "#ffffff",
        "accent_border": "#ffffff",
        "accent_active": "#00ffff",
        "danger_bg": "#ff0000",
        "danger_border": "#ffffff",
        "danger_hover": "#ff4444",
        "danger_text": "#ffffff",
        "selection_bg": "#ffff00",
        "selection_text": "#000000",
        "font_category": "sans",
    },
    "high_contrast_light": {
        "bg_main": "#ffffff",
        "bg_sidebar": "#ffffff",
        "bg_list": "#ffffff",
        "bg_input": "#ffffff",
        "bg_input_focus": "#f0f0f0",
        "bg_preview": "#ffffff",
        "bg_button": "#f0f0f0",
        "bg_button_hover": "#000000",
        "bg_button_pressed": "#d0d0d0",
        "bg_menubar": "#ffffff",
        "bg_menu": "#ffffff",
        "bg_tab": "#ffffff",
        "bg_tab_selected": "#e0e0e0",
        "bg_scroll_handle": "#000000",
        "bg_scroll_handle_hover": "#0000ee",
        "bg_selected": "#0000ee",
        "bg_splitter": "#000000",
        "bg_splitter_hover": "#0000ee",
        "border": "#000000",
        "border_input": "#000000",
        "border_button": "#000000",
        "border_menu": "#000000",
        "text_primary": "#000000",
        "text_secondary": "#0000ee",
        "text_tertiary": "#333333",
        "text_input": "#000000",
        "text_selected": "#ffffff",
        "accent": "#0000ee",
        "accent_hover": "#0000aa",
        "accent_border": "#000000",
        "accent_active": "#000088",
        "danger_bg": "#cc0000",
        "danger_border": "#000000",
        "danger_hover": "#990000",
        "danger_text": "#ffffff",
        "selection_bg": "#0000ee",
        "selection_text": "#ffffff",
        "font_category": "sans",
    },
    "amber_oled": {
        "bg_main": "#000000",
        "bg_sidebar": "#050505",
        "bg_list": "#000000",
        "bg_input": "#080808",
        "bg_input_focus": "#121212",
        "bg_preview": "#020202",
        "bg_button": "#18140a",
        "bg_button_hover": "#2e2410",
        "bg_button_pressed": "#0c0a05",
        "bg_menubar": "#050505",
        "bg_menu": "#0c0a05",
        "bg_tab": "#0c0a05",
        "bg_tab_selected": "#000000",
        "bg_scroll_handle": "#ff9900",
        "bg_scroll_handle_hover": "#ffbb33",
        "bg_selected": "#ff9900",
        "bg_splitter": "#ff9900",
        "bg_splitter_hover": "#ffbb33",
        "border": "#3d2b05",
        "border_input": "#ff9900",
        "border_button": "#804d00",
        "border_menu": "#ff9900",
        "text_primary": "#ff9900",
        "text_secondary": "#ffbb33",
        "text_tertiary": "#804d00",
        "text_input": "#ffaa22",
        "text_selected": "#000000",
        "accent": "#ff9900",
        "accent_hover": "#ffbb33",
        "accent_border": "#ff9900",
        "accent_active": "#ffe066",
        "danger_bg": "#cc2200",
        "danger_border": "#ff4422",
        "danger_hover": "#ff5533",
        "danger_text": "#ffffff",
        "selection_bg": "#ff9900",
        "selection_text": "#000000",
        "font_category": "terminal",
    },

    # ── 5. Retro Themes ────────────────────────────────────────────────
    "macintosh_system7": {
        "bg_main": "#e0e0e0",
        "bg_sidebar": "#cccccc",
        "bg_list": "#e0e0e0",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#ffffff",
        "bg_button": "#d0d0d0",
        "bg_button_hover": "#b8b8b8",
        "bg_button_pressed": "#a0a0a0",
        "bg_menubar": "#cccccc",
        "bg_menu": "#ffffff",
        "bg_tab": "#d0d0d0",
        "bg_tab_selected": "#e0e0e0",
        "bg_scroll_handle": "#888888",
        "bg_scroll_handle_hover": "#000000",
        "bg_selected": "#000000",
        "bg_splitter": "#888888",
        "bg_splitter_hover": "#000000",
        "border": "#808080",
        "border_input": "#000000",
        "border_button": "#000000",
        "border_menu": "#000000",
        "text_primary": "#000000",
        "text_secondary": "#444444",
        "text_tertiary": "#777777",
        "text_input": "#000000",
        "text_selected": "#ffffff",
        "accent": "#000000",
        "accent_hover": "#333333",
        "accent_border": "#000000",
        "accent_active": "#555555",
        "danger_bg": "#a00000",
        "danger_border": "#000000",
        "danger_hover": "#c00000",
        "danger_text": "#ffffff",
        "selection_bg": "#000000",
        "selection_text": "#ffffff",
        "font_category": "retro_pixel",
    },
    "win95_classic": {
        "bg_main": "#008080",
        "bg_sidebar": "#c0c0c0",
        "bg_list": "#ffffff",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#ffffff",
        "bg_button": "#c0c0c0",
        "bg_button_hover": "#d4d0c8",
        "bg_button_pressed": "#808080",
        "bg_menubar": "#c0c0c0",
        "bg_menu": "#c0c0c0",
        "bg_tab": "#c0c0c0",
        "bg_tab_selected": "#d4d0c8",
        "bg_scroll_handle": "#c0c0c0",
        "bg_scroll_handle_hover": "#808080",
        "bg_selected": "#000080",
        "bg_splitter": "#808080",
        "bg_splitter_hover": "#000080",
        "border": "#808080",
        "border_input": "#808080",
        "border_button": "#404040",
        "border_menu": "#808080",
        "text_primary": "#000000",
        "text_secondary": "#000080",
        "text_tertiary": "#808080",
        "text_input": "#000000",
        "text_selected": "#ffffff",
        "accent": "#000080",
        "accent_hover": "#1084d0",
        "accent_border": "#000080",
        "accent_active": "#000050",
        "danger_bg": "#800000",
        "danger_border": "#400000",
        "danger_hover": "#a00000",
        "danger_text": "#ffffff",
        "selection_bg": "#000080",
        "selection_text": "#ffffff",
        "font_category": "retro_pixel",
    },
    "commodore_64": {
        "bg_main": "#40318d",
        "bg_sidebar": "#332470",
        "bg_list": "#40318d",
        "bg_input": "#7b71d4",
        "bg_input_focus": "#8a80e8",
        "bg_preview": "#332470",
        "bg_button": "#685cb5",
        "bg_button_hover": "#7b71d4",
        "bg_button_pressed": "#332470",
        "bg_menubar": "#332470",
        "bg_menu": "#40318d",
        "bg_tab": "#685cb5",
        "bg_tab_selected": "#40318d",
        "bg_scroll_handle": "#7b71d4",
        "bg_scroll_handle_hover": "#a8a0f8",
        "bg_selected": "#7b71d4",
        "bg_splitter": "#7b71d4",
        "bg_splitter_hover": "#a8a0f8",
        "border": "#685cb5",
        "border_input": "#a8a0f8",
        "border_button": "#7b71d4",
        "border_menu": "#7b71d4",
        "text_primary": "#a8a0f8",
        "text_secondary": "#c8c0ff",
        "text_tertiary": "#685cb5",
        "text_input": "#ffffff",
        "text_selected": "#332470",
        "accent": "#7b71d4",
        "accent_hover": "#a8a0f8",
        "accent_border": "#a8a0f8",
        "accent_active": "#c8c0ff",
        "danger_bg": "#8b3f3f",
        "danger_border": "#ab4f4f",
        "danger_hover": "#cb5f5f",
        "danger_text": "#ffffff",
        "selection_bg": "#7b71d4",
        "selection_text": "#332470",
        "font_category": "retro_pixel",
    },

    # ── 6. Psychological Horror Themes ─────────────────────────────────
    "silent_hill_fog": {
        "bg_main": "#1a1816",
        "bg_sidebar": "#121110",
        "bg_list": "#1a1816",
        "bg_input": "#24201c",
        "bg_input_focus": "#2f2a24",
        "bg_preview": "#0f0e0d",
        "bg_button": "#2f2a24",
        "bg_button_hover": "#473e35",
        "bg_button_pressed": "#1a1816",
        "bg_menubar": "#121110",
        "bg_menu": "#24201c",
        "bg_tab": "#24201c",
        "bg_tab_selected": "#1a1816",
        "bg_scroll_handle": "#615446",
        "bg_scroll_handle_hover": "#802b28",
        "bg_selected": "#802b28",
        "bg_splitter": "#473e35",
        "bg_splitter_hover": "#802b28",
        "border": "#3b342c",
        "border_input": "#54493e",
        "border_button": "#54493e",
        "border_menu": "#3b342c",
        "text_primary": "#c9bdae",
        "text_secondary": "#8f8272",
        "text_tertiary": "#595045",
        "text_input": "#ded4c5",
        "text_selected": "#f0e6d8",
        "accent": "#802b28",
        "accent_hover": "#9c3532",
        "accent_border": "#a83e3a",
        "accent_active": "#5e1d1b",
        "danger_bg": "#591210",
        "danger_border": "#802b28",
        "danger_hover": "#9c3532",
        "danger_text": "#f0e6d8",
        "selection_bg": "#802b28",
        "selection_text": "#f0e6d8",
        "font_category": "serif_horror",
    },
    "blood_moon_eldritch": {
        "bg_main": "#0d0406",
        "bg_sidebar": "#080204",
        "bg_list": "#0d0406",
        "bg_input": "#1a080d",
        "bg_input_focus": "#290c14",
        "bg_preview": "#050102",
        "bg_button": "#290c14",
        "bg_button_hover": "#4a1221",
        "bg_button_pressed": "#1a080d",
        "bg_menubar": "#080204",
        "bg_menu": "#1a080d",
        "bg_tab": "#1a080d",
        "bg_tab_selected": "#0d0406",
        "bg_scroll_handle": "#991b1b",
        "bg_scroll_handle_hover": "#dc2626",
        "bg_selected": "#991b1b",
        "bg_splitter": "#991b1b",
        "bg_splitter_hover": "#ef4444",
        "border": "#3b0f1a",
        "border_input": "#7f1d1d",
        "border_button": "#5c1322",
        "border_menu": "#7f1d1d",
        "text_primary": "#fee2e2",
        "text_secondary": "#fca5a5",
        "text_tertiary": "#7f1d1d",
        "text_input": "#fef2f2",
        "text_selected": "#ffffff",
        "accent": "#dc2626",
        "accent_hover": "#ef4444",
        "accent_border": "#f87171",
        "accent_active": "#b91c1c",
        "danger_bg": "#7f1d1d",
        "danger_border": "#991b1b",
        "danger_hover": "#b91c1c",
        "danger_text": "#ffffff",
        "selection_bg": "#991b1b",
        "selection_text": "#ffffff",
        "font_category": "serif_horror",
    },
    "liminal_asylum": {
        "bg_main": "#151c19",
        "bg_sidebar": "#0e1411",
        "bg_list": "#151c19",
        "bg_input": "#1f2925",
        "bg_input_focus": "#2a3832",
        "bg_preview": "#0a0f0d",
        "bg_button": "#2a3832",
        "bg_button_hover": "#3c4f47",
        "bg_button_pressed": "#1f2925",
        "bg_menubar": "#0e1411",
        "bg_menu": "#1f2925",
        "bg_tab": "#1f2925",
        "bg_tab_selected": "#151c19",
        "bg_scroll_handle": "#2dd4bf",
        "bg_scroll_handle_hover": "#5eead4",
        "bg_selected": "#14b8a6",
        "bg_splitter": "#14b8a6",
        "bg_splitter_hover": "#2dd4bf",
        "border": "#283832",
        "border_input": "#14b8a6",
        "border_button": "#2a3832",
        "border_menu": "#14b8a6",
        "text_primary": "#ccfbf1",
        "text_secondary": "#5eead4",
        "text_tertiary": "#134e48",
        "text_input": "#f0fdfa",
        "text_selected": "#0e1411",
        "accent": "#14b8a6",
        "accent_hover": "#2dd4bf",
        "accent_border": "#5eead4",
        "accent_active": "#0f766e",
        "danger_bg": "#991b1b",
        "danger_border": "#dc2626",
        "danger_hover": "#ef4444",
        "danger_text": "#ffffff",
        "selection_bg": "#14b8a6",
        "selection_text": "#0e1411",
        "font_category": "mono",
    },

    # ── 7. Terminal & CRT Themes ───────────────────────────────────────
    "vt100_amber": {
        "bg_main": "#100c05",
        "bg_sidebar": "#0a0702",
        "bg_list": "#100c05",
        "bg_input": "#1a1308",
        "bg_input_focus": "#261c0c",
        "bg_preview": "#080602",
        "bg_button": "#261c0c",
        "bg_button_hover": "#ffb000",
        "bg_button_pressed": "#1a1308",
        "bg_menubar": "#0a0702",
        "bg_menu": "#1a1308",
        "bg_tab": "#1a1308",
        "bg_tab_selected": "#100c05",
        "bg_scroll_handle": "#ffb000",
        "bg_scroll_handle_hover": "#ffd066",
        "bg_selected": "#ffb000",
        "bg_splitter": "#ffb000",
        "bg_splitter_hover": "#ffd066",
        "border": "#473413",
        "border_input": "#ffb000",
        "border_button": "#805914",
        "border_menu": "#ffb000",
        "text_primary": "#ffb000",
        "text_secondary": "#ffd066",
        "text_tertiary": "#805914",
        "text_input": "#ffb000",
        "text_selected": "#0a0702",
        "accent": "#ffb000",
        "accent_hover": "#ffd066",
        "accent_border": "#ffb000",
        "accent_active": "#ffffff",
        "danger_bg": "#992200",
        "danger_border": "#ffb000",
        "danger_hover": "#cc3300",
        "danger_text": "#ffffff",
        "selection_bg": "#ffb000",
        "selection_text": "#0a0702",
        "font_category": "terminal",
    },
    "monokai_pro": {
        "bg_main": "#2d2a2e",
        "bg_sidebar": "#221f22",
        "bg_list": "#2d2a2e",
        "bg_input": "#3a363b",
        "bg_input_focus": "#49444b",
        "bg_preview": "#1e1b1e",
        "bg_button": "#49444b",
        "bg_button_hover": "#ffd866",
        "bg_button_pressed": "#3a363b",
        "bg_menubar": "#221f22",
        "bg_menu": "#3a363b",
        "bg_tab": "#3a363b",
        "bg_tab_selected": "#2d2a2e",
        "bg_scroll_handle": "#727072",
        "bg_scroll_handle_hover": "#ffd866",
        "bg_selected": "#a9dc76",
        "bg_splitter": "#ffd866",
        "bg_splitter_hover": "#a9dc76",
        "border": "#49444b",
        "border_input": "#727072",
        "border_button": "#727072",
        "border_menu": "#ffd866",
        "text_primary": "#fcfcfa",
        "text_secondary": "#78dce8",
        "text_tertiary": "#727072",
        "text_input": "#fcfcfa",
        "text_selected": "#2d2a2e",
        "accent": "#ffd866",
        "accent_hover": "#ff6188",
        "accent_border": "#ffd866",
        "accent_active": "#a9dc76",
        "danger_bg": "#ff6188",
        "danger_border": "#e0446b",
        "danger_hover": "#ff789c",
        "danger_text": "#2d2a2e",
        "selection_bg": "#a9dc76",
        "selection_text": "#2d2a2e",
        "font_category": "mono",
    },
    "ubuntu_terminal": {
        "bg_main": "#300a24",
        "bg_sidebar": "#200618",
        "bg_list": "#300a24",
        "bg_input": "#430e32",
        "bg_input_focus": "#561241",
        "bg_preview": "#180412",
        "bg_button": "#561241",
        "bg_button_hover": "#e95420",
        "bg_button_pressed": "#430e32",
        "bg_menubar": "#200618",
        "bg_menu": "#430e32",
        "bg_tab": "#430e32",
        "bg_tab_selected": "#300a24",
        "bg_scroll_handle": "#77216f",
        "bg_scroll_handle_hover": "#e95420",
        "bg_selected": "#e95420",
        "bg_splitter": "#e95420",
        "bg_splitter_hover": "#eea082",
        "border": "#5c1d4e",
        "border_input": "#77216f",
        "border_button": "#77216f",
        "border_menu": "#e95420",
        "text_primary": "#ffffff",
        "text_secondary": "#eea082",
        "text_tertiary": "#8c4f7d",
        "text_input": "#ffffff",
        "text_selected": "#ffffff",
        "accent": "#e95420",
        "accent_hover": "#ff6e3a",
        "accent_border": "#e95420",
        "accent_active": "#ffffff",
        "danger_bg": "#c7162b",
        "danger_border": "#e95420",
        "danger_hover": "#e02035",
        "danger_text": "#ffffff",
        "selection_bg": "#e95420",
        "selection_text": "#ffffff",
        "font_category": "terminal",
    },

    # ── 8. Minimalist Themes ───────────────────────────────────────────
    "pure_monolith": {
        "bg_main": "#000000",
        "bg_sidebar": "#080808",
        "bg_list": "#000000",
        "bg_input": "#0f0f0f",
        "bg_input_focus": "#171717",
        "bg_preview": "#050505",
        "bg_button": "#1c1c1c",
        "bg_button_hover": "#2e2e2e",
        "bg_button_pressed": "#141414",
        "bg_menubar": "#080808",
        "bg_menu": "#121212",
        "bg_tab": "#121212",
        "bg_tab_selected": "#000000",
        "bg_scroll_handle": "#404040",
        "bg_scroll_handle_hover": "#737373",
        "bg_selected": "#262626",
        "bg_splitter": "#262626",
        "bg_splitter_hover": "#525252",
        "border": "#1f1f1f",
        "border_input": "#2e2e2e",
        "border_button": "#2e2e2e",
        "border_menu": "#262626",
        "text_primary": "#f5f5f5",
        "text_secondary": "#a3a3a3",
        "text_tertiary": "#525252",
        "text_input": "#ffffff",
        "text_selected": "#ffffff",
        "accent": "#ffffff",
        "accent_hover": "#d4d4d4",
        "accent_border": "#ffffff",
        "accent_active": "#a3a3a3",
        "danger_bg": "#ef4444",
        "danger_border": "#dc2626",
        "danger_hover": "#dc2626",
        "danger_text": "#ffffff",
        "selection_bg": "#262626",
        "selection_text": "#ffffff",
        "font_category": "designer_swiss",
    },
    "ghost_paper": {
        "bg_main": "#fafafa",
        "bg_sidebar": "#f5f5f5",
        "bg_list": "#fafafa",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#f7f7f7",
        "bg_button": "#eeeeee",
        "bg_button_hover": "#e0e0e0",
        "bg_button_pressed": "#d6d6d6",
        "bg_menubar": "#f5f5f5",
        "bg_menu": "#ffffff",
        "bg_tab": "#eeeeee",
        "bg_tab_selected": "#fafafa",
        "bg_scroll_handle": "#d4d4d4",
        "bg_scroll_handle_hover": "#a3a3a3",
        "bg_selected": "#0a0a0a",
        "bg_splitter": "#e5e5e5",
        "bg_splitter_hover": "#0a0a0a",
        "border": "#e5e5e5",
        "border_input": "#d4d4d4",
        "border_button": "#d4d4d4",
        "border_menu": "#e5e5e5",
        "text_primary": "#171717",
        "text_secondary": "#525252",
        "text_tertiary": "#a3a3a3",
        "text_input": "#0a0a0a",
        "text_selected": "#ffffff",
        "accent": "#171717",
        "accent_hover": "#404040",
        "accent_border": "#171717",
        "accent_active": "#737373",
        "danger_bg": "#e11d48",
        "danger_border": "#be123c",
        "danger_hover": "#be123c",
        "danger_text": "#ffffff",
        "selection_bg": "#171717",
        "selection_text": "#ffffff",
        "font_category": "designer_swiss",
    },
    "tokyo_minimal": {
        "bg_main": "#1e2029",
        "bg_sidebar": "#181a22",
        "bg_list": "#1e2029",
        "bg_input": "#252834",
        "bg_input_focus": "#2d313f",
        "bg_preview": "#14151c",
        "bg_button": "#2d313f",
        "bg_button_hover": "#f38ba8",
        "bg_button_pressed": "#252834",
        "bg_menubar": "#181a22",
        "bg_menu": "#252834",
        "bg_tab": "#252834",
        "bg_tab_selected": "#1e2029",
        "bg_scroll_handle": "#4e546a",
        "bg_scroll_handle_hover": "#f38ba8",
        "bg_selected": "#f38ba8",
        "bg_splitter": "#2d313f",
        "bg_splitter_hover": "#f38ba8",
        "border": "#2d313f",
        "border_input": "#3e4357",
        "border_button": "#3e4357",
        "border_menu": "#f38ba8",
        "text_primary": "#e2e4ec",
        "text_secondary": "#f38ba8",
        "text_tertiary": "#6e7592",
        "text_input": "#ffffff",
        "text_selected": "#181a22",
        "accent": "#f38ba8",
        "accent_hover": "#fab387",
        "accent_border": "#f38ba8",
        "accent_active": "#cba6f7",
        "danger_bg": "#e64553",
        "danger_border": "#f38ba8",
        "danger_hover": "#d20f39",
        "danger_text": "#ffffff",
        "selection_bg": "#f38ba8",
        "selection_text": "#181a22",
        "font_category": "sans",
    },

    # ── 9. Cartoonish & Playful Themes ─────────────────────────────────
    "bubblegum_pop": {
        "bg_main": "#fff1f5",
        "bg_sidebar": "#ffe4ec",
        "bg_list": "#fff1f5",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#ffeef3",
        "bg_button": "#ffd1dc",
        "bg_button_hover": "#ff85a2",
        "bg_button_pressed": "#fca5b9",
        "bg_menubar": "#ffe4ec",
        "bg_menu": "#ffffff",
        "bg_tab": "#ffd1dc",
        "bg_tab_selected": "#fff1f5",
        "bg_scroll_handle": "#ff85a2",
        "bg_scroll_handle_hover": "#ff477e",
        "bg_selected": "#ff477e",
        "bg_splitter": "#ff85a2",
        "bg_splitter_hover": "#ff477e",
        "border": "#fbb1c2",
        "border_input": "#ff85a2",
        "border_button": "#fbb1c2",
        "border_menu": "#ff85a2",
        "text_primary": "#4a154b",
        "text_secondary": "#9c27b0",
        "text_tertiary": "#f06292",
        "text_input": "#4a154b",
        "text_selected": "#ffffff",
        "accent": "#ff477e",
        "accent_hover": "#ff5c8a",
        "accent_border": "#ff0a54",
        "accent_active": "#ff7096",
        "danger_bg": "#e63946",
        "danger_border": "#d90429",
        "danger_hover": "#ef233c",
        "danger_text": "#ffffff",
        "selection_bg": "#ff477e",
        "selection_text": "#ffffff",
        "font_category": "cartoon",
    },
    "comic_book_ink": {
        "bg_main": "#fffbe6",
        "bg_sidebar": "#ffeb99",
        "bg_list": "#fffbe6",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#fff7cc",
        "bg_button": "#ffdf66",
        "bg_button_hover": "#ff3333",
        "bg_button_pressed": "#e6c340",
        "bg_menubar": "#ffeb99",
        "bg_menu": "#ffffff",
        "bg_tab": "#ffdf66",
        "bg_tab_selected": "#fffbe6",
        "bg_scroll_handle": "#000000",
        "bg_scroll_handle_hover": "#ff3333",
        "bg_selected": "#ff3333",
        "bg_splitter": "#000000",
        "bg_splitter_hover": "#ff3333",
        "border": "#000000",
        "border_input": "#000000",
        "border_button": "#000000",
        "border_menu": "#000000",
        "text_primary": "#000000",
        "text_secondary": "#0033cc",
        "text_tertiary": "#666666",
        "text_input": "#000000",
        "text_selected": "#ffffff",
        "accent": "#ff3333",
        "accent_hover": "#0033cc",
        "accent_border": "#000000",
        "accent_active": "#00cc66",
        "danger_bg": "#cc0000",
        "danger_border": "#000000",
        "danger_hover": "#ee0000",
        "danger_text": "#ffffff",
        "selection_bg": "#ff3333",
        "selection_text": "#ffffff",
        "font_category": "cartoon",
    },

    # ── 10. Blackened Themes (Atmospheric Black Metal) ──────────────────
    "burzum_forest": {
        "bg_main": "#0a0d0a",
        "bg_sidebar": "#060906",
        "bg_list": "#0a0d0a",
        "bg_input": "#111711",
        "bg_input_focus": "#182218",
        "bg_preview": "#040704",
        "bg_button": "#182218",
        "bg_button_hover": "#263626",
        "bg_button_pressed": "#111711",
        "bg_menubar": "#060906",
        "bg_menu": "#111711",
        "bg_tab": "#111711",
        "bg_tab_selected": "#0a0d0a",
        "bg_scroll_handle": "#445944",
        "bg_scroll_handle_hover": "#6c8c6c",
        "bg_selected": "#3f563f",
        "bg_splitter": "#233023",
        "bg_splitter_hover": "#4f6b4f",
        "border": "#1b261b",
        "border_input": "#2d3d2d",
        "border_button": "#2d3d2d",
        "border_menu": "#3f563f",
        "text_primary": "#c5cdc5",
        "text_secondary": "#819481",
        "text_tertiary": "#445444",
        "text_input": "#e0e6e0",
        "text_selected": "#ffffff",
        "accent": "#4f6b4f",
        "accent_hover": "#6c8c6c",
        "accent_border": "#7ea67e",
        "accent_active": "#9dc29d",
        "danger_bg": "#591c1c",
        "danger_border": "#7a2727",
        "danger_hover": "#9c3232",
        "danger_text": "#ffffff",
        "selection_bg": "#3f563f",
        "selection_text": "#ffffff",
        "font_category": "black_metal",
    },
    "darkthrone_frost": {
        "bg_main": "#06080c",
        "bg_sidebar": "#030406",
        "bg_list": "#06080c",
        "bg_input": "#0d111a",
        "bg_input_focus": "#141a26",
        "bg_preview": "#020305",
        "bg_button": "#141a26",
        "bg_button_hover": "#222c40",
        "bg_button_pressed": "#0d111a",
        "bg_menubar": "#030406",
        "bg_menu": "#0d111a",
        "bg_tab": "#0d111a",
        "bg_tab_selected": "#06080c",
        "bg_scroll_handle": "#384a6b",
        "bg_scroll_handle_hover": "#6582ba",
        "bg_selected": "#3e5275",
        "bg_splitter": "#1f2738",
        "bg_splitter_hover": "#6582ba",
        "border": "#1b2230",
        "border_input": "#2a344a",
        "border_button": "#2a344a",
        "border_menu": "#384a6b",
        "text_primary": "#dce3f0",
        "text_secondary": "#8fa2c4",
        "text_tertiary": "#4a5975",
        "text_input": "#f0f4fc",
        "text_selected": "#ffffff",
        "accent": "#6582ba",
        "accent_hover": "#8fa8de",
        "accent_border": "#8fa8de",
        "accent_active": "#b8caff",
        "danger_bg": "#661822",
        "danger_border": "#8c202e",
        "danger_hover": "#b3293b",
        "danger_text": "#ffffff",
        "selection_bg": "#3e5275",
        "selection_text": "#ffffff",
        "font_category": "black_metal",
    },
    "behemoth_obsidian": {
        "bg_main": "#0a0705",
        "bg_sidebar": "#050302",
        "bg_list": "#0a0705",
        "bg_input": "#140e0b",
        "bg_input_focus": "#211712",
        "bg_preview": "#030201",
        "bg_button": "#211712",
        "bg_button_hover": "#36261e",
        "bg_button_pressed": "#140e0b",
        "bg_menubar": "#050302",
        "bg_menu": "#140e0b",
        "bg_tab": "#140e0b",
        "bg_tab_selected": "#0a0705",
        "bg_scroll_handle": "#d4af37",
        "bg_scroll_handle_hover": "#f5cf47",
        "bg_selected": "#801818",
        "bg_splitter": "#8c2a1c",
        "bg_splitter_hover": "#d4af37",
        "border": "#2e1c14",
        "border_input": "#d4af37",
        "border_button": "#472c20",
        "border_menu": "#d4af37",
        "text_primary": "#e6d5c3",
        "text_secondary": "#d4af37",
        "text_tertiary": "#704838",
        "text_input": "#f5ebe1",
        "text_selected": "#ffffff",
        "accent": "#d4af37",
        "accent_hover": "#801818",
        "accent_border": "#d4af37",
        "accent_active": "#f5cf47",
        "danger_bg": "#7a1212",
        "danger_border": "#a81919",
        "danger_hover": "#d12121",
        "danger_text": "#ffffff",
        "selection_bg": "#801818",
        "selection_text": "#ffffff",
        "font_category": "black_metal",
    },

    # ── 11. Unique Designer Themes ─────────────────────────────────────
    "bauhaus_geometric": {
        "bg_main": "#f4f1ea",
        "bg_sidebar": "#e8e3d5",
        "bg_list": "#f4f1ea",
        "bg_input": "#ffffff",
        "bg_input_focus": "#ffffff",
        "bg_preview": "#eae5d8",
        "bg_button": "#ded7c4",
        "bg_button_hover": "#de3831",
        "bg_button_pressed": "#1e448b",
        "bg_menubar": "#e8e3d5",
        "bg_menu": "#ffffff",
        "bg_tab": "#ded7c4",
        "bg_tab_selected": "#f4f1ea",
        "bg_scroll_handle": "#1e448b",
        "bg_scroll_handle_hover": "#de3831",
        "bg_selected": "#1e448b",
        "bg_splitter": "#de3831",
        "bg_splitter_hover": "#f2a900",
        "border": "#1a1a1a",
        "border_input": "#1a1a1a",
        "border_button": "#1a1a1a",
        "border_menu": "#1a1a1a",
        "text_primary": "#1a1a1a",
        "text_secondary": "#1e448b",
        "text_tertiary": "#de3831",
        "text_input": "#1a1a1a",
        "text_selected": "#ffffff",
        "accent": "#de3831",
        "accent_hover": "#1e448b",
        "accent_border": "#1a1a1a",
        "accent_active": "#f2a900",
        "danger_bg": "#de3831",
        "danger_border": "#1a1a1a",
        "danger_hover": "#b82620",
        "danger_text": "#ffffff",
        "selection_bg": "#1e448b",
        "selection_text": "#ffffff",
        "font_category": "designer_swiss",
    },
    "swiss_typography": {
        "bg_main": "#ffffff",
        "bg_sidebar": "#f2f2f2",
        "bg_list": "#ffffff",
        "bg_input": "#ffffff",
        "bg_input_focus": "#f9f9f9",
        "bg_preview": "#f7f7f7",
        "bg_button": "#e6e6e6",
        "bg_button_hover": "#ff3b30",
        "bg_button_pressed": "#cccccc",
        "bg_menubar": "#f2f2f2",
        "bg_menu": "#ffffff",
        "bg_tab": "#e6e6e6",
        "bg_tab_selected": "#ffffff",
        "bg_scroll_handle": "#000000",
        "bg_scroll_handle_hover": "#ff3b30",
        "bg_selected": "#ff3b30",
        "bg_splitter": "#000000",
        "bg_splitter_hover": "#ff3b30",
        "border": "#000000",
        "border_input": "#000000",
        "border_button": "#000000",
        "border_menu": "#000000",
        "text_primary": "#000000",
        "text_secondary": "#ff3b30",
        "text_tertiary": "#666666",
        "text_input": "#000000",
        "text_selected": "#ffffff",
        "accent": "#ff3b30",
        "accent_hover": "#d70015",
        "accent_border": "#000000",
        "accent_active": "#000000",
        "danger_bg": "#ff3b30",
        "danger_border": "#000000",
        "danger_hover": "#d70015",
        "danger_text": "#ffffff",
        "selection_bg": "#ff3b30",
        "selection_text": "#ffffff",
        "font_category": "designer_swiss",
    },
    "art_deco_gold": {
        "bg_main": "#0f0f12",
        "bg_sidebar": "#09090b",
        "bg_list": "#0f0f12",
        "bg_input": "#18181c",
        "bg_input_focus": "#222228",
        "bg_preview": "#050507",
        "bg_button": "#222228",
        "bg_button_hover": "#d4af37",
        "bg_button_pressed": "#18181c",
        "bg_menubar": "#09090b",
        "bg_menu": "#18181c",
        "bg_tab": "#18181c",
        "bg_tab_selected": "#0f0f12",
        "bg_scroll_handle": "#d4af37",
        "bg_scroll_handle_hover": "#f3e5ab",
        "bg_selected": "#d4af37",
        "bg_splitter": "#d4af37",
        "bg_splitter_hover": "#f3e5ab",
        "border": "#2e2e38",
        "border_input": "#d4af37",
        "border_button": "#4a4a5a",
        "border_menu": "#d4af37",
        "text_primary": "#f5eedc",
        "text_secondary": "#d4af37",
        "text_tertiary": "#8c8266",
        "text_input": "#ffffff",
        "text_selected": "#0f0f12",
        "accent": "#d4af37",
        "accent_hover": "#f3e5ab",
        "accent_border": "#d4af37",
        "accent_active": "#aa8822",
        "danger_bg": "#8b1e2a",
        "danger_border": "#d4af37",
        "danger_hover": "#b82838",
        "danger_text": "#ffffff",
        "selection_bg": "#d4af37",
        "selection_text": "#0f0f12",
        "font_category": "serif_horror",
    },
}


# ── Metadata Catalog ────────────────────────────────────────────────────

_THEME_CATALOG: List[Theme] = [
    Theme("midnight_dark", "Midnight Dark", "dark", "Core", "Default dark theme — deep slate blue", _build_stylesheet(PALETTES["midnight_dark"])),
    Theme("midnight_light", "Midnight Light", "light", "Core", "Default light theme — crisp slate", _build_stylesheet(PALETTES["midnight_light"])),
    Theme("nord", "Nord", "dark", "Core", "Arctic, north-bluish palette", _build_stylesheet(PALETTES["nord"])),
    Theme("dracula", "Dracula", "dark", "Core", "Classic dark theme for vampires", _build_stylesheet(PALETTES["dracula"])),
    Theme("tokyo_night", "Tokyo Night", "dark", "Core", "Clean dark Tokyo neon night", _build_stylesheet(PALETTES["tokyo_night"])),
    # Glow & Neon
    Theme("cyberpunk_neon", "Cyberpunk Neon", "dark", "Glow & Neon", "Electric cyan & hot magenta neon glow", _build_stylesheet(PALETTES["cyberpunk_neon"])),
    Theme("synthwave_glow", "Synthwave 80s", "dark", "Glow & Neon", "Radical sunset violet & fluorescent pink glow", _build_stylesheet(PALETTES["synthwave_glow"])),
    Theme("matrix_glow", "Matrix Phosphor", "dark", "Glow & Neon", "Digital green phosphor code rain", _build_stylesheet(PALETTES["matrix_glow"])),
    # Bland / Professional
    Theme("corporate_slate", "Corporate Slate", "dark", "Professional", "Subdued executive slate gray", _build_stylesheet(PALETTES["corporate_slate"])),
    Theme("office_paper", "Office Paper", "light", "Professional", "Clean off-white linen with navy accents", _build_stylesheet(PALETTES["office_paper"])),
    Theme("enterprise_light", "Enterprise Light", "light", "Professional", "Crisp corporate white with steel blue", _build_stylesheet(PALETTES["enterprise_light"])),
    # High Contrast
    Theme("high_contrast_dark", "High Contrast Dark", "dark", "High Contrast", "Pure black with vivid yellow & white", _build_stylesheet(PALETTES["high_contrast_dark"])),
    Theme("high_contrast_light", "High Contrast Light", "light", "High Contrast", "Pure white with high-vis black & navy", _build_stylesheet(PALETTES["high_contrast_light"])),
    Theme("amber_oled", "Amber OLED", "dark", "High Contrast", "True pitch black OLED with vivid amber", _build_stylesheet(PALETTES["amber_oled"])),
    # Retro
    Theme("macintosh_system7", "Macintosh 1991", "light", "Retro", "Classic Apple System 7 platinum gray", _build_stylesheet(PALETTES["macintosh_system7"])),
    Theme("win95_classic", "Windows 95", "light", "Retro", "Classic 3D beveled silver with teal desktop", _build_stylesheet(PALETTES["win95_classic"])),
    Theme("commodore_64", "Commodore 64", "dark", "Retro", "Authentic 1982 C64 indigo-violet & cyan", _build_stylesheet(PALETTES["commodore_64"])),
    # Psychological Horror
    Theme("silent_hill_fog", "Silent Hill Fog", "dark", "Horror", "Rusty ash, decaying mist & dried blood", _build_stylesheet(PALETTES["silent_hill_fog"])),
    Theme("blood_moon_eldritch", "Blood Moon Eldritch", "dark", "Horror", "Crimson abyss & cosmic horror scarlet", _build_stylesheet(PALETTES["blood_moon_eldritch"])),
    Theme("liminal_asylum", "Liminal Asylum", "dark", "Horror", "Sterile fluorescent mint & dilapidated tile", _build_stylesheet(PALETTES["liminal_asylum"])),
    # Terminal
    Theme("vt100_amber", "VT100 Amber CRT", "dark", "Terminal", "Cathode-ray tube amber phosphor on raster", _build_stylesheet(PALETTES["vt100_amber"])),
    Theme("monokai_pro", "Monokai Pro", "dark", "Terminal", "Iconic charcoal developer dark with coral", _build_stylesheet(PALETTES["monokai_pro"])),
    Theme("ubuntu_terminal", "Ubuntu Terminal", "dark", "Terminal", "Deep canonical aubergine & terminal orange", _build_stylesheet(PALETTES["ubuntu_terminal"])),
    # Minimalist
    Theme("pure_monolith", "Pure Monolith", "dark", "Minimalist", "Zero-distraction obsidian black with silver", _build_stylesheet(PALETTES["pure_monolith"])),
    Theme("ghost_paper", "Ghost Paper", "light", "Minimalist", "Ultra-minimal cream with whisper line art", _build_stylesheet(PALETTES["ghost_paper"])),
    Theme("tokyo_minimal", "Tokyo Minimal", "dark", "Minimalist", "Zen ink slate with cherry blossom pink", _build_stylesheet(PALETTES["tokyo_minimal"])),
    # Cartoonish
    Theme("bubblegum_pop", "Bubblegum Pop", "light", "Cartoonish", "Playful candy pastel pink, baby blue & lilac", _build_stylesheet(PALETTES["bubblegum_pop"])),
    Theme("comic_book_ink", "Comic Book Ink", "light", "Cartoonish", "Pop-art yellow with heavy ink outlines", _build_stylesheet(PALETTES["comic_book_ink"])),
    # Blackened Atmospheric
    Theme("burzum_forest", "Burzum Pine Forest", "dark", "Blackened", "Misty Scandinavian pine & twilight gloom", _build_stylesheet(PALETTES["burzum_forest"])),
    Theme("darkthrone_frost", "Darkthrone Frost", "dark", "Blackened", "Freezing Norwegian blizzard white & ice blue", _build_stylesheet(PALETTES["darkthrone_frost"])),
    Theme("behemoth_obsidian", "Behemoth Obsidian", "dark", "Blackened", "Chthonic blackened sulfur gold & bloodfire", _build_stylesheet(PALETTES["behemoth_obsidian"])),
    # Designer
    Theme("bauhaus_geometric", "Bauhaus Geometric", "light", "Designer", "Primary red, cobalt blue, yellow & warm ivory", _build_stylesheet(PALETTES["bauhaus_geometric"])),
    Theme("swiss_typography", "Swiss Typography", "light", "Designer", "International Typographic Style & Helvetica red", _build_stylesheet(PALETTES["swiss_typography"])),
    Theme("art_deco_gold", "Art Deco Gold", "dark", "Designer", "Gatsby onyx black with metallic brass & gold", _build_stylesheet(PALETTES["art_deco_gold"])),
]

THEMES: Dict[str, Theme] = {t.id: t for t in _THEME_CATALOG}
THEME_IDS: List[str] = list(THEMES.keys())
DEFAULT_THEME = "midnight_dark"


# ── Syntax Highlighter Palettes ─────────────────────────────────────────

HIGHLIGHTER_PALETTES: Dict[str, Dict[str, str]] = {
    "midnight_dark": {
        "variable_fg": "#38bdf8",
        "variable_bg": "#1e293b",
        "heading": "#818cf8",
        "role": "#4ade80",
        "code": "#f472b6",
        "error": "#f87171",
    },
    "midnight_light": {
        "variable_fg": "#0284c7",
        "variable_bg": "#e2e8f0",
        "heading": "#4f46e5",
        "role": "#16a34a",
        "code": "#db2777",
        "error": "#dc2626",
    },
    "nord": {
        "variable_fg": "#88c0d0",
        "variable_bg": "#3b4252",
        "heading": "#81a1c1",
        "role": "#a3be8c",
        "code": "#b48ead",
        "error": "#bf616a",
    },
    "dracula": {
        "variable_fg": "#8be9fd",
        "variable_bg": "#44475a",
        "heading": "#bd93f9",
        "role": "#50fa7b",
        "code": "#ff79c6",
        "error": "#ff5555",
    },
    "tokyo_night": {
        "variable_fg": "#e0af68",
        "variable_bg": "#414868",
        "heading": "#7aa2f7",
        "role": "#9ece6a",
        "code": "#bb9af7",
        "error": "#f7768e",
    },
    "cyberpunk_neon": {
        "variable_fg": "#00f0ff",
        "variable_bg": "#1a1c36",
        "heading": "#ff007f",
        "role": "#ffe600",
        "code": "#00ff66",
        "error": "#ff0055",
    },
    "synthwave_glow": {
        "variable_fg": "#fed766",
        "variable_bg": "#352752",
        "heading": "#ff388b",
        "role": "#00f0ff",
        "code": "#ff99c8",
        "error": "#e63946",
    },
    "matrix_glow": {
        "variable_fg": "#00ff66",
        "variable_bg": "#0d2810",
        "heading": "#33ff88",
        "role": "#55ff99",
        "code": "#aaffcc",
        "error": "#ff3344",
    },
    "corporate_slate": {
        "variable_fg": "#2d98da",
        "variable_bg": "#2b313e",
        "heading": "#778ca3",
        "role": "#20bf6b",
        "code": "#a55eea",
        "error": "#eb3b5a",
    },
    "office_paper": {
        "variable_fg": "#2c3e50",
        "variable_bg": "#e0e0e0",
        "heading": "#2980b9",
        "role": "#27ae60",
        "code": "#8e44ad",
        "error": "#d63031",
    },
    "enterprise_light": {
        "variable_fg": "#0d6efd",
        "variable_bg": "#e9ecef",
        "heading": "#0a58ca",
        "role": "#198754",
        "code": "#6f42c1",
        "error": "#dc3545",
    },
    "high_contrast_dark": {
        "variable_fg": "#ffff00",
        "variable_bg": "#222222",
        "heading": "#00ffff",
        "role": "#00ff00",
        "code": "#ff00ff",
        "error": "#ff0000",
    },
    "high_contrast_light": {
        "variable_fg": "#0000ee",
        "variable_bg": "#e0e0e0",
        "heading": "#000000",
        "role": "#006600",
        "code": "#660066",
        "error": "#cc0000",
    },
    "amber_oled": {
        "variable_fg": "#ff9900",
        "variable_bg": "#18140a",
        "heading": "#ffbb33",
        "role": "#ffe066",
        "code": "#ffcc00",
        "error": "#ff4422",
    },
    "macintosh_system7": {
        "variable_fg": "#000000",
        "variable_bg": "#d0d0d0",
        "heading": "#333333",
        "role": "#000080",
        "code": "#404040",
        "error": "#a00000",
    },
    "win95_classic": {
        "variable_fg": "#000080",
        "variable_bg": "#d4d0c8",
        "heading": "#000000",
        "role": "#006400",
        "code": "#800080",
        "error": "#800000",
    },
    "commodore_64": {
        "variable_fg": "#a8a0f8",
        "variable_bg": "#685cb5",
        "heading": "#c8c0ff",
        "role": "#70a4b2",
        "code": "#b8c0e0",
        "error": "#cb5f5f",
    },
    "silent_hill_fog": {
        "variable_fg": "#a83e3a",
        "variable_bg": "#2f2a24",
        "heading": "#c9bdae",
        "role": "#8f8272",
        "code": "#802b28",
        "error": "#9c3532",
    },
    "blood_moon_eldritch": {
        "variable_fg": "#f87171",
        "variable_bg": "#290c14",
        "heading": "#fee2e2",
        "role": "#fca5a5",
        "code": "#dc2626",
        "error": "#ef4444",
    },
    "liminal_asylum": {
        "variable_fg": "#2dd4bf",
        "variable_bg": "#2a3832",
        "heading": "#5eead4",
        "role": "#14b8a6",
        "code": "#99f6e4",
        "error": "#f43f5e",
    },
    "vt100_amber": {
        "variable_fg": "#ffb000",
        "variable_bg": "#261c0c",
        "heading": "#ffd066",
        "role": "#ffe066",
        "code": "#ffcc33",
        "error": "#ff4422",
    },
    "monokai_pro": {
        "variable_fg": "#ffd866",
        "variable_bg": "#49444b",
        "heading": "#ff6188",
        "role": "#a9dc76",
        "code": "#78dce8",
        "error": "#fc9867",
    },
    "ubuntu_terminal": {
        "variable_fg": "#e95420",
        "variable_bg": "#561241",
        "heading": "#eea082",
        "role": "#4ae08a",
        "code": "#ffb380",
        "error": "#c7162b",
    },
    "pure_monolith": {
        "variable_fg": "#ffffff",
        "variable_bg": "#1c1c1c",
        "heading": "#d4d4d4",
        "role": "#a3a3a3",
        "code": "#e5e5e5",
        "error": "#ef4444",
    },
    "ghost_paper": {
        "variable_fg": "#171717",
        "variable_bg": "#eeeeee",
        "heading": "#404040",
        "role": "#059669",
        "code": "#4f46e5",
        "error": "#e11d48",
    },
    "tokyo_minimal": {
        "variable_fg": "#f38ba8",
        "variable_bg": "#2d313f",
        "heading": "#fab387",
        "role": "#a6e3a1",
        "code": "#cba6f7",
        "error": "#e64553",
    },
    "bubblegum_pop": {
        "variable_fg": "#ff477e",
        "variable_bg": "#ffd1dc",
        "heading": "#9c27b0",
        "role": "#00bcd4",
        "code": "#ff0a54",
        "error": "#e63946",
    },
    "comic_book_ink": {
        "variable_fg": "#0033cc",
        "variable_bg": "#ffdf66",
        "heading": "#ff3333",
        "role": "#008800",
        "code": "#990099",
        "error": "#cc0000",
    },
    "burzum_forest": {
        "variable_fg": "#7ea67e",
        "variable_bg": "#182218",
        "heading": "#a6bfa6",
        "role": "#6c8c6c",
        "code": "#9dc29d",
        "error": "#9c3232",
    },
    "darkthrone_frost": {
        "variable_fg": "#8fa8de",
        "variable_bg": "#141a26",
        "heading": "#dce3f0",
        "role": "#6582ba",
        "code": "#b8caff",
        "error": "#b3293b",
    },
    "behemoth_obsidian": {
        "variable_fg": "#d4af37",
        "variable_bg": "#211712",
        "heading": "#f5cf47",
        "role": "#801818",
        "code": "#e6d5c3",
        "error": "#a81919",
    },
    "bauhaus_geometric": {
        "variable_fg": "#de3831",
        "variable_bg": "#ded7c4",
        "heading": "#1e448b",
        "role": "#f2a900",
        "code": "#1a1a1a",
        "error": "#de3831",
    },
    "swiss_typography": {
        "variable_fg": "#ff3b30",
        "variable_bg": "#e6e6e6",
        "heading": "#000000",
        "role": "#ff3b30",
        "code": "#333333",
        "error": "#d70015",
    },
    "art_deco_gold": {
        "variable_fg": "#d4af37",
        "variable_bg": "#222228",
        "heading": "#f3e5ab",
        "role": "#aa8822",
        "code": "#ffffff",
        "error": "#b82838",
    },
}


def get_theme(theme_id: str) -> Theme:
    """Return Theme by id, falling back to default."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])


def get_stylesheet(theme_id: str) -> str:
    """Return QSS string for a theme id, falling back to default."""
    return get_theme(theme_id).stylesheet


def list_themes() -> List[Theme]:
    """Return all themes in definition order."""
    return list(THEMES.values())


def list_theme_categories() -> List[str]:
    """Return unique theme category names."""
    seen = set()
    categories = []
    for t in _THEME_CATALOG:
        if t.category not in seen:
            seen.add(t.category)
            categories.append(t.category)
    return categories


def get_highlighter_palette(theme_id: str) -> Dict[str, str]:
    """Return highlighter color dict for a theme."""
    return HIGHLIGHTER_PALETTES.get(theme_id, HIGHLIGHTER_PALETTES[DEFAULT_THEME])


def is_dark_theme(theme_id: str) -> bool:
    return get_theme(theme_id).is_dark


def is_light_theme(theme_id: str) -> bool:
    return get_theme(theme_id).is_light
