import unittest
from pathlib import Path

import media_acquisition_recovery as recovery
import media_must_verifier as mustv


ROOT = Path(__file__).resolve().parents[1]


class Stage6RecoveryUnwrapTests(unittest.TestCase):
    def test_query_expansion_exposes_underlying_function(self):
        text = (ROOT / "visual_query_expansion_v4.py").read_text(encoding="utf-8")
        self.assertIn("_sap_query_expansion_original", text)
        self.assertIn("wrapped.__wrapped__ = fn", text)

    def test_recovery_collapses_wrapper_chain(self):
        text = (ROOT / "media_acquisition_recovery.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "2.0"', text)
        self.assertIn("_sap_query_expansion_original", text)
        self.assertIn("_sap_vse42_original", text)
        self.assertIn("__wrapped__", text)
        self.assertIn("SAP_MEDIA_RESCUE_NESTING=DISABLED layers=", text)

    def test_stock_first_queries_are_short_visual_queries(self):
        queries = recovery._rescue_queries(
            "prisoner hands chipping concrete wall with makeshift spoon tool",
            ["hands", "wall", "spoon"],
            "A Fuga de Alcatraz de 1962",
            "Esculpindo concreto ferramentas improvisadas, como colheres",
            "object",
        )
        joined = " | ".join(queries)
        self.assertIn("hands wall spoon", joined)
        self.assertNotIn("A Fuga de Alcatraz de 1962", joined)
        self.assertLessEqual(len(queries), 8)

    def test_documentary_queries_keep_subject_context(self):
        queries = recovery._rescue_queries(
            "vintage FBI agents examining papers",
            ["investigators", "papers"],
            "A Fuga de Alcatraz de 1962",
            "depois ajudou FBI.",
            "evidence",
        )
        self.assertTrue(any("A Fuga de Alcatraz de 1962" in q for q in queries))

    def test_spoon_aliases_are_conservative(self):
        good = {"description": "hand holding a metal spoon beside a concrete wall"}
        bad = {"description": "hand holding a hammer beside a concrete wall"}
        self.assertTrue(mustv.requirement_matches("spoon", good))
        self.assertFalse(mustv.requirement_matches("spoon", bad))

    def test_ventilation_duct_alias_matches_air_duct(self):
        candidate = {"description": "worker inside an air duct passage"}
        self.assertTrue(mustv.requirement_matches("ventilation duct", candidate))

    def test_tunnel_alias_matches_passageway_but_not_corridor(self):
        self.assertTrue(
            mustv.requirement_matches(
                "tunnel",
                {"description": "dark underground passageway"},
            )
        )
        self.assertFalse(
            mustv.requirement_matches(
                "tunnel",
                {"description": "office corridor"},
            )
        )

    def test_stock_first_defers_wikimedia(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_SOURCE_ROUTE_FASTPATH=STOCK_FIRST", text)
        self.assertIn('rota_fonte.get("route") != "stock_first"', text)

    def test_provider_timeouts_are_bounded(self):
        media = (ROOT / "midia.py").read_text(encoding="utf-8")
        wiki = (ROOT / "wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_API_TIMEOUT", media)
        self.assertIn("SAP_WIKIMEDIA_TIMEOUT", wiki)
        self.assertIn("10", media)
        self.assertIn("10", wiki)

    def test_strict_policy_is_still_fail_closed(self):
        strict = (ROOT / "media_strict_must_guard.py").read_text(encoding="utf-8")
        self.assertIn("EXPLICIT_MUST_FAIL_CLOSED", strict)
        self.assertIn("hits >= total", strict)


if __name__ == "__main__":
    unittest.main()
