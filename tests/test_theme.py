"""Tests for themes, palettes, and syntax highlighter colors."""

import unittest
from prompt_manager.ui.theme import (
    THEMES,
    THEME_IDS,
    DEFAULT_THEME,
    list_themes,
    get_theme,
    get_stylesheet,
    get_highlighter_palette,
    is_dark_theme,
    is_light_theme,
)


class TestThemes(unittest.TestCase):

    def test_all_13_themes_registered(self):
        themes = list_themes()
        self.assertEqual(len(themes), 13)
        self.assertEqual(len(THEME_IDS), 13)
        expected_ids = {
            "midnight_dark",
            "midnight_light",
            "nord",
            "dracula",
            "catppuccin_mocha",
            "catppuccin_latte",
            "gruvbox_dark",
            "gruvbox_light",
            "solarized_dark",
            "solarized_light",
            "tokyo_night",
            "rose_pine",
            "everforest",
        }
        self.assertEqual(set(THEME_IDS), expected_ids)

    def test_theme_properties_and_stylesheets(self):
        for theme in list_themes():
            self.assertIn(theme.id, THEMES)
            self.assertTrue(theme.name)
            self.assertIn(theme.variant, ("dark", "light"))
            self.assertTrue(theme.description)
            stylesheet = get_stylesheet(theme.id)
            self.assertIsInstance(stylesheet, str)
            self.assertGreater(len(stylesheet), 100)
            self.assertIn("QMainWindow", stylesheet)
            self.assertIn("QPlainTextEdit", stylesheet)

    def test_highlighter_palettes(self):
        required_keys = {"variable_fg", "heading", "role", "code", "error"}
        for tid in THEME_IDS:
            palette = get_highlighter_palette(tid)
            self.assertIsInstance(palette, dict)
            for k in required_keys:
                self.assertIn(k, palette, f"Theme {tid} missing highlighter color {k}")
                self.assertTrue(palette[k].startswith("#"))

    def test_fallback_on_invalid_theme_id(self):
        fallback = get_theme("non_existent_theme_id")
        self.assertEqual(fallback.id, DEFAULT_THEME)

    def test_is_dark_and_is_light(self):
        self.assertTrue(is_dark_theme("midnight_dark"))
        self.assertFalse(is_light_theme("midnight_dark"))
        self.assertTrue(is_light_theme("midnight_light"))
        self.assertFalse(is_dark_theme("midnight_light"))


if __name__ == "__main__":
    unittest.main()
