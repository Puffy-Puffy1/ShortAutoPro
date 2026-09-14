import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class RegisterTopicRuntimeTests(unittest.TestCase):
    def run_register(self, base: Path, short_id: str):
        env = os.environ.copy()
        env["SHORTAUTOPRO_BASE"] = str(base)
        env["SHORT_ID"] = short_id
        return subprocess.run(
            [sys.executable, str(REPO / "register_topic.py")],
            cwd=str(REPO),
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_respects_shortautopro_base_and_registers_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)
            short_id = "test_001"
            (roteiros / f"used_topic_{short_id}.txt").write_text(
                "O Assassino do Zodíaco", encoding="utf-8"
            )

            first = self.run_register(base, short_id)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            history = base / "historico_assuntos.json"
            self.assertTrue(history.is_file())
            payload = json.loads(history.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["short_id"], short_id)
            self.assertEqual(payload[0]["topic"], "O Assassino do Zodíaco")

            second = self.run_register(base, short_id)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            payload2 = json.loads(history.read_text(encoding="utf-8"))
            self.assertEqual(len(payload2), 1)

    def test_invalid_history_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)
            short_id = "test_002"
            (roteiros / f"topic_{short_id}.txt").write_text(
                "Caso de teste", encoding="utf-8"
            )
            history = base / "historico_assuntos.json"
            history.write_text("{invalid", encoding="utf-8")

            result = self.run_register(base, short_id)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(history.read_text(encoding="utf-8"), "{invalid")


if __name__ == "__main__":
    unittest.main()
