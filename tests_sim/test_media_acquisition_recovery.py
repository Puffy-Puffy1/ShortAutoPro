#!/usr/bin/env python3
import os
import unittest
from unittest.mock import patch

import media_acquisition_recovery as recovery


class MediaAcquisitionRecoveryTests(unittest.TestCase):
    def test_rescue_query_contains_all_explicit_must_terms(self):
        queries = recovery._rescue_queries(
            "paper documents",
            ["case file", "criminal record"],
            "Alcatraz escape 1962",
        )
        self.assertTrue(queries)
        self.assertIn("case file", queries[0])
        self.assertIn("criminal record", queries[0])

    def test_pool_rescue_only_runs_when_initial_pool_has_no_complete_asset(self):
        calls = []

        def fake_search(busca, must_have, avoid, segmento="", visual_mode=""):
            calls.append(busca)
            if "dummy head paper mache" in busca:
                return [{
                    "title": "Dummy head made from paper mache",
                    "url": "https://example.test/complete.jpg",
                }]
            return [{
                "title": "Dummy head",
                "url": "https://example.test/partial.jpg",
            }]

        namespace = {
            "buscar_todos_candidatos": fake_search,
            "ASSUNTO": "Alcatraz escape",
        }
        result = recovery.install(namespace)
        self.assertTrue(result["must_pool_rescue"])

        pool = namespace["buscar_todos_candidatos"](
            "dummy head",
            ["dummy head", "paper mache"],
            [],
        )
        self.assertGreaterEqual(len(calls), 2)
        self.assertTrue(any(recovery._complete(item, ["dummy head", "paper mache"]) for item in pool))

    def test_complete_initial_asset_skips_rescue_queries(self):
        calls = []

        def fake_search(busca, must_have, avoid, segmento="", visual_mode=""):
            calls.append(busca)
            return [{
                "title": "Cell house with metal tiers",
                "url": "https://example.test/cell.jpg",
            }]

        namespace = {"buscar_todos_candidatos": fake_search}
        recovery.install(namespace)
        namespace["buscar_todos_candidatos"](
            "cell house metal tiers",
            ["cell house", "metal tiers"],
            [],
        )
        self.assertEqual(calls, ["cell house metal tiers"])

    def test_provider_circuit_has_single_external_authority(self):
        def fake_coverr(*args, **kwargs):
            return []

        namespace = {"coverr_video": fake_coverr}
        result = recovery.install(namespace)
        self.assertIs(namespace["coverr_video"], fake_coverr)
        self.assertEqual(result["provider_circuit"], "media_external_resilience")

    def test_identical_acquisition_calls_use_cache_and_return_isolated_copy(self):
        calls = []

        def fake_search(busca, must_have, avoid, segmento="", visual_mode=""):
            calls.append(busca)
            return [{
                "title": "Generic prison exterior",
                "url": "https://example.test/prison.jpg",
                "score": 1,
            }]

        namespace = {"buscar_todos_candidatos": fake_search}
        recovery.install(namespace)
        wrapped = namespace["buscar_todos_candidatos"]

        first = wrapped("prison exterior", [], [])
        first[0]["score"] = 999
        second = wrapped("prison exterior", [], [])

        self.assertEqual(calls, ["prison exterior"])
        self.assertEqual(second[0]["score"], 1)
        self.assertEqual(wrapped._sap_acquisition_stats["hits"], 1)
        self.assertEqual(wrapped._sap_acquisition_stats["misses"], 1)

    def test_rescue_budget_is_bounded_and_configurable(self):
        with patch.dict(os.environ, {"SAP_MUST_RESCUE_MAX_QUERIES": "2"}, clear=False):
            self.assertEqual(recovery._rescue_budget(), 2)
        with patch.dict(os.environ, {"SAP_MUST_RESCUE_MAX_QUERIES": "999"}, clear=False):
            self.assertEqual(recovery._rescue_budget(), 8)
        with patch.dict(os.environ, {"SAP_MUST_RESCUE_MAX_QUERIES": "invalid"}, clear=False):
            self.assertEqual(recovery._rescue_budget(), 2)


    def test_install_is_idempotent_and_keeps_existing_wrapper_active(self):
        calls = []

        def fake_search(busca, must_have, avoid, segmento="", visual_mode=""):
            calls.append(busca)
            return []

        namespace = {"buscar_todos_candidatos": fake_search}
        first = recovery.install(namespace)
        wrapped = namespace["buscar_todos_candidatos"]
        second = recovery.install(namespace)

        self.assertTrue(first["must_pool_rescue"])
        self.assertTrue(second["must_pool_rescue"])
        self.assertIs(namespace["buscar_todos_candidatos"], wrapped)


if __name__ == "__main__":
    unittest.main()
