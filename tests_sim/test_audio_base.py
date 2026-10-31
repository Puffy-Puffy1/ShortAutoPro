import os
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch
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


    def test_piper_output_is_validated_as_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            script = r"""
import sys, wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import audio

def fake_piper(command, **kwargs):
    destination = Path(command[command.index("-f") + 1])
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(b"\\x00\\x00" * 2205)
    return SimpleNamespace(returncode=0)

destination = Path(sys.argv[1])
with patch("audio.run_group", side_effect=fake_piper):
    audio.piper_wav("teste de voz", destination, {})
assert destination.is_file() and destination.stat().st_size > 44
"""
            destination = base / "speech.wav"
            result = subprocess.run(
                [sys.executable, "-c", script, str(destination)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(destination.is_file())
            self.assertGreater(destination.stat().st_size, 44)

    def test_ffmpeg_does_not_mislabel_piper_wav_as_raw_float_pcm(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"f32le"', source)
        self.assertIn('str(source_wav)', source)
        self.assertIn('wave.open(str(dest)', source)


    def test_speech_director_preserves_cyrillic_subtitles_but_sanitizes_tts_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiro_dir = base / "roteiros"
            roteiro_dir.mkdir()
            original = (
                'A montanha Kholat Syakhl (Холат Сяхл) fica nos Urais. '
                'O Passo Dyatlov (Перевал Дятлова) recebeu esse nome.'
            )
            (roteiro_dir / "short_pronunciation_case.txt").write_text(original, encoding="utf-8")
            env = os.environ.copy()
            env["SHORTAUTOPRO_BASE"] = str(base)
            env["SHORT_ID"] = "pronunciation_case"
            result = subprocess.run(
                [sys.executable, str(ROOT / "speech_director.py")],
                cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            speech_text = (roteiro_dir / "speech_pronunciation_case.txt").read_text(encoding="utf-8")
            import json
            plan = json.loads((roteiro_dir / "speech_pronunciation_case.json").read_text(encoding="utf-8"))
            self.assertIn("Холат Сяхл", speech_text)
            self.assertIn("Перевал Дятлова", speech_text)
            tts_text = " ".join(chunk["tts_text"] for chunk in plan["chunks"])
            self.assertIn("Kholat Syakhl", tts_text)
            self.assertIn("Passo Dyatlov", tts_text)
            self.assertNotRegex(tts_text, r"[\u0400-\u04FF]")

    def test_segmented_audio_uses_pronunciation_safe_text(self):
        import audio
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            spoken = []

            def fake_piper(text, destination, _env):
                spoken.append(text)
                with wave.open(str(destination), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(22050)
                    output.writeframes(b"\x00\x00" * 2205)

            def fake_ffmpeg(command, **_kwargs):
                destination = Path(command[-1])
                with wave.open(str(destination), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(44100)
                    output.writeframes(b"\x00\x00" * 2205)

            with patch("audio.piper_wav", side_effect=fake_piper), patch("audio.run_group", side_effect=fake_ffmpeg):
                audio.render_segmented(
                    [{"text": "Kholat Syakhl (Холат Сяхл)", "tts_text": "Kholat Syakhl"}],
                    work, {}
                )
            self.assertEqual(spoken, ["Kholat Syakhl"])

if __name__ == "__main__":
    unittest.main()
