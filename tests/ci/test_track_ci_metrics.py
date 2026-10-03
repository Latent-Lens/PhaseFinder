"""CI-level test suite for scripts/track_ci_metrics.py (TEST-02 box 6)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import track_ci_metrics


class TestTrackCIMetrics(unittest.TestCase):
    def test_parse_iso_datetime(self):
        dt = track_ci_metrics.parse_iso_datetime("2026-09-08T12:30:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.minute, 30)

        dt_offset = track_ci_metrics.parse_iso_datetime("2026-09-08T08:30:00-04:00")
        self.assertIsNotNone(dt_offset)

        self.assertIsNone(track_ci_metrics.parse_iso_datetime(None))
        self.assertIsNone(track_ci_metrics.parse_iso_datetime("invalid-date"))

    def test_analyze_ci_durations_and_flakes(self):
        sample_runs = [
            {
                "databaseId": 101,
                "workflowName": "Build website",
                "headSha": "commit1",
                "status": "completed",
                "conclusion": "failure",
                "startedAt": "2026-09-08T10:00:00Z",
                "updatedAt": "2026-09-08T10:01:00Z",
            },
            {
                "databaseId": 102,
                "workflowName": "Build website",
                "headSha": "commit1",
                "status": "completed",
                "conclusion": "success",
                "startedAt": "2026-09-08T10:02:00Z",
                "updatedAt": "2026-09-08T10:03:00Z",
            },
            {
                "databaseId": 103,
                "workflowName": "Browser compatibility",
                "headSha": "commit2",
                "status": "completed",
                "conclusion": "success",
                "startedAt": "2026-09-08T10:00:00Z",
                "updatedAt": "2026-09-08T10:05:00Z",
            },
        ]
        res = track_ci_metrics.analyze_ci_durations_and_flakes(sample_runs)
        self.assertEqual(res["total_runs_inspected"], 3)
        self.assertEqual(res["completed_runs"], 3)
        self.assertEqual(res["success_count"], 2)
        self.assertEqual(res["failure_count"], 1)
        self.assertEqual(res["failure_rate_pct"], 33.3)
        self.assertEqual(res["flaky_commits_detected"], 1)
        self.assertEqual(res["flake_rate_pct"], 50.0)

        bw = res["workflow_durations"]["Build website"]
        self.assertEqual(bw["count"], 2)
        self.assertEqual(bw["mean_seconds"], 60.0)
        self.assertEqual(bw["min_seconds"], 60.0)
        self.assertEqual(bw["max_seconds"], 60.0)

        bc = res["workflow_durations"]["Browser compatibility"]
        self.assertEqual(bc["count"], 1)
        self.assertEqual(bc["mean_seconds"], 300.0)

    def test_analyze_browser_failures(self):
        sample_runs = [
            {"databaseId": 201, "workflowName": "Browser compatibility"}
        ]
        sample_jobs = {
            "201": [
                {"name": "Linux / chromium", "conclusion": "success"},
                {"name": "Linux / firefox", "conclusion": "failure"},
                {"name": "Linux / webkit", "conclusion": "failure"},
                {"name": "windows-latest / edge", "conclusion": "failure"},
                {"name": "ubuntu-latest / brave", "conclusion": "success"},
            ]
        }
        with tempfile.TemporaryDirectory() as empty_results:
            browsers = track_ci_metrics.analyze_browser_failures(
                sample_runs,
                offline_sample={"jobs": sample_jobs},
                results_dir=Path(empty_results),
            )
            self.assertEqual(browsers["chromium"]["passed"], 1)
            self.assertEqual(browsers["chromium"]["failed"], 0)
            self.assertEqual(browsers["chromium"]["pass_rate_pct"], 100.0)

            self.assertEqual(browsers["firefox"]["passed"], 0)
            self.assertEqual(browsers["firefox"]["failed"], 1)
            self.assertEqual(browsers["firefox"]["pass_rate_pct"], 0.0)

            self.assertEqual(browsers["edge"]["failed"], 1)
            self.assertEqual(browsers["brave"]["passed"], 1)

    def test_analyze_artifact_sizes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist = Path(tmpdir)
            manifest = {
                "files": [
                    {"path": "assets/main.js", "bytes": 1000},
                    {"path": "assets/main.css", "bytes": 500},
                    {"path": "assets/logo.png", "bytes": 2000},
                    {"path": "index.html", "bytes": 300},
                ]
            }
            (dist / "artifact-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            res = track_ci_metrics.analyze_artifact_sizes(dist)
            self.assertTrue(res["manifest_present"])
            self.assertEqual(res["file_count"], 4)
            self.assertEqual(res["total_bytes"], 3800)
            self.assertEqual(res["js_bytes"], 1000)
            self.assertEqual(res["css_bytes"], 500)
            self.assertEqual(res["images_bytes"], 2000)
            self.assertTrue(res["within_budget"])

    def test_analyze_benchmark_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bdir = Path(tmpdir)
            b1 = {
                "models": [
                    {"modelId": "dean_jett", "maxAbsoluteErrorPercentagePoints": 1.0, "converged": True},
                    {"modelId": "watson_pragmatic", "maxAbsoluteErrorPercentagePoints": 2.0, "converged": True},
                ]
            }
            b2 = {
                "models": [
                    {"modelId": "dean_jett", "maxAbsoluteErrorPercentagePoints": 1.05, "converged": True},
                    {"modelId": "watson_pragmatic", "maxAbsoluteErrorPercentagePoints": 2.20, "converged": True},
                ]
            }
            (bdir / "synthetic_fcs_benchmark_20260101-100000.json").write_text(json.dumps(b1), encoding="utf-8")
            (bdir / "synthetic_fcs_benchmark_20260101-110000.json").write_text(json.dumps(b2), encoding="utf-8")

            res = track_ci_metrics.analyze_benchmark_drift(bdir, max_drift_pp=0.15)
            self.assertEqual(res["benchmarks_found"], 2)
            self.assertTrue(res["drift_detected"])  # watson_pragmatic drifted by +0.20 > 0.15
            self.assertFalse(res["models"]["dean_jett"]["exceeded_drift_limit"])
            self.assertTrue(res["models"]["watson_pragmatic"]["exceeded_drift_limit"])

    def test_cli_invocation_offline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = Path(tmpdir) / "sample.json"
            json_out = Path(tmpdir) / "metrics.json"
            summary_out = Path(tmpdir) / "summary.md"

            sample_data = {
                "runs": [
                    {
                        "databaseId": 501,
                        "workflowName": "Build website",
                        "status": "completed",
                        "conclusion": "success",
                        "startedAt": "2026-09-08T10:00:00Z",
                        "updatedAt": "2026-09-08T10:00:30Z",
                    }
                ],
                "jobs": {
                    "501": [{"name": "Vite production build", "conclusion": "success"}]
                },
            }
            sample_file.write_text(json.dumps(sample_data), encoding="utf-8")

            cmd = [
                sys.executable,
                str(ROOT / "scripts/track_ci_metrics.py"),
                "--offline-sample",
                str(sample_file),
                "--json-output",
                str(json_out),
                "--summary-file",
                str(summary_out),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.assertIn("CI Trend & Quality Metrics (TEST-02)", proc.stdout)
            self.assertTrue(json_out.exists())
            self.assertTrue(summary_out.exists())

            saved_json = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertIn("durations", saved_json)
            self.assertIn("browsers", saved_json)
            self.assertIn("artifacts", saved_json)
            self.assertIn("benchmarks", saved_json)


if __name__ == "__main__":
    unittest.main()
