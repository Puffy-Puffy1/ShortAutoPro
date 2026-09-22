import os
import unittest
from unittest import mock

import media_must_priority as priority
import media_acquisition_recovery as recovery
import production_profiler


class ProductionContractBudgetTests(unittest.TestCase):
    def test_scene5_prioritizes_spoon_as_strict_anchor(self):
        result = priority.prioritize(
            ["hands", "wall", "spoon"],
            query="prisoner hands chipping concrete wall with makeshift spoon tool",
            visual_mode="object",
        )
        self.assertEqual(result["strict"], ["spoon"])
        self.assertCountEqual(result["context"], ["hands", "wall"])

    def test_scene6_prioritizes_ventilation_duct_over_tunnel(self):
        result = priority.prioritize(
            ["ventilation duct", "tunnel"],
            query="dark narrow prison ventilation duct pipe tunnel service corridor",
            visual_mode="environment",
        )
        self.assertEqual(result["strict"], ["ventilation duct"])
        self.assertEqual(result["context"], ["tunnel"])

    def test_documentary_mode_keeps_full_must_contract(self):
        result = priority.prioritize(
            ["investigators", "papers"],
            query="vintage FBI agents examining prison cell evidence papers",
            visual_mode="evidence",
        )
        self.assertEqual(result["strict"], ["investigators", "papers"])
        self.assertEqual(result["context"], [])

    def test_single_must_is_never_demoted(self):
        result = priority.prioritize(
            ["spoon"],
            query="metal spoon",
            visual_mode="object",
        )
        self.assertEqual(result["strict"], ["spoon"])

    def test_recovery_version_and_stock_budget_contract(self):
        text = open("media_acquisition_recovery.py", encoding="utf-8").read()
        self.assertIn('VERSION = "1.9"', text)
        self.assertIn("SAP_STOCK_RESCUE_MAX_QUERIES", text)
        self.assertIn('"4"', text)
        self.assertIn("SAP_STOCK_RESCUE_BUDGET=", text)

    def test_midia_reports_prioritized_contract(self):
        text = open("midia.py", encoding="utf-8").read()
        self.assertIn("SAP_MUST_CONTRACT=PRIORITIZED", text)
        self.assertIn("original_must_have", text)
        self.assertIn("context_must", text)

    def test_profiler_run_id_propagates_through_environment(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            rid = production_profiler.begin_run("abc", "run-xyz")
            self.assertEqual(rid, "run-xyz")
            self.assertEqual(os.environ.get("SAP_PROFILE_RUN_ID"), "run-xyz")
            production_profiler._ACTIVE_RUNS.clear()
            self.assertEqual(production_profiler.current_run_id("abc"), "run-xyz")

    def test_strict_guard_remains_fail_closed_for_effective_contract(self):
        text = open("media_strict_must_guard.py", encoding="utf-8").read()
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", text)
        self.assertIn("hits >= total", text)


if __name__ == "__main__":
    unittest.main()
