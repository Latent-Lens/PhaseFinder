#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "e2e" / "driving_code"))
from compatibility_evidence import aggregate


class CompatibilityEvidenceTests(unittest.TestCase):
    def test_aggregate_emits_exact_versions_and_requires_every_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = {
                "browser": "chromium",
                "browser_version": "150.0.1",
                "engine": "Chromium",
                "os": "Linux-6.0",
                "python": "3.12.9",
                "playwright": "1.61.0",
                "status": "passed",
                "date": "2026-07-30T12:00:00Z",
            }
            (root / "compatibility.json").write_text(json.dumps(record), encoding="utf-8")
            output = root / "matrix.md"
            aggregate(root, output, ["chromium"])
            table = output.read_text(encoding="utf-8")
            self.assertIn("150.0.1", table)
            self.assertIn("Linux-6.0", table)

            with self.assertRaises(SystemExit):
                aggregate(root, output, ["chromium", "firefox"])

    def test_informational_browser_does_not_fail_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chromium_record = {
                "browser": "chromium",
                "browser_version": "150.0.1",
                "engine": "Chromium",
                "os": "Linux-6.0",
                "python": "3.12.9",
                "playwright": "1.61.0",
                "status": "passed",
                "date": "2026-07-30T12:00:00Z",
            }
            brave_record = {
                "browser": "brave",
                "browser_version": "150.0.1",
                "engine": "Chromium",
                "os": "Linux-6.0",
                "python": "3.12.9",
                "playwright": "1.61.0",
                "status": "failed",
                "date": "2026-07-30T12:00:00Z",
            }
            (root / "dir1").mkdir()
            (root / "dir2").mkdir()
            (root / "dir1" / "compatibility.json").write_text(json.dumps(chromium_record), encoding="utf-8")
            (root / "dir2" / "compatibility.json").write_text(json.dumps(brave_record), encoding="utf-8")
            output = root / "matrix.md"
            # Gate expects only chromium; brave is informational and failed
            aggregate(root, output, ["chromium"])
            table = output.read_text(encoding="utf-8")
            self.assertIn("Informational browser runs (non-gating)", table)
            self.assertIn("brave", table)
            self.assertIn("FAILED", table)


if __name__ == "__main__":
    unittest.main()
