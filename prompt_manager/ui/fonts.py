"""Cross-platform OS-aware font cascades and typography management for themes."""

from __future__ import annotations

import platform
from typing import Dict, List

_OS = platform.system().lower()  # "linux", "darwin" (macOS), "windows"


# Primary and fallback font cascades tailored for each OS
FONT_STACKS: Dict[str, Dict[str, List[str]]] = {
    "sans": {
        "darwin": ["SF Pro Text", "SF Pro Display", "-apple-system", "Helvetica Neue", "Helvetica", "sans-serif"],
        "windows": ["Segoe UI", "Aptos", "Calibri", "Arial", "sans-serif"],
        "linux": ["Inter", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans", "FreeSans", "sans-serif"],
        "default": ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Noto Sans", "Ubuntu", "sans-serif"],
    },
    "mono": {
        "darwin": ["SF Mono", "Menlo", "Monaco", "Courier New", "monospace"],
        "windows": ["Cascadia Code", "Cascadia Mono", "Consolas", "Courier New", "monospace"],
        "linux": ["JetBrains Mono", "Fira Code", "Ubuntu Mono", "DejaVu Sans Mono", "monospace"],
        "default": ["ui-monospace", "Cascadia Code", "SF Mono", "Menlo", "Consolas", "monospace"],
    },
    "retro_pixel": {
        "darwin": ["Monaco", "Courier", "Apple Garamond", "monospace"],
        "windows": ["Fixedsys", "Lucida Console", "Courier New", "System", "monospace"],
        "linux": ["Terminus", "DejaVu Sans Mono", "Courier 10 Pitch", "monospace"],
        "default": ["VT323", "Courier New", "Lucida Console", "monospace"],
    },
    "serif_horror": {
        "darwin": ["Baskerville", "Hoefler Text", "Didot", "Times New Roman", "serif"],
        "windows": ["Georgia", "Palatino Linotype", "Book Antiqua", "Times New Roman", "serif"],
        "linux": ["Liberation Serif", "DejaVu Serif", "FreeSerif", "serif"],
        "default": ["Cinzel", "Crimson Pro", "Georgia", "Palatino", "serif"],
    },
    "cartoon": {
        "darwin": ["Chalkboard SE", "Chalkboard", "Comic Sans MS", "Arial Rounded MT Bold", "sans-serif"],
        "windows": ["Comic Sans MS", "Trebuchet MS", "Segoe UI Rounded", "Arial", "sans-serif"],
        "linux": ["Ubuntu", "Comfortaa", "URW Gothic", "DejaVu Sans", "sans-serif"],
        "default": ["Comic Sans MS", "Trebuchet MS", "Arial Rounded MT Bold", "sans-serif"],
    },
    "designer_swiss": {
        "darwin": ["Helvetica Neue", "Helvetica", "SF Pro Display", "Arial", "sans-serif"],
        "windows": ["Arial", "Segoe UI", "Trebuchet MS", "sans-serif"],
        "linux": ["Liberation Sans", "Inter", "DejaVu Sans", "FreeSans", "sans-serif"],
        "default": ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    },
    "terminal": {
        "darwin": ["SF Mono", "Menlo", "Courier New", "monospace"],
        "windows": ["Consolas", "Cascadia Code", "Lucida Console", "monospace"],
        "linux": ["Ubuntu Mono", "DejaVu Sans Mono", "Fira Code", "monospace"],
        "default": ["VT100", "Courier New", "monospace"],
    },
    "black_metal": {
        "darwin": ["Hoefler Text", "Times New Roman", "Courier", "serif"],
        "windows": ["Palatino Linotype", "Georgia", "Courier New", "serif"],
        "linux": ["FreeSerif", "DejaVu Serif", "Liberation Serif", "serif"],
        "default": ["Old English Text MT", "Gothic", "Georgia", "serif"],
    },
}


def get_font_stack(category: str = "sans") -> str:
    """Return formatted CSS font-family string for the requested category on current OS."""
    category = category.lower().strip()
    stacks = FONT_STACKS.get(category, FONT_STACKS["sans"])
    fonts = stacks.get(_OS, stacks.get("default", ["sans-serif"]))

    # Quote font names containing spaces
    formatted = [f'"{f}"' if " " in f and not f.startswith('"') else f for f in fonts]
    return ", ".join(formatted)


def get_ui_font_css(category: str = "sans", font_size: str = "13px") -> str:
    """Return complete font-family and font-size CSS rule."""
    stack = get_font_stack(category)
    return f"font-family: {stack}; font-size: {font_size};"
