import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepairAndSecondaryBoundsTests(unittest.TestCase):
    def test_repair_actions_have_timeout(self):
        text = (ROOT / "shortauto_repair_engine.py").read_text(encoding="utf-8")
        self.assertIn("SAP_REPAIR_ACTION_TIMEOUT", text)
        self.assertIn("SAP_REPAIR_MEDIA_TIMEOUT", text)
        self.assertIn("SAP_REPAIR_RENDER_TIMEOUT", text)
        self.assertIn("subprocess.TimeoutExpired", text)
        self.assertIn("SHORTAUTO_REPAIR_ACTION_TIMEOUT", text)

    def test_secondary_media_is_bounded(self):
        text = (ROOT / "multi_asset_director.py").read_text(encoding="utf-8")
        self.assertIn('SAP_MULTI_ASSET_DOWNLOAD_SECONDS",20.0', text)
        self.assertIn('SAP_MULTI_ASSET_MAX",2', text)
        self.assertIn("timeout=(5,read_timeout)", text)


if __name__ == "__main__":
    unittest.main()
