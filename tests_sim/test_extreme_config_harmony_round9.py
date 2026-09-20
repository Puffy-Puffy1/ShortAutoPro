import math
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ExtremeConfigHarmonyRound9Tests(unittest.TestCase):
    def test_runtime_config_falls_back_and_clamps(self):
        import runtime_config

        with patch.dict(os.environ, {"SAP_TEST_INT": "abc"}, clear=False):
            self.assertEqual(runtime_config.env_int("SAP_TEST_INT", 4, 0, 6), 4)
        with patch.dict(os.environ, {"SAP_TEST_INT": "999"}, clear=False):
            self.assertEqual(runtime_config.env_int("SAP_TEST_INT", 4, 0, 6), 6)
        with patch.dict(os.environ, {"SAP_TEST_FLOAT": "nan"}, clear=False):
            self.assertEqual(runtime_config.env_float("SAP_TEST_FLOAT", 1.5, 0.0, 2.0), 1.5)
        with patch.dict(os.environ, {"SAP_TEST_FLOAT": "inf"}, clear=False):
            self.assertEqual(runtime_config.env_float("SAP_TEST_FLOAT", 1.5, 0.0, 2.0), 1.5)
        self.assertTrue(math.isfinite(runtime_config.env_float("SAP_MISSING_FLOAT", 1.0, 0.0, 2.0)))

    def test_fragile_runtime_modules_use_shared_config_parser(self):
        expectations = {
            "audio_finalizer.py": ("env_float", 'float(os.getenv("SAP_AUDIO_'),
            "visual_qa.py": ("env_int", 'int(os.getenv("SHORT_QTD_CENAS"'),
            "multi_asset_director.py": ("env_int", 'int(os.getenv("SAP_MULTI_ASSET_MAX"'),
        }
        for name, (helper, forbidden) in expectations.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("runtime_config import", text, name)
            self.assertIn(helper, text, name)
            self.assertNotIn(forbidden, text, name)

    def test_secondary_asset_config_has_explicit_bounds(self):
        text = (ROOT / "multi_asset_director.py").read_text(encoding="utf-8")
        self.assertIn('env_int("SAP_MULTI_ASSET_MAX",4,0,6)', text)
        self.assertIn('env_float("SAP_MULTI_ASSET_DOWNLOAD_SECONDS",45.0,10.0,120.0)', text)

    def test_audio_policy_config_has_safe_bounds(self):
        text = (ROOT / "audio_finalizer.py").read_text(encoding="utf-8")
        self.assertIn('env_float("SAP_AUDIO_TARGET_LUFS",-14.0,-24.0,-8.0)', text)
        self.assertIn('env_float("SAP_AUDIO_TRUE_PEAK_DB",-1.5,-6.0,-0.1)', text)
        self.assertIn('env_float("SAP_AUDIO_LUFS_TOLERANCE",0.7,0.1,3.0)', text)


if __name__ == "__main__":
    unittest.main()
