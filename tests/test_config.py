"""Tests for configuration and settings persistence."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prompt_manager import config


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.temp_dir.name) / "settings.json"
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.config_dir = Path(self.temp_dir.name) / "config"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_theme_get_and_set(self):
        with patch.object(config, "CONFIG_FILE_PATH", self.settings_file), \
             patch.object(config, "APP_CONFIG_DIR", self.config_dir):
            self.assertEqual(config.get_theme_id(), config.DEFAULT_THEME_ID)
            config.set_theme_id("dracula")
            self.assertEqual(config.get_theme_id(), "dracula")

    def test_github_config_lifecycle(self):
        with patch.object(config, "CONFIG_FILE_PATH", self.settings_file), \
             patch.object(config, "APP_CONFIG_DIR", self.config_dir):
            gh = config.get_github_config()
            self.assertEqual(gh["token"], "")
            self.assertFalse(config.is_github_connected())

            config.set_github_config({
                "token": "ghp_secrettoken123",
                "token_type": "pat",
                "username": "octocat",
                "repo": "octocat/my-prompts",
                "connected": True,
            })
            self.assertTrue(config.is_github_connected())
            gh_updated = config.get_github_config()
            self.assertEqual(gh_updated["username"], "octocat")
            self.assertEqual(gh_updated["repo"], "octocat/my-prompts")

            config.clear_github_config()
            self.assertFalse(config.is_github_connected())
            gh_cleared = config.get_github_config()
            self.assertEqual(gh_cleared["token"], "")
            self.assertFalse(gh_cleared["connected"])

    def test_generic_setting(self):
        with patch.object(config, "CONFIG_FILE_PATH", self.settings_file), \
             patch.object(config, "APP_CONFIG_DIR", self.config_dir):
            self.assertIsNone(config.get_setting("custom_key"))
            self.assertEqual(config.get_setting("custom_key", "default_val"), "default_val")
            config.set_setting("custom_key", 42)
            self.assertEqual(config.get_setting("custom_key"), 42)


if __name__ == "__main__":
    unittest.main()
