#!/usr/bin/env python3
import importlib
import math
import os
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


class PiperTermuxCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / "shortautopro"
        cls.env_patch = patch.dict(os.environ, {"SHORTAUTOPRO_BASE": str(cls.base)})
        cls.env_patch.start()
        import audio
        cls.audio = importlib.reload(audio)

    @classmethod
    def tearDownClass(cls):
        cls.env_patch.stop()
        cls.temp.cleanup()

    def test_wav_output_is_accepted_without_reencoding(self):
        root = Path(self.temp.name)
        source = root / "piper.wav"
        destination = root / "voice.wav"
        with wave.open(str(source), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes(b"\\x00\\x00" * 2205)
        self.audio.convert_piper_output(source, destination, 22050)
        self.assertFalse(source.exists())
        with wave.open(str(destination), "rb") as result:
            self.assertEqual(result.getframerate(), 22050)
            self.assertEqual(result.getnframes(), 2205)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for RAW conversion")
    def test_termux_float32_raw_output_is_converted_to_pcm_wav(self):
        root = Path(self.temp.name)
        source = root / "piper.raw"
        destination = root / "voice_from_raw.wav"
        sample_rate = 22050
        samples = [
            struct.pack("<f", 0.2 * math.sin(2 * math.pi * 440 * i / sample_rate))
            for i in range(2205)
        ]
        source.write_bytes(b"".join(samples))
        self.audio.convert_piper_output(source, destination, sample_rate)
        self.assertFalse(source.exists())
        with wave.open(str(destination), "rb") as result:
            self.assertEqual(result.getnchannels(), 1)
            self.assertEqual(result.getsampwidth(), 2)
            self.assertEqual(result.getframerate(), sample_rate)
            self.assertGreater(result.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
