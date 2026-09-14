import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "used_topic.py"


class UsedTopicBaseTests(unittest.TestCase):
    def test_uses_shortautopro_base_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)
            short_id = "test_custom_base"
            source = roteiros / f"fonte_{short_id}.txt"
            source.write_text(
                "ASSUNTO: Caso de Teste\n\nFonte factual controlada.",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            env["SHORT_ID"] = short_id

            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            output = roteiros / f"used_topic_{short_id}.txt"
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_text(encoding="utf-8"), "Caso de Teste")


if __name__ == "__main__":
    unittest.main()
