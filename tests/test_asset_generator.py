"""Tests for BackgroundRemover and AccentGenerator asset pipeline."""

import io
import unittest
from prompt_manager.ui.assets.asset_generator import AccentGenerator, BackgroundRemover, ACCENTS_DIR


class TestAssetGenerator(unittest.TestCase):

    def test_svg_accents_generated(self):
        AccentGenerator.generate_all_theme_assets()
        self.assertTrue(ACCENTS_DIR.exists())

        expected_files = [
            "glow_border_cyan.svg",
            "glow_border_magenta.svg",
            "scanlines_crt.svg",
            "art_deco_divider.svg",
            "bauhaus_badge.svg",
            "horror_corner.svg",
            "black_metal_sigil.svg",
        ]
        for f in expected_files:
            file_path = ACCENTS_DIR / f
            self.assertTrue(file_path.exists(), f"Asset {f} was not generated")
            content = file_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("<svg"))
            self.assertTrue(content.strip().endswith("</svg>"))

    def test_background_remover_with_synthetic_image(self):
        try:
            from PIL import Image
            # Create a 4x4 image: 2 white pixels, 2 black pixels
            img = Image.new("RGB", (2, 2), color=(255, 255, 255))
            img.putpixel((0, 0), (0, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            input_bytes = buf.getvalue()

            result = BackgroundRemover.remove_color_background(
                input_bytes, target_color=(255, 255, 255), tolerance=10, feather=5
            )
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)

            # Check that output is a valid RGBA image where white became transparent
            out_img = Image.open(io.BytesIO(result))
            self.assertEqual(out_img.mode, "RGBA")
            # Black pixel should be opaque
            self.assertEqual(out_img.getpixel((0, 0))[3], 255)
            # White pixel should be transparent
            self.assertEqual(out_img.getpixel((1, 1))[3], 0)
        except ImportError:
            pass


if __name__ == "__main__":
    unittest.main()
