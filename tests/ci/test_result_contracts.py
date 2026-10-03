"""MAINT-01: Typed result contracts.

Statically asserts that:
1. js/analysis/cell_cycle/result_contract.js exports the canonical contract version,
   validation, and assertion utilities.
2. JSDoc @typedef definitions exist for all core domain shapes:
   PhaseFractions, PeakRegions, ModelComponent, ModelDiagnostics, ResultReasonIssue,
   QualityWarning, QCOutcome, PreflightBundle, NormalizedModelResult,
   ContractedModelResult, ActiveModelResult.
3. js/analysis/cell_cycle/export.js defines typed export payloads (FitExportPayload)
   referencing contracted result types.
4. All registered cell-cycle models (dean_jett, dean_jett_fox, watson_pragmatic,
   watson_classic, cloccs) implement normalizeResult methods conforming to the contract boundary.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "js"
RESULT_CONTRACT_FILE = ROOT / "js/analysis/cell_cycle/result_contract.js"
EXPORT_FILE = ROOT / "js/analysis/cell_cycle/export.js"
MODELS_DIR = ROOT / "js/analysis/cell_cycle/models"

REGISTERED_MODEL_FILES = {
    "dean_jett.js",
    "dean_jett_fox.js",
    "watson_pragmatic.js",
    "watson_classic.js",
    "cloccs.js",
}


class TestResultContractsStatic(unittest.TestCase):
    def setUp(self):
        self.contract_code = RESULT_CONTRACT_FILE.read_text(encoding="utf-8")
        self.export_code = EXPORT_FILE.read_text(encoding="utf-8")

    def test_result_contract_version_and_exports(self):
        self.assertIn("RESULT_CONTRACT_VERSION = 2", self.contract_code)
        expected_exports = [
            "RESULT_CONTRACT_VERSION",
            "apply_result_contract",
            "validate_contracted_result_shape",
            "assert_contracted_result_shape",
            "assert_result_contracted",
            "is_contracted_result",
        ]
        for exp in expected_exports:
            pattern = rf"\bexport\s+(?:const|function)\s+{exp}\b"
            self.assertTrue(
                re.search(pattern, self.contract_code),
                f"Expected {exp} to be exported in result_contract.js",
            )

    def test_jsdoc_typedefs_in_result_contract(self):
        required_typedefs = [
            "PhaseFractions",
            "PeakRegionRange",
            "PeakRegions",
            "ModelComponent",
            "ModelDiagnostics",
            "ResultReasonIssue",
            "QualityWarning",
            "QCOutcome",
            "PreflightBundle",
            "NormalizedModelResult",
            "ContractedModelResult",
            "ActiveModelResult",
        ]
        for typedef in required_typedefs:
            pattern = rf"@typedef\s*\{{.*?}}\s*{typedef}\b"
            self.assertTrue(
                re.search(pattern, self.contract_code, re.DOTALL),
                f"Missing @typedef for {typedef} in result_contract.js",
            )

    def test_export_jsdoc_typedefs(self):
        self.assertTrue(
            re.search(r"@typedef\s*\{.*?\}\s*FitExportPayload\b", self.export_code, re.DOTALL),
            "Missing @typedef for FitExportPayload in export.js",
        )
        self.assertIn("ContractedModelResult", self.export_code)

    def test_models_normalize_results(self):
        for filename in REGISTERED_MODEL_FILES:
            model_file = MODELS_DIR / filename
            self.assertTrue(model_file.exists(), f"Model file {filename} does not exist")
            code = model_file.read_text(encoding="utf-8")
            self.assertTrue(
                "normalizeResult" in code,
                f"Model file {filename} must define or export normalizeResult",
            )


if __name__ == "__main__":
    unittest.main()
