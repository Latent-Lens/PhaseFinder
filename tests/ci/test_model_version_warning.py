"""The model release check warns, without blocking, on missing version notes."""

import subprocess
import tempfile
import unittest
from pathlib import Path


CHECK = Path(__file__).resolve().parents[2] / "scripts" / "check-model-version.cjs"


class ModelVersionWarningTest(unittest.TestCase):
    def test_warns_until_model_version_and_changelog_entry_are_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "js/analysis/cell_cycle/models/sample.js"
            model.parent.mkdir(parents=True)
            model.write_text('export const sample = {\n  version: "1.0.0",\n};\n')
            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
            def check():
                return subprocess.run(["node", str(CHECK)], cwd=root, check=True,
                                      capture_output=True, text=True).stderr
            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            git("add", ".")
            git("commit", "-qm", "baseline")
            model.write_text(model.read_text() + "// changed math\n")
            self.assertIn("without a model-version bump", check())
            self.assertIn("without a CHANGELOG.md entry", check())
            model.write_text(model.read_text().replace('"1.0.0"', '"1.1.0"'))
            (root / "CHANGELOG.md").write_text("## [Unreleased]\n\n- Changed sample model.\n")
            self.assertEqual(check(), "")
            git("add", ".")
            git("commit", "-qm", "model and notes")
            self.assertEqual(check(), "")


if __name__ == "__main__":
    unittest.main()
