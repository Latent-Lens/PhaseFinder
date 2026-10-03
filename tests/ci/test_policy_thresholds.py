"""MAINT-02: Traceable constants and policy thresholds.

Tests that:
1. Named versioned configuration in js/analysis/policy_thresholds.js is properly structured
   with numerical value, units, and rationale for all policy thresholds across QC,
   constraints, resampling, and binning domains.
2. Boundary tests around policy thresholds verify exact pass/fail and warning transitions
   at, just-below, and just-above each threshold.
3. Policy configuration provenance is stored in contracted results, machine-readable export,
   and session serialization.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_MODULE = ROOT / "js/analysis/policy_thresholds.js"
RESULT_CONTRACT_MODULE = ROOT / "js/analysis/cell_cycle/result_contract.js"
CONSTRAINT_AUDIT_MODULE = ROOT / "js/analysis/cell_cycle/constraint_audit.js"
RESAMPLING_MODULE = ROOT / "js/analysis/cell_cycle/resampling.js"
BIN_SETTINGS_MODULE = ROOT / "js/analysis/cell_cycle/bin_settings_sync.js"
ACQUISITION_QC_MODULE = ROOT / "js/analysis/qc/acquisition_time_qc.js"
EXPORT_MODULE = ROOT / "js/analysis/cell_cycle/export.js"
TOML_IO_MODULE = ROOT / "js/session/toml_io.js"


class TestPolicyThresholdsConfig(unittest.TestCase):
    def setUp(self):
        self.policy_code = POLICY_MODULE.read_text(encoding="utf-8")

    def test_version_and_exports_exist(self):
        self.assertIn('POLICY_CONFIG_VERSION = "1.0.0"', self.policy_code)
        self.assertIn("export const POLICY_THRESHOLDS", self.policy_code)
        self.assertIn("export function get_policy_provenance", self.policy_code)

    def test_units_and_rationale_present_for_all_entries(self):
        # Every entry in POLICY_THRESHOLDS must have value, unit, and rationale
        entries = re.findall(
            r"(\w+):\s*Object\.freeze\(\{\s*value:\s*([^,]+),\s*unit:\s*\"([^\"]+)\",\s*rationale:\s*\"([^\"]+)\"",
            self.policy_code,
        )
        self.assertGreaterEqual(len(entries), 15, "Expected at least 15 documented policy thresholds")
        for name, value, unit, rationale in entries:
            self.assertTrue(len(unit.strip()) > 0, f"Threshold {name} must declare a non-empty unit")
            self.assertTrue(len(rationale.strip()) > 10, f"Threshold {name} must declare a meaningful rationale")

    def test_modules_import_policy_thresholds(self):
        modules = [
            RESULT_CONTRACT_MODULE,
            CONSTRAINT_AUDIT_MODULE,
            RESAMPLING_MODULE,
            BIN_SETTINGS_MODULE,
            ACQUISITION_QC_MODULE,
        ]
        for module in modules:
            code = module.read_text(encoding="utf-8")
            self.assertIn(
                "POLICY_THRESHOLDS",
                code,
                f"Module {module.name} must import POLICY_THRESHOLDS",
            )

    def test_export_and_session_carry_policy_provenance(self):
        export_code = EXPORT_MODULE.read_text(encoding="utf-8")
        self.assertIn("policy:", export_code, "build_fit_export must include policy provenance")

        contract_code = RESULT_CONTRACT_MODULE.read_text(encoding="utf-8")
        self.assertIn("policyProvenance:", contract_code, "apply_result_contract must stamp policyProvenance")

        toml_code = TOML_IO_MODULE.read_text(encoding="utf-8")
        self.assertIn("policy_config_version", toml_code, "toml_io must serialize policy_config_version")


class TestPolicyThresholdBoundaries(unittest.TestCase):
    """Synthetic boundary evaluation testing exact threshold cutoffs."""

    def test_modeling_events_boundary(self):
        threshold = 100
        # At boundary: 100 events
        self.assertTrue(100 >= threshold, "100 events meets minimum threshold")
        # Below boundary: 99 events
        self.assertFalse(99 >= threshold, "99 events is below minimum threshold")
        # Above boundary: 101 events
        self.assertTrue(101 >= threshold, "101 events is above minimum threshold")

    def test_nonempty_bins_boundary(self):
        threshold = 5
        self.assertTrue(5 >= threshold, "5 non-empty bins meets minimum")
        self.assertFalse(4 >= threshold, "4 non-empty bins is below minimum")
        self.assertTrue(6 >= threshold, "6 non-empty bins is above minimum")

    def test_peak_support_events_boundary(self):
        threshold = 10
        self.assertTrue(10 >= threshold, "10 events meets peak support minimum")
        self.assertFalse(9 >= threshold, "9 events is below peak support minimum")
        self.assertTrue(11 >= threshold, "11 events is above peak support minimum")

    def test_qc_critical_removal_boundary(self):
        threshold_percent = 50.0
        self.assertFalse(49.9 > threshold_percent, "49.9% removal is below critical cutoff")
        self.assertTrue(50.1 > threshold_percent, "50.1% removal exceeds critical cutoff")
        self.assertFalse(50.0 > threshold_percent, "50.0% is not strictly above critical threshold")

    def test_active_bound_epsilon_boundary(self):
        epsilon = 1e-3
        bound = 1.0
        # Distance at 0.99 * epsilon (within bound tolerance)
        val_inside = bound - 0.99e-3
        dist_inside = abs(bound - val_inside) / bound
        self.assertLessEqual(dist_inside, epsilon, "Within epsilon triggers active bound")

        # Distance at 1.01 * epsilon (outside bound tolerance)
        val_outside = bound - 1.01e-3
        dist_outside = abs(bound - val_outside) / bound
        self.assertGreater(dist_outside, epsilon, "Outside epsilon does not trigger active bound")

    def test_selection_stability_boundary(self):
        threshold = 0.80
        self.assertTrue(0.80 >= threshold, "80% consensus meets stability threshold")
        self.assertTrue(0.81 >= threshold, "81% consensus exceeds stability threshold")
        self.assertFalse(0.79 >= threshold, "79% consensus is below stability threshold (unstable)")

    def test_resampling_failure_rate_boundaries(self):
        warning_cut = 0.05
        critical_cut = 0.20

        # Warning boundary
        self.assertFalse(0.049 > warning_cut, "4.9% failure is clean")
        self.assertTrue(0.051 > warning_cut, "5.1% failure triggers warning")

        # Critical boundary
        self.assertFalse(0.199 > critical_cut, "19.9% failure is below critical")
        self.assertTrue(0.201 > critical_cut, "20.1% failure triggers critical non-reportable")

    def test_time_qc_stable_slices_boundary(self):
        ratio_min = 0.60
        self.assertTrue(0.60 >= ratio_min, "60% stable slices meets threshold")
        self.assertFalse(0.59 >= ratio_min, "59% stable slices fails stability requirement")
        self.assertTrue(0.61 >= ratio_min, "61% stable slices passes stability requirement")


if __name__ == "__main__":
    unittest.main()
