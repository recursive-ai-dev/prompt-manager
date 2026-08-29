"""Syntax highlighter for prompt templates, mustache variables, and markdown structures."""

import re
from typing import Dict, Optional

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PromptSyntaxHighlighter(QSyntaxHighlighter):
    """Highlights {{variables}}, markdown headers, and code fences."""

    # Default palette (midnight_dark) — overridden via apply_palette()
    DEFAULT_PALETTE: Dict[str, str] = {
        "variable_fg": "#fbbf24",
        "variable_bg": "#2d2415",
        "heading": "#60a5fa",
        "role": "#34d399",
        "code": "#f472b6",
        "error": "#f87171",
    }

    def __init__(self, parent=None, palette: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.highlighting_rules = []
        self._current_palette: Dict[str, str] = palette or dict(self.DEFAULT_PALETTE)
        self._build_rules(self._current_palette)

    def _build_rules(self, palette: Dict[str, str]) -> None:
        """(Re)build highlighting rules from a palette."""
        self.highlighting_rules.clear()

        # 1. Mustache Variables: {{variable}}, {{var:default}}, {{var|multiline}}
        var_format = QTextCharFormat()
        var_format.setForeground(QColor(palette.get("variable_fg", "#fbbf24")))
        var_bg = palette.get("variable_bg", "")
        if var_bg:
            var_format.setBackground(QColor(var_bg))
        var_format.setFontWeight(QFont.Weight.Bold)
        var_pattern = QRegularExpression(
            r"\{\{\s*[a-zA-Z0-9_\-]+(?::[^}|]+)?(?:\|[^}]+)?\s*\}\}"
        )
        self.highlighting_rules.append((var_pattern, var_format))

        # 2. Markdown Headings: #, ##, ###
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor(palette.get("heading", "#60a5fa")))
        heading_format.setFontWeight(QFont.Weight.Bold)
        heading_pattern = QRegularExpression(r"^(#{1,6}\s.*)$")
        self.highlighting_rules.append((heading_pattern, heading_format))

        # 3. Role markers: [SYSTEM], [USER], [ASSISTANT]
        role_format = QTextCharFormat()
        role_format.setForeground(QColor(palette.get("role", "#34d399")))
        role_format.setFontWeight(QFont.Weight.Bold)
        role_pattern = QRegularExpression(
            r"\[(SYSTEM|USER|ASSISTANT|SYSTEM INSTRUCTION|CONTEXT)\]"
        )
        self.highlighting_rules.append((role_pattern, role_format))

        # 4. Inline code: `code`
        code_format = QTextCharFormat()
        code_format.setForeground(QColor(palette.get("code", "#f472b6")))
        code_format.setFontFamily("monospace")
        code_pattern = QRegularExpression(r"`[^`\n]+`")
        self.highlighting_rules.append((code_pattern, code_format))

        # 5. Unclosed or malformed variable markers (error style)
        unclosed_format = QTextCharFormat()
        unclosed_format.setForeground(QColor(palette.get("error", "#f87171")))
        unclosed_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        # Use same error color for underline, fallback to red
        underline_col = palette.get("error", "#f87171")
        try:
            unclosed_format.setUnderlineColor(QColor(underline_col))
        except Exception:
            unclosed_format.setUnderlineColor(QColor("#ef4444"))
        unclosed_pattern = QRegularExpression(r"\{\{[^}\n]*$")
        self.highlighting_rules.append((unclosed_pattern, unclosed_format))

    def apply_palette(self, palette: Dict[str, str]) -> None:
        """Switch highlighter colors at runtime and rehighlight."""
        self._current_palette = dict(palette)
        self._build_rules(self._current_palette)
        self.rehighlight()

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
