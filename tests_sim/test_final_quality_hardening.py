import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "final_quality.py"


class FinalQualityHardeningTests(unittest.TestCase):
    def test_missing_manifest_blocks_even_with_good_text_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)
            (roteiros / "short_case.txt").write_text(" ".join(["palavra"] * 110), encoding="utf-8")
            (roteiros / "hook_case.txt").write_text("Este mistério nunca deixou de gerar perguntas", encoding="utf-8")
            (roteiros / "publish_case.json").write_text('{"publish_score": 90}', encoding="utf-8")

            env = os.environ.copy()
            env.update({
                "SHORTAUTOPRO_BASE": str(base),
                "SHORT_ID": "case",
                "SHORT_QTD_CENAS": "6",
                "PYTHONIOENCODING": "utf-8",
            })
            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=str(REPO),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest_missing_or_invalid", result.stdout)


if __name__ == "__main__":
    unittest.main()
