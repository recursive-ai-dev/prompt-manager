"""Regression tests for the proactive code stabilization pass.

Pure-Python coverage (no Qt required):
- Overflow-tolerant numeric coercion in models and exporter helpers
- Corrupt/non-dict settings.json tolerance in config
- Malformed JSON library import tolerance in storage.backup
- Keychain fallback vault: original write errors are surfaced, not masked
  by a double file-descriptor close (EBADF)
- Repository.get_template_by_name tolerance for empty/None names

Qt coverage (skipped automatically when PyQt6 is unavailable):
- VariableFormWidget rebuilds when variable metadata (not just names) change
- PromptEditorPanel.update_prompt_model canonicalizes tags
- TemplateManagerDialog preserves unsaved editor edits across list refreshes
- MainWindow resets an active folder/tag filter when the target is deleted
- ToastNotification stops a running fade-out when a new message is shown
- QuickLauncherHUD clears stale variable inputs when nothing matches
- thread_helpers releases workers promptly for finished threads and keeps
  them alive (referenced) while their thread is still running
- MainWindow._github_quick_push records last_sync after a successful push
  (regression: set_github_config was referenced but never imported, so a
  successful push raised NameError and was reported as a failure)

Second-pass (static analysis + deep audit) coverage:
- github_client._http_request survives non-dict JSON error bodies
- github_sync.pull_library_via_api rejects null content with GithubError
- Database._init_db closes the connection it opens
"""

import json
import math
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from prompt_manager.core.models import Folder, Prompt, PromptRevision
from prompt_manager.core.exporter import (
    _safe_float,
    _safe_int,
    to_langchain_template,
    to_llamaindex_template,
)
from prompt_manager.storage.database import Database
from prompt_manager.storage.repository import PromptRepository


# ── Numeric coercion overflow tolerance ─────────────────────────────────


class TestNumericCoercion(unittest.TestCase):
    """int(float(x)) raises OverflowError for inf/1e400 — must not crash."""

    def test_use_count_overflow_falls_back_to_zero(self):
        self.assertEqual(Prompt(use_count="1e400").use_count, 0)
        self.assertEqual(Prompt(use_count=float("inf")).use_count, 0)
        self.assertEqual(Prompt(use_count="-1e400").use_count, 0)

    def test_use_count_nan_falls_back_to_zero(self):
        self.assertEqual(Prompt(use_count="nan").use_count, 0)

    def test_use_count_still_coerces_normal_values(self):
        self.assertEqual(Prompt(use_count="42").use_count, 42)
        self.assertEqual(Prompt(use_count=3.9).use_count, 3)
        self.assertEqual(Prompt(use_count=True).use_count, 1)
        self.assertEqual(Prompt(use_count="").use_count, 0)

    def test_folder_sort_order_overflow_falls_back_to_zero(self):
        self.assertEqual(Folder(sort_order="1e400").sort_order, 0)
        self.assertEqual(Folder(sort_order=float("inf")).sort_order, 0)
        self.assertEqual(Folder(sort_order="7").sort_order, 7)

    def test_revision_number_overflow_falls_back_to_one(self):
        self.assertEqual(PromptRevision(revision_number="1e400").revision_number, 1)
        self.assertEqual(PromptRevision(revision_number=float("inf")).revision_number, 1)
        self.assertEqual(PromptRevision(revision_number="5").revision_number, 5)
        self.assertEqual(PromptRevision(revision_number=-3).revision_number, 1)

    def test_safe_int_overflow_and_non_finite(self):
        self.assertEqual(_safe_int("1e400"), 0)
        self.assertEqual(_safe_int(float("inf"), default=5), 5)
        self.assertEqual(_safe_int("nan"), 0)
        self.assertEqual(_safe_int(True), 1)
        self.assertEqual(_safe_int("3.7"), 3)
        self.assertEqual(_safe_int(None), 0)

    def test_safe_float_non_finite_falls_back(self):
        self.assertEqual(_safe_float("1e400"), 0.7)
        self.assertEqual(_safe_float(float("inf")), 0.7)
        self.assertEqual(_safe_float("nan"), 0.7)
        self.assertEqual(_safe_float("0.9"), 0.9)
        self.assertEqual(_safe_float(None), 0.7)
        self.assertEqual(_safe_float(1), 1.0)
        self.assertNotAlmostEqual(_safe_float("inf"), float("inf"))
        self.assertFalse(math.isnan(_safe_float("nan")))


