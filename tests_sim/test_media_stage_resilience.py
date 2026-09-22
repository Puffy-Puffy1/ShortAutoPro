import os
import unittest
from unittest import mock

import media_acquisition_recovery as recovery
import media_stage_runtime as stage


class MediaStageResilienceTests(unittest.TestCase):
    def test_round_env_escalates_both_rescue_budgets(self):
        expected = [1, 2, 3, 4]
        for index, budget in enumerate(expected):
            env = stage.round_env(index)
            self.assertEqual(int(env["SAP_STOCK_RESCUE_MAX_QUERIES"]), budget)
            self.assertEqual(int(env["SAP_MUST_RESCUE_MAX_QUERIES"]), budget)

    def test_round_env_escalates_timeouts_bounded(self):
        first = stage.round_env(0)
        fourth = stage.round_env(3)
        self.assertLess(
            float(first["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
            float(fourth["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
        )
        self.assertLessEqual(
            float(fourth["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
            45.0,
        )

    def test_rescue_query_generator_can_return_eight_distinct_variants(self):
        queries = recovery._rescue_queries(
            "old sealed court record archive",
            ["court record", "wax seal"],
            assunto="Historic Case",
            segmento="investigators found a sealed archival record",
            visual_mode="document",
        )
        self.assertGreaterEqual(len(queries), 6)
        self.assertLessEqual(len(queries), 8)
        self.assertEqual(len(queries), len({q.casefold() for q in queries}))

    def test_individual_must_anchor_queries_are_added(self):
        queries = recovery._rescue_queries(
            "case files police documents",
            ["case files", "documents"],
            assunto="Case",
            segmento="archived investigation documents",
            visual_mode="document",
        )
        joined = "\n".join(queries).casefold()
        self.assertIn("case files", joined)
        self.assertIn("documents", joined)

    def test_recovery_version_incremented(self):
        self.assertEqual(recovery.VERSION, "1.9")

    def test_stage_does_not_abort_on_first_no_progress_contract(self):
        text = open("media_stage_runtime.py", encoding="utf-8").read()
        self.assertIn("ESCALATE_NEXT_ROUND", text)
        self.assertIn("STOP_BOUNDED_RECOVERY", text)
        self.assertIn("no_progress_rounds >= 2", text)
        self.assertIn("TWO_CONSECUTIVE_NO_PROGRESS_ROUNDS", text)
        self.assertNotIn("reason=NO_PROGRESS", text)
        self.assertIn('env_int("SAP_MEDIA_STAGE_ROUNDS", 3, 1, 4)', text)


if __name__ == "__main__":
    unittest.main()
