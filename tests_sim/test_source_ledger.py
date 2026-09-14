import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "source_ledger.py"


class SourceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "credits").mkdir(parents=True)
        (self.base / "roteiros").mkdir(parents=True)
        (self.base / "imagens" / "short_case").mkdir(parents=True)
        (self.base / "manifests" / "source_provenance_live").mkdir(parents=True)

        self.media = self.base / "imagens" / "short_case" / "scene_01.jpg"
        self.media.write_bytes(b"fake")

        publish = {
            "chosen_title": "Título válido para teste",
            "description": "Descrição válida para o pacote de publicação.",
            "hashtags": ["#Shorts", "#Teste", "#Media", "#Fonte", "#Video"],
            "publish_score": 80,
        }
        (self.base / "roteiros" / "publish_case.json").write_text(
            json.dumps(publish), encoding="utf-8"
        )
        (self.base / "roteiros" / "publish_case.txt").write_text(
            "TÍTULO:\nTítulo válido para teste\n\nDESCRIÇÃO:\n"
            "Descrição válida para o pacote de publicação.\n\nHASHTAGS:\n"
            "#Shorts #Teste #Media #Fonte #Video\n",
            encoding="utf-8",
        )

        provenance = {
            "provider": "Wikimedia Commons",
            "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
            "local_path": str(self.media.resolve()),
        }
        (self.base / "manifests" / "source_provenance_live" / "source_test_scene_01.json").write_text(
            json.dumps(provenance), encoding="utf-8"
        )

        self.env = os.environ.copy()
        self.env.update(
            {
                "SHORTAUTOPRO_BASE": str(self.base),
                "SHORT_ID": "case",
                "SHORT_QTD_CENAS": "6",
                "PYTHONIOENCODING": "utf-8",
            }
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_ledger(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(REPO),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_wikimedia_provenance_without_credit_blocks(self):
        result = self.run_ledger()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sem crédito", result.stdout)

    def test_matching_wikimedia_credit_passes(self):
        (self.base / "credits" / "short_case.txt").write_text(
            "SCENE 1\n"
            "Author: Example Author\n"
            "License: CC BY 4.0\n"
            "Page: https://commons.wikimedia.org/wiki/File:Example.jpg\n",
            encoding="utf-8",
        )
        result = self.run_ledger()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        ledger = json.loads(
            (self.base / "credits" / "ledger_case.json").read_text(encoding="utf-8")
        )
        self.assertEqual(ledger["wikimedia_scenes_from_provenance"], [1])
        self.assertTrue(ledger["attribution_required"])

        publish = json.loads(
            (self.base / "roteiros" / "publish_case.json").read_text(encoding="utf-8")
        )
        self.assertIn("Example Author", publish["media_attribution"])


if __name__ == "__main__":
    unittest.main()
