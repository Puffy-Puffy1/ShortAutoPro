import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "audio.py"


class AudioBaseTests(unittest.TestCase):
    def test_respects_shortautopro_base_before_runtime_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            env["SHORT_ID"] = "isolated_audio_001"

            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            combined = result.stdout + result.stderr
            expected = base / "roteiros" / "short_isolated_audio_001.txt"

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(expected), combined)
            self.assertNotIn(str(Path.home() / "ShortAutoPro" / "roteiros"), combined)


if __name__ == "__main__":
    unittest.main()
