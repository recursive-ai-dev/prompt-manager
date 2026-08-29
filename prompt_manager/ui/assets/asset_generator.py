"""Asset & Accent Generation Pipeline with Background Removal for Theme Embellishments.

Generates and post-processes atmospheric SVG/PNG accents, glowing borders,
textures, and decorative icons for the expanded theme library.
"""

from __future__ import annotations

import io
import math
import os
from pathlib import Path
import urllib.parse
import urllib.request
from typing import Optional, Tuple

ACCENTS_DIR = Path(__file__).parent / "theme_accents"


class BackgroundRemover:
    """Removes solid, gradient, or near-uniform backgrounds from image byte streams."""

    @staticmethod
    def remove_color_background(
        image_bytes: bytes,
        target_color: Tuple[int, int, int] = (255, 255, 255),
        tolerance: int = 40,
        feather: int = 15,
    ) -> bytes:
        """Remove background matching target RGB color within tolerance."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            pixels = img.load()
            width, height = img.size
            tr, tg, tb = target_color

            for x in range(width):
                for y in range(height):
                    r, g, b, a = pixels[x, y]
                    dist = math.sqrt((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2)
                    if dist < tolerance:
                        pixels[x, y] = (r, g, b, 0)
                    elif dist < tolerance + feather:
                        alpha_factor = (dist - tolerance) / float(feather)
                        pixels[x, y] = (r, g, b, int(a * alpha_factor))

            out_buf = io.BytesIO()
            img.save(out_buf, format="PNG")
            return out_buf.getvalue()
        except Exception:
            # Fallback if Pillow not installed or corrupt bytes
            return image_bytes


class AccentGenerator:
    """Generates vector SVG and stylized PNG theme accents."""

    @classmethod
    def ensure_accents_dir(cls) -> Path:
        ACCENTS_DIR.mkdir(parents=True, exist_ok=True)
        return ACCENTS_DIR

    @classmethod
    def generate_all_theme_assets(cls) -> None:
        """Generate vector SVG assets for theme styles."""
        cls.ensure_accents_dir()

        # 1. Cyberpunk / Synthwave Glow Border Accent
        cls._write_svg(
            "glow_border_cyan.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <filter id="cyanGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <rect x="10" y="10" width="80" height="80" rx="8" fill="none" stroke="#00f0ff" stroke-width="3" filter="url(#cyanGlow)" />
</svg>""",
        )

        # 2. Synthwave Neon Pink Glow
        cls._write_svg(
            "glow_border_magenta.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <filter id="pinkGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <rect x="10" y="10" width="80" height="80" rx="8" fill="none" stroke="#ff007f" stroke-width="3" filter="url(#pinkGlow)" />
</svg>""",
        )

        # 3. Retro 80s Scanlines Overlay Pattern
        cls._write_svg(
            "scanlines_crt.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4">
  <rect width="4" height="2" fill="#000000" opacity="0.18" />
  <rect y="2" width="4" height="2" fill="transparent" />
</svg>""",
        )

        # 4. Art Deco Geometric Divider Accent
        cls._write_svg(
            "art_deco_divider.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 24" width="200" height="24">
  <path d="M 10 12 L 80 12 L 90 4 L 100 12 L 110 4 L 120 12 L 190 12" stroke="#d4af37" stroke-width="2" fill="none"/>
  <polygon points="100,0 106,12 100,24 94,12" fill="#d4af37"/>
</svg>""",
        )

        # 5. Bauhaus Geometric Composition
        cls._write_svg(
            "bauhaus_badge.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40">
  <circle cx="20" cy="20" r="16" fill="#1e448b" />
  <polygon points="20,8 32,30 8,30" fill="#de3831" />
  <rect x="15" y="15" width="10" height="10" fill="#f2a900" />
</svg>""",
        )

        # 6. Horror / Eldritch Sigil Corner
        cls._write_svg(
            "horror_corner.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50" width="50" height="50">
  <path d="M 5 5 L 45 5 L 45 10 L 10 10 L 10 45 L 5 45 Z" fill="#881337" opacity="0.8"/>
  <circle cx="10" cy="10" r="3" fill="#be123c"/>
</svg>""",
        )

        # 7. Black Metal Atmospheric Rune
        cls._write_svg(
            "black_metal_sigil.svg",
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60" width="60" height="60">
  <line x1="30" y1="5" x2="30" y2="55" stroke="#94a3b8" stroke-width="2"/>
  <line x1="30" y1="20" x2="15" y2="35" stroke="#94a3b8" stroke-width="2"/>
  <line x1="30" y1="20" x2="45" y2="35" stroke="#94a3b8" stroke-width="2"/>
  <line x1="30" y1="40" x2="18" y2="52" stroke="#64748b" stroke-width="1.5"/>
  <line x1="30" y1="40" x2="42" y2="52" stroke="#64748b" stroke-width="1.5"/>
</svg>""",
        )

    @classmethod
    def _write_svg(cls, filename: str, content: str) -> Path:
        target = ACCENTS_DIR / filename
        target.write_text(content, encoding="utf-8")
        return target

    @classmethod
    def fetch_ai_theme_stamp(cls, prompt: str, filename: str) -> Optional[Path]:
        """Fetch AI generated stamp from free endpoint and process background to transparency."""
        cls.ensure_accents_dir()
        encoded = urllib.parse.quote(f"icon logo vector graphic on pure white background, {prompt}")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=256&height=256&nologo=true"

        req = urllib.request.Request(url, headers={"User-Agent": "PromptManager/0.2.0"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_img = resp.read()
                transparent_png = BackgroundRemover.remove_color_background(
                    raw_img, target_color=(255, 255, 255), tolerance=45, feather=20
                )
                target_path = ACCENTS_DIR / filename
                target_path.write_bytes(transparent_png)
                return target_path
        except Exception:
            return None


# Generate vector assets upon import
AccentGenerator.generate_all_theme_assets()
