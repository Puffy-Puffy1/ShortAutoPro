import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "audio.py"


class AudioBaseTests(unittest.TestCase):
    def test_uses_downloaded_piper_model_file_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            voice_dir = base / "piper" / "voice"
            voice_dir.mkdir(parents=True)
            model = voice_dir / "pt_BR-faber-medium.onnx"
            model.write_bytes(b"test-model-placeholder")
            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import audio; print(audio.MODEL_ARG)",
                ],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(str(model), result.stdout.strip())

    def test_accepts_explicit_absolute_piper_model_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            model = base / "piper" / "voice" / "pt_BR-faber-medium.onnx"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"test-model-placeholder")
            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            env["PIPER_MODEL"] = str(model)
            result = subprocess.run(
                [sys.executable, "-c", "import audio; print(audio.MODEL_ARG)"],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), str(model))

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
