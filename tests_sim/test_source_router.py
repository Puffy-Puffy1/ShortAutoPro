import unittest

from source_router import escolher_rota


class SourceRouterTests(unittest.TestCase):
    def test_documentary_mode_stays_documentary_first(self):
        result = escolher_rota("document")
        self.assertEqual(result["route"], "documentary_first")
        self.assertGreater(result["wikimedia_bonus"], 0)

    def test_portuguese_accented_airplane_cue_routes_mixed(self):
        result = escolher_rota("", ["avião desaparecido"])
        self.assertEqual(result["route"], "mixed")
        self.assertGreater(result["wikimedia_bonus"], 0)

    def test_portuguese_document_cue_routes_mixed(self):
        result = escolher_rota("", ["relatório policial"])
        self.assertEqual(result["route"], "mixed")

    def test_generic_must_have_remains_stock_first(self):
        result = escolher_rota("", ["floresta escura", "chuva"])
        self.assertEqual(result["route"], "stock_first")


if __name__ == "__main__":
    unittest.main()
