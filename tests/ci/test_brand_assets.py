"""BRAND-01 / AUDIT-015: verify brand asset integrity, minimum size, and clearspace rules."""
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]

def get_png_dimensions(path: Path):
    with open(path, "rb") as f:
        sig = f.read(8)
        assert sig == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature for {path}"
        length, chunk_type = struct.unpack(">I4s", f.read(8))
        assert chunk_type == b"IHDR", f"Expected IHDR chunk in {path}"
        width, height = struct.unpack(">II", f.read(8))
        return width, height

class TestBrandAssets(unittest.TestCase):
    def test_logo_dimensions_and_integrity(self):
        logo_path = ROOT / "assets" / "img" / "logo.png"
        self.assertTrue(logo_path.exists(), "Master logo asset missing: assets/img/logo.png")
        width, height = get_png_dimensions(logo_path)
        self.assertEqual(width, 1593, "Master logo width must be 1593px")
        self.assertEqual(height, 331, "Master logo height must be 331px")
        aspect_ratio = width / height
        self.assertAlmostEqual(aspect_ratio, 4.8127, places=3)

    def test_favicon_and_touch_icon_assets(self):
        favicon_dir = ROOT / "assets" / "img" / "favicon"
        expected_icons = {
            "favicon-16x16.png": (16, 16),
            "favicon-32x32.png": (32, 32),
            "apple-touch-icon.png": (180, 180),
            "android-chrome-192x192.png": (192, 192),
            "android-chrome-512x512.png": (512, 512),
        }
        for filename, (exp_w, exp_h) in expected_icons.items():
            icon_path = favicon_dir / filename
            self.assertTrue(icon_path.exists(), f"Favicon asset missing: {filename}")
            w, h = get_png_dimensions(icon_path)
            self.assertEqual((w, h), (exp_w, exp_h), f"Unexpected dimensions for {filename}")

    def test_brand_surfaces_css_rules(self):
        # Surface 1: Main Application Header
        layout_css = (ROOT / "css" / "layout.css").read_text(encoding="utf-8")
        self.assertIn(".site_logo", layout_css)
        site_logo_match = re.search(r"\.site_logo\s*\{([^}]+)\}", layout_css)
        self.assertIsNotNone(site_logo_match, "Missing .site_logo rule block in css/layout.css")
        site_logo_body = site_logo_match.group(1)
        self.assertIn("260px", site_logo_body, ".site_logo must specify max width 260px")

        # Surface 2: Help Center Header
        help_css = (ROOT / "css" / "help.css").read_text(encoding="utf-8")
        self.assertIn(".help_header_logo", help_css)
        help_logo_match = re.search(r"\.help_header_logo\s*\{([^}]+)\}", help_css)
        self.assertIsNotNone(help_logo_match, "Missing .help_header_logo rule block in css/help.css")
        help_logo_body = help_logo_match.group(1)
        height_match = re.search(r"height:\s*(\d+)px", help_logo_body)
        self.assertIsNotNone(height_match, ".help_header_logo must have explicit pixel height")
        rendered_height = int(height_match.group(1))
        self.assertGreaterEqual(rendered_height, 28, "Help header logo must be >= minimum safe height 28px")

        # Clearspace in Help Header: verify padding and gap >= 12px
        help_header_match = re.search(r"\.help_header\s*\{([^}]+)\}", help_css)
        self.assertIsNotNone(help_header_match, "Missing .help_header rule block in css/help.css")
        help_header_body = help_header_match.group(1)
        gap_match = re.search(r"gap:\s*(\d+)px", help_header_body)
        self.assertIsNotNone(gap_match, ".help_header must have flex gap")
        self.assertGreaterEqual(int(gap_match.group(1)), 12, "Clearspace gap must be >= 12px")

    def test_guidelines_documentation_presence(self):
        guidelines_path = ROOT / "docs" / "brand-guidelines.md"
        readme_path = ROOT / "assets" / "img" / "README.md"
        self.assertTrue(guidelines_path.exists(), "docs/brand-guidelines.md must exist")
        self.assertTrue(readme_path.exists(), "assets/img/README.md must exist")
        content = guidelines_path.read_text(encoding="utf-8")
        self.assertIn("28 CSS pixels", content)
        self.assertIn("Clearspace", content)

if __name__ == "__main__":
    unittest.main()
