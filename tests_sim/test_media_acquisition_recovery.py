#!/usr/bin/env python3
import unittest

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

    def test_coverr_circuit_opens_after_two_empty_returns(self):
        calls = []

        def fake_coverr(*args, **kwargs):
            calls.append(args)
            return []

        namespace = {"coverr_video": fake_coverr}
        recovery.install(namespace)
        wrapped = namespace["coverr_video"]
        self.assertEqual(wrapped("one", [], []), [])
        self.assertEqual(wrapped("two", [], []), [])
        self.assertEqual(wrapped("three", [], []), [])
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
