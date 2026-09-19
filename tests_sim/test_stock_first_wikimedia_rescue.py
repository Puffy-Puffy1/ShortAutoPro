import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StockFirstWikimediaRescueTests(unittest.TestCase):
    def test_stock_first_defer_has_bounded_wikimedia_rescue(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn('SAP_SOURCE_ROUTE_FASTPATH=STOCK_FIRST', text)
        self.assertIn('SAP_SOURCE_ROUTE_RESCUE=WIKIMEDIA', text)
        self.assertIn('reason=NO_STRICT_STOCK_MATCH', text)
        self.assertIn('buscar_wikimedia_fotos(', text)
        self.assertIn('candidato_semanticamente_valido(', text)

    def test_rescue_does_not_relax_strict_must(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        block = text[
            text.index('# Stock-first intentionally defers Wikimedia'):
            text.index('# Wikimedia continua sendo processado', text.index('# Stock-first intentionally defers Wikimedia'))
        ]
        self.assertIn('relaxado=False', block)
        self.assertNotIn('relaxado=True', block)

    def test_easy_stock_scene_still_keeps_fast_path(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        block = text[
            text.index('# Stock-first intentionally defers Wikimedia'):
            text.index('# Wikimedia continua sendo processado', text.index('# Stock-first intentionally defers Wikimedia'))
        ]
        self.assertIn('if not _stock_strict_ok:', block)
        self.assertNotIn('if _stock_strict_ok:', block)


if __name__ == "__main__":
    unittest.main()