# ── Exporter variable conversion ────────────────────────────────────────


class TestExporterVariableConversion(unittest.TestCase):
    """LangChain/LlamaIndex export must use the canonical variable grammar
    (same as template_engine), including hyphenated variable names."""

    def test_hyphenated_variables_converted(self):
        prompt = Prompt(template_content="Hi {{my-var}} and {{plain}}")
        out = to_langchain_template(prompt)
        self.assertIn("{my-var}", out)
        self.assertIn("{plain}", out)
        self.assertNotIn("{{my-var}}", out)

    def test_hyphenated_variables_with_default_converted(self):
        prompt = Prompt(template_content="X {{with-hyphen:default val}} Y")
        out = to_llamaindex_template(prompt)
        self.assertIn("{with-hyphen}", out)
        self.assertNotIn("{{with-hyphen:default val}}", out)

    def test_plain_variables_still_converted(self):
        prompt = Prompt(
            template_content="A {{alpha}} B",
            system_instruction="Sys {{beta}}",
        )
        out = to_langchain_template(prompt)
        self.assertIn("{alpha}", out)
        self.assertIn("{beta}", out)


# ── Config corruption tolerance ─────────────────────────────────────────


class TestConfigCorruptionTolerance(unittest.TestCase):
    """A settings.json containing valid JSON that is not an object (or with
    non-dict nested blocks) must fall back to defaults, not crash."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.temp_dir.name) / "settings.json"
        self.config_dir = Path(self.temp_dir.name) / "config"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, raw):
        self.settings_file.write_text(raw, encoding="utf-8")

    def _with_patch(self, fn, *args):
        from prompt_manager import config

        with patch.object(config, "CONFIG_FILE_PATH", self.settings_file), \
             patch.object(config, "APP_CONFIG_DIR", self.config_dir):
            return fn(*args)

    def test_top_level_list(self):
        from prompt_manager import config

        self._write(json.dumps([1, 2, 3]))
        self.assertEqual(self._with_patch(config.get_theme_id), config.DEFAULT_THEME_ID)
        gh = self._with_patch(config.get_github_config)
        self.assertEqual(gh["token"], "")
        self.assertFalse(gh["connected"])

    def test_top_level_string(self):
        from prompt_manager import config

        self._write('"just a string"')
        self.assertEqual(self._with_patch(config.get_theme_id), config.DEFAULT_THEME_ID)

    def test_top_level_number(self):
        from prompt_manager import config

        self._write("5")
        self.assertEqual(
            self._with_patch(config.get_pollinations_config)["model"],
            config.DEFAULT_POLLINATIONS_MODEL,
        )

    def test_nested_list_github_block(self):
        from prompt_manager import config

        self._write(json.dumps({"github": ["x"], "pollinations": 5}))
        gh = self._with_patch(config.get_github_config)
        self.assertFalse(gh["connected"])
        pol = self._with_patch(config.get_pollinations_config)
        self.assertEqual(pol["model"], config.DEFAULT_POLLINATIONS_MODEL)
        # set_* on corrupt nested blocks must also not crash
        self._with_patch(config.set_github_config, {"repo": "a/b"})
        self._with_patch(config.set_pollinations_config, {"model": "mistral"})
        self.assertEqual(self._with_patch(config.get_github_config)["repo"], "a/b")

    def test_valid_settings_still_load(self):
        from prompt_manager import config

        self._write(json.dumps({"theme": "dracula", "github": {"repo": "o/r"}}))
        self.assertEqual(self._with_patch(config.get_theme_id), "dracula")
        self.assertEqual(self._with_patch(config.get_github_config)["repo"], "o/r")


# ── Backup import corruption tolerance ──────────────────────────────────


class TestBackupImportCorruptionTolerance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "t.db")
        self.repo = PromptRepository(self.db)
        self.file = Path(self.temp_dir.name) / "lib.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _import(self, data):
        from prompt_manager.storage.backup import import_library_from_json

        self.file.write_text(json.dumps(data), encoding="utf-8")
        return import_library_from_json(self.repo, self.file)

    def test_top_level_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            self._import(["a", "list"])

    def test_non_dict_entries_skipped_good_ones_imported(self):
        data = {
            "folders": ["bad", {"name": "Good Folder"}],
            "tags": {"not": "a list"},
            "templates": [42, {"name": "T", "content": "c {{x}}"}],
            "prompts": [42, None, {"id": "p1", "title": "T1"}],
        }
        count = self._import(data)
        self.assertEqual(count, 1)
        self.assertTrue(any(f.name == "Good Folder" for f in self.repo.list_folders()))
        self.assertIsNotNone(self.repo.get_template_by_name("T"))
        self.assertIsNotNone(self.repo.get_prompt_by_id("p1"))

    def test_non_list_section_treated_as_empty(self):
        count = self._import({"folders": {"id": "x"}, "prompts": "nope"})
        self.assertEqual(count, 0)

    def test_normal_import_still_works(self):
        data = {
            "folders": [{"id": "f1", "name": "F"}],
            "tags": [{"id": "t1", "name": "tag1"}],
            "prompts": [{"id": "p1", "title": "P", "tags": ["tag1"]}],
        }
        count = self._import(data)
        self.assertEqual(count, 1)
        fetched = self.repo.get_prompt_by_id("p1")
        self.assertEqual(fetched.tags, ["tag1"])


# ── Keychain fallback vault error surfacing ─────────────────────────────


class TestKeyVaultWriteErrors(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        from prompt_manager.core.keychain import KeyVault

        self.vault = KeyVault(
            use_keyring=False, vault_path=Path(self.temp_dir.name) / "vault.dat"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_roundtrip(self):
        self.vault.set_api_key("openai", "sk-test")
        self.assertEqual(self.vault.get_api_key("openai"), "sk-test")
        self.vault.set_api_key("openai", "")
        self.assertEqual(self.vault.get_api_key("openai"), "")

    def test_write_error_surfaced_not_masked_by_ebadf(self):
        """A failing write must surface the original error (previously the
        manual os.close(fd) after the with-block raised EBADF instead)."""
        import os as _os

        class FailingFile:
            def __init__(self, fd):
                self._fd = fd

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                try:
                    _os.close(self._fd)
                except OSError:
                    pass
                return False

            def write(self, b):
                raise OSError("ENOSPC simulated")

            def flush(self):
                pass

            def fileno(self):
                return self._fd

        real_fdopen = _os.fdopen

        def fake_fdopen(fd, mode):
            return FailingFile(fd)

        _os.fdopen = fake_fdopen
        try:
            with self.assertRaises(OSError) as ctx:
                self.vault._write_fallback_vault({"k": "v"})
            self.assertIn("ENOSPC simulated", str(ctx.exception))
            self.assertNotIn("Bad file descriptor", str(ctx.exception))
        finally:
            _os.fdopen = real_fdopen
        # Failed write leaves no .tmp litter and the old vault intact
        self.assertFalse((Path(self.temp_dir.name) / "vault.tmp").exists())

    def test_corrupt_vault_file_falls_back_to_empty(self):
        self.vault.vault_path.write_bytes(b"garbage that is not our format")
        self.assertEqual(self.vault.get_api_key("openai"), "")


# ── Repository name tolerance ───────────────────────────────────────────


class TestRepositoryNameTolerance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "t.db")
        self.repo = PromptRepository(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_template_by_name_none_or_blank(self):
        from prompt_manager.core.models import PromptTemplate

        self.repo.save_template(PromptTemplate(name="alpha", content="c"))
        self.assertIsNone(self.repo.get_template_by_name(None))
        self.assertIsNone(self.repo.get_template_by_name("   "))
        self.assertEqual(self.repo.get_template_by_name("alpha").name, "alpha")


# ── GitHub client / sync error-path resilience ──────────────────────────


class TestGithubClientErrorParsing(unittest.TestCase):
    def test_non_dict_json_error_body_still_raises_github_error(self):
        """A non-dict JSON error body (e.g. a bare list) used to crash the
        except-handler itself (AttributeError) and mask the HTTP error."""
        import io
        from urllib.error import HTTPError

        import prompt_manager.integrations.github_client as gc

        def fake_urlopen(req, timeout=None):
            raise HTTPError(
                req.full_url, 422, "Unprocessable Entity", None, io.BytesIO(b'["unexpected","shape"]')
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(gc.GithubError) as ctx:
                gc._http_request("GET", "https://api.github.com/x")
        self.assertEqual(ctx.exception.status, 422)
        self.assertIn("unexpected", str(ctx.exception))

    def test_dict_error_body_message_preferred(self):
        import io
        from urllib.error import HTTPError

        import prompt_manager.integrations.github_client as gc

        def fake_urlopen(req, timeout=None):
            raise HTTPError(
                req.full_url, 401, "Unauthorized", None, io.BytesIO(b'{"message": "Bad credentials"}')
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(gc.GithubError) as ctx:
                gc._http_request("GET", "https://api.github.com/x")
        self.assertEqual(str(ctx.exception), "Bad credentials")


class TestGithubSyncPullResilience(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "t.db")
        self.repo = PromptRepository(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pull_with_null_content_raises_github_error(self):
        from unittest.mock import MagicMock

        import prompt_manager.core.github_sync as gs

        client = MagicMock()
        client.get_file.return_value = {"content": None}
        with self.assertRaises(gs.GithubError):
            gs.pull_library_via_api(self.repo, client, "o/r")

    def test_pull_with_undecodable_content_raises_github_error(self):
        from unittest.mock import MagicMock

        import prompt_manager.core.github_sync as gs

        client = MagicMock()
        client.get_file.return_value = {"content": "!!!!not-base64-!!!"}
        with self.assertRaises(gs.GithubError):
            gs.pull_library_via_api(self.repo, client, "o/r")


class TestDatabaseConnectionLifecycle(unittest.TestCase):
    def test_init_closes_its_connection(self):
        """sqlite3 `with conn` only manages the transaction — the connection
        must be closed explicitly or the DB file handle lingers until GC."""
        import sqlite3

        db_path = Path(tempfile.mkdtemp()) / "t.db"
        created: list = []
        orig_get_connection = Database.get_connection

        def tracking(self):
            conn = orig_get_connection(self)
            created.append(conn)
            return conn

        with patch.object(Database, "get_connection", tracking):
            Database(db_path)

        def is_closed(c):
            try:
                c.execute("SELECT 1")
                return False
            except sqlite3.ProgrammingError:
                return True

        self.assertTrue(created, "_init_db should open a connection")
        self.assertTrue(all(is_closed(c) for c in created), "all connections must be closed")


# ── Qt widget regression tests ──────────────────────────────────────────

PyQt6 = __import__("importlib").util.find_spec("PyQt6")
HAS_QT = PyQt6 is not None

if HAS_QT:
    import os as _os

    if not _os.environ.get("QT_QPA_PLATFORM") and not _os.environ.get("DISPLAY"):
        _os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PyQt6.QtCore import QPropertyAnimation, QThread
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QComboBox

    _app = QApplication.instance() or QApplication([])

    from prompt_manager import config as _config
    from prompt_manager.core.models import PromptTemplate, VariableSpec
    from prompt_manager.ui.components.editor import PromptEditorPanel
    from prompt_manager.ui.components.quick_launcher import QuickLauncherHUD
    from prompt_manager.ui.components.template_manager import TemplateManagerDialog
    from prompt_manager.ui.components.thread_helpers import WorkerLifetime, track_worker
    from prompt_manager.ui.components.toast import ToastNotification
    from prompt_manager.ui.components.variable_form import VariableFormWidget

    class _QtTempBase(unittest.TestCase):
        """Base for widget tests.

        Top-level widgets created here are tracked and explicitly torn down
        in tearDown.  Without that, reference cycles (signal connections to
        bound methods) keep wrappers alive until the cyclic GC happens to
        run, which can race with pending timers (e.g. the editor's 400 ms
        autosave debounce) and intermittently abort the test process.
        """

        def setUp(self):
            self.temp_dir = tempfile.TemporaryDirectory()
            self._cfg_patch = patch.object(
                _config, "CONFIG_FILE_PATH", Path(self.temp_dir.name) / "settings.json"
            )
            self._cfg_patch.start()
            self.db = Database(Path(self.temp_dir.name) / "t.db")
            self.repo = PromptRepository(self.db)
            self._widgets = []

        def tearDown(self):
            for w in self._widgets:
                try:
                    w.close()
                except Exception:
                    pass
            self._widgets.clear()
            import gc

            gc.collect()
            QTest.qWait(50)
            self._cfg_patch.stop()
            self.temp_dir.cleanup()

        def _track(self, w):
            self._widgets.append(w)
            return w

        def _main_window(self):
            from prompt_manager.ui.main_window import MainWindow

            return self._track(MainWindow(db=self.db))

    class TestVariableFormMetadataRebuild(_QtTempBase):
        def test_rebuild_when_options_change(self):
            vf = VariableFormWidget()
            vf.set_variables([VariableSpec(name="tone", options=["casual", "formal"])])
            combo1 = vf._widgets["tone"]
            self.assertIsInstance(combo1, QComboBox)
            items1 = [combo1.itemText(i) for i in range(combo1.count())]
            self.assertEqual(items1, ["casual", "formal"])

            # Same name, new options -> widgets must be rebuilt
            vf.set_variables([VariableSpec(name="tone", options=["a", "b", "c"])])
            combo2 = vf._widgets["tone"]
            self.assertIsNot(combo2, combo1)
            items2 = [combo2.itemText(i) for i in range(combo2.count())]
            self.assertEqual(items2, ["a", "b", "c"])

        def test_no_rebuild_when_signature_unchanged(self):
            vf = self._track(VariableFormWidget())
            vf.set_variables([VariableSpec(name="v", default_value="d")])
            widget1 = vf._widgets["v"]
            vf.set_variables([VariableSpec(name="v", default_value="d")])
            self.assertIs(vf._widgets["v"], widget1)

        def test_reset_uses_new_default_after_metadata_change(self):
            vf = self._track(VariableFormWidget())
            vf.set_variables([VariableSpec(name="lang", default_value="python")])
            vf.set_variables([VariableSpec(name="lang", default_value="rust")])
            vf.reset_to_defaults()
            self.assertEqual(vf._widgets["lang"].text(), "rust")

    class TestEditorTagCanonicalization(_QtTempBase):
        def test_update_prompt_model_normalizes_tags(self):
            ed = self._track(PromptEditorPanel())
            p = Prompt(title="T")
            ed.title_input.setText("T")
            ed.tags_input.setText("Coding, #Refactor , coding")
            ed.update_prompt_model(p)
            self.assertEqual(p.tags, ["coding", "refactor"])
            # The text edits above armed the 400 ms autosave debounce; drop
            # it deterministically so it cannot fire during a later test's
            # event pump after this editor is torn down.
            ed.autosave_timer.stop()

    class TestTemplateManagerEditPreservation(_QtTempBase):
        def test_unsaved_edits_survive_list_refresh(self):
            self.repo.save_template(PromptTemplate(name="alpha", content="base {{x}}"))
            self.repo.save_template(PromptTemplate(name="beta", content="other {{y}}"))
            dlg = self._track(TemplateManagerDialog(self.repo, None))

            for i in range(dlg.list_widget.count()):
                if dlg.list_widget.item(i).text().startswith("alpha"):
                    dlg.list_widget.setCurrentRow(i)
                    break
            self.assertEqual(dlg.editor.name_input.text(), "alpha")

            dlg.editor.content_edit.setPlainText("EDITED {{x}}")
            dlg._refresh_list()
            self.assertEqual(dlg.editor.content_edit.toPlainText(), "EDITED {{x}}")

            # Switching to a different template still reloads
            for i in range(dlg.list_widget.count()):
                if dlg.list_widget.item(i).text().startswith("beta"):
                    dlg.list_widget.setCurrentRow(i)
                    break
            self.assertEqual(dlg.editor.content_edit.toPlainText(), "other {{y}}")

    class TestMainWindowFilterReset(_QtTempBase):
        def test_deleting_filtered_folder_resets_filter(self):
            from prompt_manager.core.models import Folder

            w = self._main_window()
            folder = Folder(name="to-delete")
            self.repo.save_folder(folder)
            w._on_filter_changed("folder", folder.id)
            self.assertEqual(w._current_filter_id, folder.id)
            w._on_delete_folder(folder.id)
            self.assertEqual((w._current_filter_type, w._current_filter_id), ("all", None))

        def test_deleting_filtered_tag_resets_filter(self):
            from prompt_manager.core.models import Tag

            w = self._main_window()
            self.repo.save_tag(Tag(name="to-delete"))
            tag = [t for t in self.repo.list_tags() if t.name == "to-delete"][0]
            w._on_filter_changed("tag", tag.id)
            w._on_delete_tag(tag.id)
            self.assertEqual((w._current_filter_type, w._current_filter_id), ("all", None))

        def test_deleting_unrelated_folder_keeps_filter(self):
            from prompt_manager.core.models import Folder

            w = self._main_window()
            kept = Folder(name="keep")
            other = Folder(name="other")
            self.repo.save_folder(kept)
            self.repo.save_folder(other)
            w._on_filter_changed("folder", kept.id)
            w._on_delete_folder(other.id)
            self.assertEqual((w._current_filter_type, w._current_filter_id), ("folder", kept.id))

    class TestToastFadeStop(_QtTempBase):
        def test_new_message_stops_running_fade(self):
            w = self._main_window()
            toast = ToastNotification(w)
            toast.show_message("first")
            QTest.qWait(60)
            toast._timer.stop()
            toast._start_fade_out()
            QTest.qWait(100)
            self.assertEqual(toast._fade_anim.state(), QPropertyAnimation.State.Running)
            toast.show_message("second")
            self.assertEqual(toast._fade_anim.state(), QPropertyAnimation.State.Stopped)
            self.assertEqual(toast._opacity_effect.opacity(), 1.0)

        def test_rapid_messages_do_not_fade_immediately(self):
            w = self._main_window()
            toast = ToastNotification(w)
            toast.show_message("one", duration_ms=300)
            QTest.qWait(50)
            toast.show_message("two", duration_ms=300)
            QTest.qWait(50)
            self.assertEqual(toast._fade_anim.state(), QPropertyAnimation.State.Stopped)
            self.assertGreater(toast._opacity_effect.opacity(), 0.5)

    class TestQuickLauncherStaleVars(_QtTempBase):
        def test_stale_var_inputs_cleared_on_no_match(self):
            self.repo.save_prompt(Prompt(title="Searchable var prompt", template_content="Hi {{who}}"))
            hud = self._track(QuickLauncherHUD(self.repo, None))
            hud.search_input.setText("Searchable")
            QTest.qWait(30)
            self.assertEqual(len(hud._var_inputs), 1)
            hud.search_input.setText("zzz-no-match-zzz")
            QTest.qWait(30)
            self.assertEqual(len(hud._var_inputs), 0)
            self.assertFalse(hud.var_container.isVisible())

    class TestGithubQuickPushRecordsSync(_QtTempBase):
        """Regression: set_github_config was called in _github_quick_push but
        never imported — every *successful* push raised NameError, was caught
        by the generic handler, and was reported to the user as a failure
        (and last_sync was never recorded)."""

        def test_successful_push_records_last_sync(self):
            import prompt_manager.core.github_sync as gs
            from PyQt6.QtWidgets import QMessageBox

            from prompt_manager.config import get_github_config, set_github_config

            w = self._main_window()
            set_github_config({"token": "ghp_testtoken", "repo": "o/r"})
            with patch.object(
                gs, "push_library_via_api", return_value={"commit": {"sha": "abcdef1234567"}}
            ), patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
            ), patch.object(
                QMessageBox, "critical"
            ) as critical_mock:
                w._github_quick_push()
            critical_mock.assert_not_called()
            gh = get_github_config()
            self.assertTrue(gh.get("last_sync"))
            self.assertEqual(gh["last_sync_sha"], "abcdef1")

        def test_push_failure_does_not_record_sync(self):
            import prompt_manager.core.github_sync as gs
            from PyQt6.QtWidgets import QMessageBox

            from prompt_manager.config import get_github_config, set_github_config

            w = self._main_window()
            set_github_config({"token": "ghp_testtoken", "repo": "o/r"})
            with patch.object(
                gs, "push_library_via_api", side_effect=gs.GithubError("boom", status=403)
            ), patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
            ), patch.object(
                QMessageBox, "critical"
            ) as critical_mock:
                w._github_quick_push()
            critical_mock.assert_called_once()
            gh = get_github_config()
            self.assertFalse(gh.get("last_sync"))

    class TestThreadHelpers(_QtTempBase):
        def test_finished_thread_released_immediately(self):
            from PyQt6.QtCore import QObject

            class Worker(QObject):
                pass

            t = QThread()
            t.start()
            t.quit()
            self.assertTrue(t.wait(3000))
            holders = []
            track_worker(Worker(), t, holders)
            self.assertEqual(len(holders), 0)

        def test_running_thread_worker_held_until_finished(self):
            from PyQt6.QtCore import QObject

            class Worker(QObject):
                pass

            t = QThread()

            def block():
                time.sleep(0.2)

            t.started.connect(block)
            worker = Worker()
            t.start()
            holders = []
            track_worker(worker, t, holders)
            self.assertEqual(len(holders), 1)
            self.assertFalse(holders[0].released)
            t.quit()
            self.assertTrue(t.wait(3000))
            for _ in range(100):
                if holders[0].released:
                    break
                time.sleep(0.02)
                _app.processEvents()
            self.assertTrue(holders[0].released)

        def test_release_does_not_require_wait_timeout_when_done_fast(self):
            from PyQt6.QtCore import QObject

            class Worker(QObject):
                pass

            t = QThread()
            t.start()
            t.quit()
            self.assertTrue(t.wait(3000))
            lifetime = WorkerLifetime(Worker(), t)
            self.assertTrue(lifetime.released)


if not HAS_QT:
    @unittest.skipUnless(False, "PyQt6 not installed")
    class TestQtUnavailablePlaceholder(unittest.TestCase):
        def test_skip(self):
            pass


if __name__ == "__main__":
    unittest.main()
