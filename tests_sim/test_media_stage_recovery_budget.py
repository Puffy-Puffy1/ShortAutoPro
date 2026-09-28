#!/usr/bin/env python3
"""Regression tests for Stage 6 provider/recovery timeout alignment."""

import os
import unittest


class MediaStageRecoveryBudgetTests(unittest.TestCase):
    def test_recovery_budget_gives_provider_controller_enough_time(self):
        import media_stage_runtime as runtime

        old_sid = runtime.SID
        try:
            runtime.SID = "test-timeout-alignment"
            first = runtime.round_env(0)
            second = runtime.round_env(1)
            third = runtime.round_env(2)

            self.assertEqual(first["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"], "10")
            self.assertEqual(second["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"], "12")
            self.assertEqual(third["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"], "12")

            self.assertEqual(first["SAP_WIKIMEDIA_SEARCH_DEADLINE"], "8")
            self.assertEqual(second["SAP_WIKIMEDIA_SEARCH_DEADLINE"], "10")
            self.assertEqual(third["SAP_WIKIMEDIA_SEARCH_DEADLINE"], "12")

            for env in (first, second, third):
                self.assertGreaterEqual(
                    int(env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]),
                    int(env["SAP_WIKIMEDIA_SEARCH_DEADLINE"]),
                )
            for env in (first, second, third):
                self.assertEqual(env["SAP_MEDIA_SIMPLIFIED_RETRY_MAX"], "1")
                self.assertEqual(env["SAP_VSE4_QUERY_EXPANSION"], "1")
                self.assertEqual(env["SAP_VSE4_QUERY_ONLY_ON_EMPTY"], "1")
                self.assertEqual(env["SAP_VSE4_QUERY_EXTRA"], "1")
        finally:
            runtime.SID = old_sid


if __name__ == "__main__":
    unittest.main()
