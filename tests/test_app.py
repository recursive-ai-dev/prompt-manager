"""Headless CLI behavior and credential output regression tests."""

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from prompt_manager import app, config


def invoke(*args):
    with patch.object(sys, "argv", ["prompt-manager", *args]), pytest.raises(SystemExit) as result:
        app.main()
    assert result.value.code == 0


def test_github_status_redacts_token(capsys):
    config.set_github_config({"token": "ghp_private", "connected": True, "repo": "me/prompts"})
    invoke("--github-status")
    output = capsys.readouterr().out
    assert "ghp_private" not in output
    assert "[REDACTED]" in output
    assert "me/prompts" in output


@pytest.mark.parametrize("text", ["x" * 1000, "line one\nline two", "text\0with nul"])
def test_run_ai_accepts_non_path_prompt(text, capsys):
    with patch("prompt_manager.integrations.pollinations_client.PollinationsClient.generate", return_value="answer") as generate:
        invoke("--run-ai", text)
        assert generate.call_args.kwargs["prompt"] == text
    assert "answer" in capsys.readouterr().out


def test_run_ai_reads_prompt_file(tmp_path):
    path = tmp_path / "prompt.txt"
    path.write_text("file contents")
    with patch("prompt_manager.integrations.pollinations_client.PollinationsClient.generate", return_value="answer") as generate:
        invoke("--run-ai", str(path))
        assert generate.call_args.kwargs["prompt"] == "file contents"


@pytest.mark.parametrize("action", ["--github-push", "--github-pull"])
def test_successful_sync_exits_before_gui(action):
    config.set_github_config({"token": "ghp_private", "repo": "me/prompts"})
    with patch("prompt_manager.storage.database.Database"), \
         patch("prompt_manager.storage.repository.PromptRepository"), \
         patch("prompt_manager.core.github_sync.push_library_via_api", return_value={}), \
         patch("prompt_manager.core.github_sync.pull_library_via_api", return_value=(0, {})):
        invoke(action)


def test_pure_python_modules_and_cli_load_without_qt(tmp_path):
    code = '''
import importlib.abc
import sys
class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith("PyQt6"):
            raise ImportError("Qt intentionally unavailable")
sys.meta_path.insert(0, NoQt())
from prompt_manager.ui import theme
from prompt_manager.ui.assets import asset_generator
from prompt_manager import app
sys.argv = ["prompt-manager", "--version"]
app.main()
'''
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path)}
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert config.APP_VERSION in result.stdout
