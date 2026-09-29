"""Exercise autosave state transitions with Qt's offscreen platform."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QComboBox, QPlainTextEdit, QMessageBox

from prompt_manager.core.models import Folder, Prompt, VariableSpec
from prompt_manager.ui.components.variable_form import VariableFormWidget
from prompt_manager.storage.database import Database
from prompt_manager.ui.main_window import MainWindow


@pytest.fixture
def window(qapp, tmp_path):
    widget = MainWindow(Database(tmp_path / "editor.db"))
    yield widget
    widget.editor.autosave_timer.stop()
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_refresh_folders_preserves_unsaved_folder_selection(window):
    folder = window.repo.save_folder(Folder(name="Selected folder"))
    window._refresh_folders_and_tags()
    window.editor.folder_combo.setCurrentIndex(window.editor.folder_combo.findData(folder.id))
    window._on_create_folder("Another folder")
    assert window.editor.folder_combo.currentData() == folder.id
    window._on_save_prompt()
    assert window.repo.get_prompt_by_id(window._active_prompt.id).folder_id == folder.id


@pytest.mark.parametrize("action", ["select", "new", "template", "close", "favorite", "duplicate"])
def test_navigation_flushes_pending_autosave(window, action):
    original_id = window._active_prompt.id
    window.editor.template_edit.setPlainText("pending edit")
    assert window.editor.autosave_timer.isActive()
    if action == "select":
        other = window.repo.save_prompt(Prompt(title="Other"))
        window._on_prompt_selected(other.id)
    elif action == "new":
        window._on_new_prompt()
    elif action == "template":
        from prompt_manager.core.models import PromptTemplate
        template = window.repo.save_template(PromptTemplate(name="T", content="template"))
        window._instantiate_prompt_from_template(template.id)
    elif action == "close":
        window.close()
    elif action == "favorite":
        window._on_toggle_favorite(original_id)
    else:
        window._on_duplicate_prompt(original_id)
        assert window._active_prompt.template_content == "pending edit"
    assert window.repo.get_prompt_by_id(original_id).template_content == "pending edit"
    assert not window.editor.autosave_timer.isActive()


def test_failed_save_keeps_unsaved_editor_and_blocks_navigation(window, monkeypatch):
    original_id = window._active_prompt.id
    other = window.repo.save_prompt(Prompt(title="Other"))
    window.editor.template_edit.setPlainText("pending edit")
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args))
    with monkeypatch.context() as context:
        def fail(*args, **kwargs):
            raise OSError("disk full")
        context.setattr(window.repo, "save_prompt", fail)
        window._on_prompt_selected(other.id)
    assert errors
    assert window._active_prompt.id == original_id
    assert window.editor.get_template_content() == "pending edit"
    assert window.editor._is_dirty


def test_variable_specs_update_controls_and_clear_removed_values(qapp):
    form = VariableFormWidget()
    form.set_variables([VariableSpec("value", default_value="typed")])
    form.set_variables([VariableSpec("value", is_multiline=True)])
    assert isinstance(form._widgets["value"], QPlainTextEdit)
    assert form.get_values() == {"value": "typed"}
    form.set_variables([VariableSpec("value", options=["a", "b"])])
    assert isinstance(form._widgets["value"], QComboBox)
    form.set_variables([VariableSpec("value", options=["c", "d"])])
    assert form.get_values() == {"value": "c"}
    form.set_variables([])
    assert form.get_values() == {}
    form.deleteLater()


def test_failed_save_blocks_close(window, monkeypatch):
    from PyQt6.QtGui import QCloseEvent
    window.editor.template_edit.setPlainText("pending edit")
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    with monkeypatch.context() as context:
        def fail(*args, **kwargs):
            raise OSError("disk full")
        context.setattr(window.repo, "save_prompt", fail)
        event = QCloseEvent()
        window.closeEvent(event)
    assert not event.isAccepted()
    assert window.editor._is_dirty
