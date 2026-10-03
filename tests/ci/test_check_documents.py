"""DOC-05: Documentation validation misses nested audit and plan documents.

Tests that:
1. scripts/check_documents.py passes cleanly on current repository state.
2. Recursive link validation covers nested documents under docs/plans/ and docs/audits/.
3. Tracker freshness and parser verification are wired into check_documents.py.
4. Archive exceptions explicitly handle historical source-line references in docs/archive/
   without hiding broken navigation.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CHECK_DOCS_SCRIPT = ROOT / "scripts/check_documents.py"


class TestCheckDocuments(unittest.TestCase):
    def test_check_documents_passes_cleanly(self):
        result = subprocess.run(
            ["python3", str(CHECK_DOCS_SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"check_documents failed:\n{result.stderr}\n{result.stdout}")
        self.assertIn("Document checks passed:", result.stdout)
        self.assertIn("active Markdown files", result.stdout)
        self.assertIn("tracker freshness and parser", result.stdout)

    def test_detects_broken_link_in_nested_doc(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_documents

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_plan = ROOT / "docs/plans/nonexistent_test_probe.md"
            try:
                nested_plan.write_text("See [missing](nonexistent_target_file.md)", encoding="utf-8")
                errors = []
                with patch.object(check_documents, "errors", errors):
                    check_documents.check_target(nested_plan, "nonexistent_target_file.md", is_archive=False)
                self.assertTrue(any("missing local target" in err for err in errors))
            finally:
                if nested_plan.exists():
                    nested_plan.unlink()

    def test_explicit_archive_exceptions(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_documents

        archive_doc = ROOT / "docs/archive/test_doc.md"

        # Line number fragment to existing HTML should be accepted in archive doc
        errors = []
        with patch.object(check_documents, "errors", errors):
            check_documents.check_target(archive_doc, "../../index.html#L222", is_archive=True)
        self.assertEqual(errors, [], "Historical line anchor in archive should be accepted")

        # But broken file navigation must fail even in archive
        errors = []
        with patch.object(check_documents, "errors", errors):
            check_documents.check_target(archive_doc, "totally_missing_page.md", is_archive=True)
        self.assertTrue(any("missing local target" in err for err in errors), "Broken file link in archive must be caught")

    def test_validation_help_pages_wired_and_shipped(self):
        """CLEAN-04: Confirm deep validation help pages are wired in vite build and navigation."""
        vite_config = (ROOT / "vite.config.js").read_text(encoding="utf-8")
        help_index = (ROOT / "help/index.html").read_text(encoding="utf-8")
        accuracy_page = (ROOT / "help/help-cell-cycle-accuracy.html").read_text(encoding="utf-8")
        math_check_page = (ROOT / "help/help-cell-cycle-math-check.html").read_text(encoding="utf-8")
        modeling_page = (ROOT / "help/help-modeling.html").read_text(encoding="utf-8")

        for page in ["djf-model-validation.html", "tool_validation.html", "result_validation.html"]:
            self.assertTrue((ROOT / "help" / page).exists(), f"Validation page {page} must exist in help/")
            self.assertIn(page, vite_config, f"Validation page {page} must be registered in vite.config.js rollup input")
            self.assertIn(page, help_index, f"Validation page {page} must be linked in help/index.html")

        # Confirm cross-links from related user guides
        self.assertIn("tool_validation.html", accuracy_page)
        self.assertIn("result_validation.html", accuracy_page)
        self.assertIn("djf-model-validation.html", math_check_page)
        self.assertIn("djf-model-validation.html", modeling_page)


if __name__ == "__main__":
    unittest.main()
