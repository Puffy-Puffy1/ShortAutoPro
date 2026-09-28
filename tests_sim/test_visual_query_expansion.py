#!/usr/bin/env python3
import os
import unittest


class VisualQueryExpansionTests(unittest.TestCase):
    def test_expansion_is_rescue_only_when_primary_has_candidates(self):
        from visual_query_expansion_v4 import wrap_search_function

        calls = []

        def search(query, must_have=None):
            calls.append(query)
            return [{"id": "primary"}]

        old = os.environ.get("SAP_VSE4_QUERY_ONLY_ON_EMPTY")
        os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
        try:
            wrapped = wrap_search_function(search)
            result = wrapped(
                "abandoned merchant ship",
                ["ship", "ocean"],
            )
        finally:
            if old is None:
                os.environ.pop("SAP_VSE4_QUERY_ONLY_ON_EMPTY", None)
            else:
                os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = old

        self.assertEqual(len(result), 1)
        self.assertEqual(calls, ["abandoned merchant ship"])

    def test_empty_primary_uses_must_first_rescue(self):
        from visual_query_expansion_v4 import wrap_search_function

        calls = []

        def search(query, must_have=None):
            calls.append(query)
            if query != "abandoned vintage merchant ship drifting at sea":
                return [{"id": "rescued"}]
            return []

        old_expansion = os.environ.get("SAP_VSE4_QUERY_EXPANSION")
        old_extra = os.environ.get("SAP_VSE4_QUERY_EXTRA")
        old_only = os.environ.get("SAP_VSE4_QUERY_ONLY_ON_EMPTY")
        os.environ["SAP_VSE4_QUERY_EXPANSION"] = "1"
        os.environ["SAP_VSE4_QUERY_EXTRA"] = "1"
        os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
        try:
            wrapped = wrap_search_function(search)
            result = wrapped(
                "abandoned vintage merchant ship drifting at sea",
                ["ship", "ocean"],
            )
        finally:
            for name, value in (
                ("SAP_VSE4_QUERY_EXPANSION", old_expansion),
                ("SAP_VSE4_QUERY_EXTRA", old_extra),
                ("SAP_VSE4_QUERY_ONLY_ON_EMPTY", old_only),
            ):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.assertEqual(result, [{"id": "rescued"}])
        self.assertEqual(calls[0], "abandoned vintage merchant ship drifting at sea")
        self.assertEqual(len(calls), 2)
        self.assertIn("ship", calls[1].casefold())
        self.assertIn("ocean", calls[1].casefold())
        self.assertIn("vessel", calls[1].casefold())


if __name__ == "__main__":
    unittest.main()
