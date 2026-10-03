"""CI-level test suite for scripts/verify_provenance_comparison.py (CI-05)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_provenance_comparison


def create_mock_dist(directory: Path, source_commit: str, version: str = "0.8.0") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    file1 = directory / "index.html"
    file1.write_text("<html>PhaseFinder</html>", encoding="utf-8")

    meta = {
        "application": "PhaseFinder",
        "version": version,
        "sourceCommit": source_commit,
        "builtAt": "2026-09-08T12:00:00Z",
    }
    (directory / "build-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    manifest = {
        "version": 1,
        "files": [
            {
                "path": "index.html",
                "bytes": len(file1.read_bytes()),
                "sha256": hashlib.sha256(file1.read_bytes()).hexdigest(),
            },
            {
                "path": "build-metadata.json",
                "bytes": len((directory / "build-metadata.json").read_bytes()),
                "sha256": hashlib.sha256((directory / "build-metadata.json").read_bytes()).hexdigest(),
            },
        ],
    }
    (directory / "artifact-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    sbom = {
        "bomFormat": "CycloneDX",
        "components": [
            {"type": "library", "name": "vite", "version": "8.1.5"}
        ],
    }
    (directory / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")


class TestVerifyProvenanceComparison(unittest.TestCase):
    def test_compare_provenance_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            cand_dir = Path(tmpdir) / "cand"
            base_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            cand_sha = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

            create_mock_dist(base_dir, base_sha)
            create_mock_dist(cand_dir, cand_sha)

            res = verify_provenance_comparison.compare_provenance(
                base_dir, cand_dir, expected_base_ref=base_sha, expected_cand_ref=cand_sha
            )
            self.assertEqual(res["base"]["sourceCommit"], base_sha)
            self.assertEqual(res["candidate"]["sourceCommit"], cand_sha)
            self.assertEqual(res["base"]["files"], 2)
            self.assertEqual(res["candidate"]["files"], 2)

            report = verify_provenance_comparison.generate_markdown_report(res)
            self.assertIn("Build Provenance Comparison (CI-05)", report)
            self.assertIn("**Revisions Match Respective Checkouts:** ✅ Yes", report)

    def test_detects_overwritten_base_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            cand_dir = Path(tmpdir) / "cand"
            cand_sha = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

            # Simulate the bug: base build metadata carries candidate commit
            create_mock_dist(base_dir, cand_sha)
            create_mock_dist(cand_dir, cand_sha)

            with self.assertRaises(ValueError) as ctx:
                verify_provenance_comparison.compare_provenance(
                    base_dir,
                    cand_dir,
                    expected_base_ref="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    expected_cand_ref=cand_sha,
                )
            self.assertIn("Base provenance sourceCommit", str(ctx.exception))
            self.assertIn("CRITICAL (CI-05)", str(ctx.exception))

    def test_detects_corrupted_file_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_dir = Path(tmpdir) / "dist"
            create_mock_dist(dist_dir, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

            # Corrupt index.html
            (dist_dir / "index.html").write_text("<html>tampered</html>", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                verify_provenance_comparison.verify_dist_integrity(dist_dir)
            self.assertIn("Hash mismatch", str(ctx.exception))

    def test_cli_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            cand_dir = Path(tmpdir) / "cand"
            summary = Path(tmpdir) / "summary.md"
            base_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            cand_sha = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

            create_mock_dist(base_dir, base_sha)
            create_mock_dist(cand_dir, cand_sha)

            cmd = [
                sys.executable,
                str(ROOT / "scripts/verify_provenance_comparison.py"),
                str(base_dir),
                str(cand_dir),
                "--base-ref",
                base_sha,
                "--candidate-ref",
                cand_sha,
                "--summary-file",
                str(summary),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.assertIn("Build Provenance Comparison (CI-05)", proc.stdout)
            self.assertTrue(summary.exists())


if __name__ == "__main__":
    unittest.main()
