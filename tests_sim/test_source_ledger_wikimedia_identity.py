import unittest
from pathlib import Path

import media_provenance_capture_v1 as provenance
import source_ledger


class SourceLedgerWikimediaIdentityTests(unittest.TestCase):
    def test_commons_page_and_upload_url_share_asset_key(self):
        page = "https://commons.wikimedia.org/wiki/File:Example_image.jpg"
        upload = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Example_image.jpg"
        self.assertEqual(
            source_ledger._wikimedia_asset_key(page),
            source_ledger._wikimedia_asset_key(upload),
        )

    def test_upload_wikimedia_provenance_resolves_distinct_credits(self):
        credits = [
            {
                "scene": 3,
                "page": "https://commons.wikimedia.org/wiki/File:A.jpg",
                "license": "CC BY 4.0",
                "author": "A",
            },
            {
                "scene": 3,
                "page": "https://commons.wikimedia.org/wiki/File:B.jpg",
                "license": "CC BY 4.0",
                "author": "B",
            },
        ]
        records = [{
            "provider": "",
            "source_url": "https://upload.wikimedia.org/wikipedia/commons/x/y/B.jpg",
            "local_path": "/tmp/short_x/scene_03.jpg",
        }]
        resolved, notes = source_ledger.reconciliar_creditos_duplicados(
            credits,
            records,
        )
        self.assertEqual(len(resolved), 1)
        self.assertTrue(resolved[0]["page"].endswith("File:B.jpg"))
        self.assertEqual(
            notes[0]["reason"],
            "PROVENANCE_OR_WIKIMEDIA_FILE_MATCH",
        )

    def test_ambiguous_filename_still_fails_closed(self):
        credits = [
            {
                "scene": 3,
                "page": "https://commons.wikimedia.org/wiki/File:A.jpg",
                "license": "CC BY 4.0",
                "author": "A",
            },
            {
                "scene": 3,
                "page": "https://commons.wikimedia.org/wiki/File:B.jpg",
                "license": "CC BY 4.0",
                "author": "B",
            },
        ]
        records = [{
            "provider": "Wikimedia Commons",
            "source_url": "https://upload.wikimedia.org/wikipedia/commons/x/y/C.jpg",
            "local_path": "/tmp/short_x/scene_03.jpg",
        }]
        with self.assertRaises(RuntimeError):
            source_ledger.reconciliar_creditos_duplicados(credits, records)

    def test_provenance_prefers_credit_page(self):
        candidate = {
            "credit_page": "https://commons.wikimedia.org/wiki/File:A.jpg",
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/a/A.jpg",
        }
        normalized = provenance.normalize_candidate(candidate)
        self.assertEqual(
            normalized["source_url"],
            "https://commons.wikimedia.org/wiki/File:A.jpg",
        )
        self.assertEqual(normalized["provider"], "Wikimedia Commons")

    def test_upload_host_is_recognized_as_wikimedia(self):
        normalized = provenance.normalize_candidate({
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/a/A.jpg",
        })
        self.assertEqual(normalized["provider"], "Wikimedia Commons")

    def test_media_records_final_selected_candidate(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        self.assertIn("selected_scene_commit", text)
        self.assertIn("_sap_write_provenance(", text)
        self.assertIn("escolhido,", text)
        self.assertIn("destino,", text)


if __name__ == "__main__":
    unittest.main()
