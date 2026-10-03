"""Focused checks for the local FlowJo comparison contract."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowjo_cross_tool_report import render
from validation_tests import FLOWJO_QC_MATRIX, fit_model_flowjo, score_djf


class FlowJoScoringTests(unittest.TestCase):
    def test_raw_and_rescaled_scores_are_distinct(self):
        fitted = {"phaseFractions": {"g1": .23, "s": .28, "g2": .49},
                  "parameters": {"g1Mean": 170, "g2Mean": 340}}
        reference = {"g1_fraction": .20, "s_fraction": .25, "g2_fraction": .45,
                     "g1_mean": 170, "g2_mean": 340, "g2_g1_ratio": 2}
        tolerance = {"phase_fraction_abs_pp": {"g1": 2, "s": 2, "g2": 2},
                     "peak_mean_rel": .03, "g2_g1_ratio_abs": .06}
        score = score_djf(fitted, reference, tolerance)
        self.assertEqual(score["passFailBasis"], "raw")
        self.assertFalse(score["all_pass"])
        self.assertTrue(score["rescaledAllPass"])
        self.assertFalse(score["phaseAllPass"])
        self.assertTrue(score["rescaledPhaseAllPass"])
        self.assertAlmostEqual(score["referenceFractionTotal"], .90)

    def test_modes_and_private_report(self):
        self.assertEqual([row[3] for row in FLOWJO_QC_MATRIX].count("product"), 1)
        self.assertEqual([row[3] for row in FLOWJO_QC_MATRIX].count("matched"), 1)
        payload = {"results": [{"strain": "sample<&>", "configs": [
            {"label": "No QC (diagnostic)", "status": "ERROR", "stage": "fit:dean_jett_fox",
             "error": "timed out <wait>", "scores": {}, "fitAudit": {}},
            {"label": "Product default", "status": "PASS", "mode": "product",
             "eventsRetained": 90, "scores": {"dean_jett_fox": {
                 "phases": {phase: {"ours": .3, "ref": .2} for phase in ("g1", "s", "g2")},
                 "all_pass": False, "rescaledAllPass": True}},
             "fitAudit": {"dean_jett_fox": {"warnings": [
                 {"code": "overdispersed_fit", "severity": "warning"}]}}},
        ]}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "comparison.json"
            path.write_text(json.dumps(payload))
            report = render([path])
        self.assertIn("sample&lt;&amp;&gt;", report)
        self.assertIn("timed out &lt;wait&gt;", report)
        self.assertIn("fit:dean_jett_fox", report)
        self.assertIn("overdispersed_fit (warning)", report)
        self.assertIn("Product default", report)
        self.assertEqual(report.count("<td>"), 22)

    def test_fit_refusal_is_reported_without_waiting_for_a_result_key(self):
        page = MagicMock()
        page.evaluate.side_effect = [[], None]
        page.locator.return_value.inner_text.return_value = "critical QC loss needs acknowledgement"
        with patch("validation_tests.wait_for_overlay_hidden"):
            with self.assertRaisesRegex(RuntimeError, "critical QC loss"):
                fit_model_flowjo(page, "sample", "dean_jett_fox")
        self.assertIn("cell_cycle_fit_status", page.wait_for_function.call_args_list[-1].args[0])


if __name__ == "__main__":
    unittest.main()
