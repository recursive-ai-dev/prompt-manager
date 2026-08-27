"""Dynamic form widget generated from template variable specifications."""

from typing import Dict, List
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prompt_manager.core.models import VariableSpec


class VariableFormWidget(QFrame):
    """Generates dynamic inputs for each {{variable}} detected in the active prompt."""

    values_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("variableFormFrame")
        self._current_specs: List[VariableSpec] = []
        self._current_values: Dict[str, str] = {}
        self._widgets: Dict[str, QWidget] = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("VARIABLES")
        header_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;"
        )
        header_label.setToolTip("Dynamic parameters detected in the active prompt template")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.clear_btn.setToolTip("Clear all variable inputs to blank")
        self.clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(self.clear_btn)

        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.reset_btn.setToolTip("Reset all variable inputs to their template default values")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        header_layout.addWidget(self.reset_btn)
        main_layout.addLayout(header_layout)

        # Scrollable form container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setToolTip("Fill in variable values to live-compile the prompt")

        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(10)
        self.form_layout.addStretch()

        self.scroll_area.setWidget(self.form_container)
        main_layout.addWidget(self.scroll_area)

        self.no_vars_label = QLabel("No variables detected in template.\nAdd {{variable_name}} to parameterize.")
        self.no_vars_label.setStyleSheet("color: #64748b; font-style: italic; padding: 12px 0;")
        main_layout.addWidget(self.no_vars_label)

    def set_variables(self, specs: List[VariableSpec]):
        """Update form fields based on variable specifications, preserving existing typed values."""
        current_names = [s.name for s in self._current_specs]
        new_names = [s.name for s in specs]

        self._current_specs = specs

        if not specs:
            self.no_vars_label.show()
            self.scroll_area.hide()
            self.clear_btn.hide()
            self.reset_btn.hide()
            self._current_values = {}
            self.values_changed.emit({})
            return

        self.no_vars_label.hide()
        self.scroll_area.show()
        self.clear_btn.show()
        self.reset_btn.show()

        if current_names == new_names:
            return

        # Clear existing fields
        for widget in self._widgets.values():
            widget.deleteLater()
        self._widgets.clear()

        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for spec in specs:
            field_wrapper = QWidget()
            f_layout = QVBoxLayout(field_wrapper)
            f_layout.setContentsMargins(0, 0, 0, 0)
            f_layout.setSpacing(3)

            label_row = QHBoxLayout()
            var_label = QLabel(spec.name)
            var_label.setStyleSheet("font-weight: 600; font-size: 11px; color: #cbd5e1;")
            var_label.setToolTip(f"Parameter: {spec.name}")
            label_row.addWidget(var_label)

            if spec.default_value:
                def_hint = QLabel(f"(default: {spec.default_value})")
                def_hint.setStyleSheet("font-size: 10px; color: #64748b;")
                def_hint.setToolTip(f"Default fallback value: '{spec.default_value}'")
                label_row.addWidget(def_hint)
            label_row.addStretch()
            f_layout.addLayout(label_row)

            initial_val = self._current_values.get(spec.name, spec.default_value)

            if spec.has_options:
                combo = QComboBox()
                combo.addItems(spec.options)
                combo.setToolTip(f"Select option for '{spec.name}'")
                if initial_val in spec.options:
                    combo.setCurrentText(initial_val)
                elif spec.default_value in spec.options:
                    combo.setCurrentText(spec.default_value)
                combo.currentTextChanged.connect(self._on_input_changed)
                f_layout.addWidget(combo)
                self._widgets[spec.name] = combo
            elif spec.is_multiline:
                text_edit = QPlainTextEdit()
                text_edit.setPlaceholderText(spec.default_value or f"Enter {spec.name}...")
                text_edit.setToolTip(f"Multi-line input for '{spec.name}'")
                text_edit.setPlainText(initial_val)
                text_edit.setMaximumHeight(90)
                text_edit.textChanged.connect(self._on_input_changed)
                f_layout.addWidget(text_edit)
                self._widgets[spec.name] = text_edit
            else:
                line_edit = QLineEdit()
                line_edit.setPlaceholderText(spec.default_value or f"Enter {spec.name}...")
                line_edit.setToolTip(f"Value for '{spec.name}'")
                line_edit.setText(initial_val)
                line_edit.textChanged.connect(self._on_input_changed)
                f_layout.addWidget(line_edit)
                self._widgets[spec.name] = line_edit

            self.form_layout.addWidget(field_wrapper)

        self.form_layout.addStretch()
        self._emit_current_values()

    def get_values(self) -> Dict[str, str]:
        values = {}
        for name, widget in self._widgets.items():
            if isinstance(widget, QLineEdit):
                values[name] = widget.text()
            elif isinstance(widget, QPlainTextEdit):
                values[name] = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                values[name] = widget.currentText()
        return values

    def reset_to_defaults(self):
        """Reset all inputs to template defaults."""
        for spec in self._current_specs:
            widget = self._widgets.get(spec.name)
            if not widget:
                continue
            if isinstance(widget, QLineEdit):
                widget.setText(spec.default_value)
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(spec.default_value)
            elif isinstance(widget, QComboBox):
                if spec.default_value in spec.options:
                    widget.setCurrentText(spec.default_value)
        self._emit_current_values()

    def clear_all(self):
        """Clear all inputs to empty strings."""
        for spec in self._current_specs:
            widget = self._widgets.get(spec.name)
            if not widget:
                continue
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QPlainTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                if widget.count() > 0:
                    widget.setCurrentIndex(0)
        self._emit_current_values()

    def _on_input_changed(self):
        self._emit_current_values()

    def _emit_current_values(self):
        self._current_values = self.get_values()
        self.values_changed.emit(self._current_values)
