import unittest
from pathlib import Path

import source_ledger


class SourceLedgerIdempotentTests(unittest.TestCase):
    def test_identical_duplicate_scene_credit_collapses(self):
        credits = [
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:A.jpg", "license": "CC BY 4.0", "author": "A"},
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:A.jpg", "license": "CC BY 4.0", "author": "A"},
        ]
        resolved, notes = source_ledger.reconciliar_creditos_duplicados(credits, [])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["scene"], 3)
        self.assertEqual(notes[0]["reason"], "IDENTICAL_DUPLICATE_COLLAPSED")

    def test_distinct_duplicates_resolve_only_with_final_provenance(self):
        credits = [
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:A.jpg", "license": "CC BY 4.0", "author": "A"},
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:B.jpg", "license": "CC BY 4.0", "author": "B"},
        ]
        provenance = [{
            "provider": "Wikimedia Commons",
            "source_url": "https://commons.wikimedia.org/wiki/File:B.jpg",
            "local_path": "/tmp/scene_03.jpg",
        }]
        resolved, notes = source_ledger.reconciliar_creditos_duplicados(credits, provenance)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["page"], "https://commons.wikimedia.org/wiki/File:B.jpg")
        self.assertEqual(notes[0]["reason"], "PROVENANCE_OR_WIKIMEDIA_FILE_MATCH")

    def test_ambiguous_distinct_duplicates_fail_closed(self):
        credits = [
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:A.jpg", "license": "CC BY 4.0", "author": "A"},
            {"scene": 3, "page": "https://commons.wikimedia.org/wiki/File:B.jpg", "license": "CC BY 4.0", "author": "B"},
        ]
        with self.assertRaises(RuntimeError):
            source_ledger.reconciliar_creditos_duplicados(credits, [])

    def test_writer_is_idempotent_by_scene(self):
        text = Path("wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("Keep exactly one credit block per scene", text)
        self.assertIn("os.replace(temp_path, path)", text)
        self.assertNotIn('"a",\n            encoding="utf-8"', text)

    def test_ledger_records_reconciliation_metadata(self):
        text = Path("source_ledger.py").read_text(encoding="utf-8")
        self.assertIn('"raw_scene_credit_blocks"', text)
        self.assertIn('"reconciled_duplicate_scenes"', text)


if __name__ == "__main__":
    unittest.main()
