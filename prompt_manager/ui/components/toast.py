"""Floating toast notification popup for desktop actions."""

from PyQt6.QtCore import QPoint, QPropertyAnimation, QTimer, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class ToastNotification(QLabel):
    """Temporary notification pill that overlays the main window."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            """
            QLabel {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
            }
            """
        )
        self.hide()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(250)
        self._fade_anim.finished.connect(self._on_fade_finished)

    def show_message(self, text: str, duration_ms: int = 1800):
        self.setText(text)
        self.adjustSize()

        # Center horizontally at the top/bottom of parent window
        parent = self.parentWidget()
        if parent:
            x = (parent.width() - self.width()) // 2
            y = parent.height() - self.height() - 40
            self.move(x, y)

        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def _start_fade_out(self):
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self):
        if self._opacity_effect.opacity() == 0.0:
            self.hide()
