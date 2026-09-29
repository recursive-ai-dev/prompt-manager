"""UI exports, loaded only when a Qt window is requested."""

__all__ = ["MainWindow"]


def __getattr__(name):
    if name == "MainWindow":
        from prompt_manager.ui.main_window import MainWindow
        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
