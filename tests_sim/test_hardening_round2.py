import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import source_identity
import source_router
import topic_memory


ROOT = Path(__file__).resolve().parents[1]


class TopicIdentityHardeningTests(unittest.TestCase):
    def test_same_bare_number_different_entities_is_not_automatic_duplicate(self):
        score = topic_memory.similaridade(
            "Air France 3054",
            "TAM 3054",
        )
        self.assertLess(score, 0.72)

    def test_alphanumeric_id_remains_strong(self):
        score = topic_memory.similaridade(
            "Desaparecimento do MH370",
            "Voo MH-370",
        )
        self.assertEqual(score, 1.0)

    def test_generic_flight_number_is_not_mh370_alias(self):
        aliases = source_identity.detectar_aliases(
            "Voo 370 da Air France"
        )
        self.assertNotIn("mh370", aliases)

    def test_year_difference_does_not_create_numeric_identity_conflict(self):
        result = source_identity.conflito_id_numerico(
            "Incidente em 2014",
            "Incidente em 2015",
        )
        self.assertFalse(result["conflict"])
        self.assertEqual(result["topic_ids"], [])
        self.assertEqual(result["title_ids"], [])


class SourceRouterBoundaryTests(unittest.TestCase):
    def test_train_does_not_match_inside_training(self):
        result = source_router.escolher_rota(
            "unknown_mode",
            ["training exercise"],
        )
        self.assertEqual(result["route"], "stock_first")

    def test_train_token_routes_to_mixed(self):
        result = source_router.escolher_rota(
            "unknown_mode",
            ["historic train station"],
        )
        self.assertEqual(result["route"], "mixed")


class ConfigurableEditorialGateTests(unittest.TestCase):
    def test_editorial_gate_respects_configured_scene_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "ShortAutoPro"
            roteiros = base / "roteiros"
            imagens = base / "imagens" / "short_regression"
            roteiros.mkdir(parents=True)
            imagens.mkdir(parents=True)

            count = 8
            scenes = [{"scene": i} for i in range(1, count + 1)]
            motion = [{"scene": i} for i in range(1, count + 1)]

            (roteiros / "scene_map_regression.json").write_text(
                json.dumps({"scenes": scenes}),
                encoding="utf-8",
            )
            (roteiros / "motion_plan_regression.json").write_text(
                json.dumps({"scenes": motion}),
                encoding="utf-8",
            )

            for i in range(1, count + 1):
                (imagens / f"scene_{i:02d}.webp").write_bytes(b"fake")

            env = os.environ.copy()
            env["HOME"] = tmp
            env["USERPROFILE"] = tmp
            env["SHORT_ID"] = "regression"
            env["SHORT_QTD_CENAS"] = str(count)

            proc = subprocess.run(
                [sys.executable, str(ROOT / "editorial_gate.py")],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, output)
            self.assertIn("8/8", output)
            self.assertIn("EDITORIAL GATE: PASS", output)


if __name__ == "__main__":
    unittest.main()
