"""UI module for Prompt Manager.

``MainWindow`` is exposed lazily so that importing lightweight, Qt-free
submodules (e.g. ``prompt_manager.ui.theme``) does not pull in PyQt6 and its
system OpenGL libraries. This keeps headless CLI commands such as
``--list-themes`` working on servers without a GUI stack.
"""

from typing import TYPE_CHECKING

__all__ = ["MainWindow"]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from prompt_manager.ui.main_window import MainWindow


def __getattr__(name: str):
    if name == "MainWindow":
        from prompt_manager.ui.main_window import MainWindow

        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
