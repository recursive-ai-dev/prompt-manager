"""Tests for themes, palettes, OS font integration, and syntax highlighter colors."""

import unittest
from prompt_manager.ui.fonts import FONT_STACKS, get_font_stack, get_ui_font_css
from prompt_manager.ui.theme import (
    THEMES,
    THEME_IDS,
    DEFAULT_THEME,
    list_themes,
    list_theme_categories,
    get_theme,
    get_stylesheet,
    get_highlighter_palette,
    is_dark_theme,
    is_light_theme,
)


class TestThemes(unittest.TestCase):

    def test_theme_count_and_categories(self):
        themes = list_themes()
        self.assertGreaterEqual(len(themes), 30)
        self.assertEqual(len(THEME_IDS), len(themes))

        categories = list_theme_categories()
        expected_categories = {
            "Core",
            "Glow & Neon",
            "Professional",
            "High Contrast",
            "Retro",
            "Horror",
            "Terminal",
            "Minimalist",
            "Cartoonish",
            "Blackened",
            "Designer",
        }
        for cat in expected_categories:
            self.assertIn(cat, categories, f"Category '{cat}' missing from theme library")

    def test_theme_properties_and_stylesheets(self):
        for theme in list_themes():
            self.assertIn(theme.id, THEMES)
            self.assertTrue(theme.name, f"Theme {theme.id} missing name")
            self.assertIn(theme.variant, ("dark", "light"), f"Theme {theme.id} invalid variant")
            self.assertTrue(theme.category, f"Theme {theme.id} missing category")
            self.assertTrue(theme.description, f"Theme {theme.id} missing description")

            stylesheet = get_stylesheet(theme.id)
            self.assertIsInstance(stylesheet, str)
            self.assertGreater(len(stylesheet), 100)
            self.assertIn("QMainWindow", stylesheet)
            self.assertIn("QPlainTextEdit", stylesheet)
            self.assertIn("QPushButton#primaryButton", stylesheet)

    def test_highlighter_palettes_for_all_themes(self):
        required_keys = {"variable_fg", "heading", "role", "code", "error"}
        for tid in THEME_IDS:
            palette = get_highlighter_palette(tid)
            self.assertIsInstance(palette, dict, f"Highlighter palette for {tid} is not dict")
            for k in required_keys:
                self.assertIn(k, palette, f"Theme {tid} missing highlighter color {k}")
                self.assertTrue(palette[k].startswith("#"), f"Theme {tid} key {k} must start with #")

    def test_fallback_on_invalid_theme_id(self):
        fallback = get_theme("non_existent_theme_id")
        self.assertEqual(fallback.id, DEFAULT_THEME)

    def test_is_dark_and_is_light(self):
        self.assertTrue(is_dark_theme("midnight_dark"))
        self.assertFalse(is_light_theme("midnight_dark"))
        self.assertTrue(is_light_theme("midnight_light"))
        self.assertFalse(is_dark_theme("midnight_light"))

    def test_os_font_stacks(self):
        for cat in FONT_STACKS.keys():
            stack = get_font_stack(cat)
            self.assertIsInstance(stack, str)
            self.assertGreater(len(stack), 0)

            css = get_ui_font_css(cat, "14px")
            self.assertIn("font-family:", css)
            self.assertIn("font-size: 14px", css)


if __name__ == "__main__":
    unittest.main()
