"""Syntax highlighter for prompt templates, mustache variables, and markdown structures."""

import re
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PromptSyntaxHighlighter(QSyntaxHighlighter):
    """Highlights {{variables}}, markdown headers, and code fences."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 1. Mustache Variables: {{variable}}, {{var:default}}, {{var|multiline}}
        var_format = QTextCharFormat()
        var_format.setForeground(QColor("#fbbf24"))  # Warm amber
        var_format.setBackground(QColor("#2d2415"))  # Subtle dark amber bg
        var_format.setFontWeight(QFont.Weight.Bold)
        var_pattern = QRegularExpression(
            r"\{\{\s*[a-zA-Z0-9_\-]+(?::[^}|]+)?(?:\|[^}]+)?\s*\}\}"
        )
        self.highlighting_rules.append((var_pattern, var_format))

        # 2. Markdown Headings: #, ##, ###
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor("#60a5fa"))  # Bright sky blue
        heading_format.setFontWeight(QFont.Weight.Bold)
        heading_pattern = QRegularExpression(r"^(#{1,6}\s.*)$")
        self.highlighting_rules.append((heading_pattern, heading_format))

        # 3. Role markers: [SYSTEM], [USER], [ASSISTANT]
        role_format = QTextCharFormat()
        role_format.setForeground(QColor("#34d399"))  # Emerald green
        role_format.setFontWeight(QFont.Weight.Bold)
        role_pattern = QRegularExpression(
            r"\[(SYSTEM|USER|ASSISTANT|SYSTEM INSTRUCTION|CONTEXT)\]"
        )
        self.highlighting_rules.append((role_pattern, role_format))

        # 4. Inline code: `code`
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("#f472b6"))  # Pink/Rose
        code_format.setFontFamily("monospace")
        code_pattern = QRegularExpression(r"`[^`\n]+`")
        self.highlighting_rules.append((code_pattern, code_format))

        # 5. Unclosed or malformed variable markers (error style)
        unclosed_format = QTextCharFormat()
        unclosed_format.setForeground(QColor("#f87171"))  # Red
        unclosed_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        unclosed_format.setUnderlineColor(QColor("#ef4444"))
        unclosed_pattern = QRegularExpression(r"\{\{[^}\n]*$")
        self.highlighting_rules.append((unclosed_pattern, unclosed_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
