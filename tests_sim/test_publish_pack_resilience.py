import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublishPackResilienceTests(unittest.TestCase):
    def test_publish_pack_uses_shared_gemini_runtime(self):
        text = (ROOT / "publish_pack.py").read_text(encoding="utf-8")
        self.assertIn("from gemini_runtime import", text)
        self.assertIn('component="Publish Pack"', text)
        self.assertNotIn("requests.post(", text)
        self.assertNotIn("generativelanguage.googleapis.com", text)

    def test_publish_pack_has_local_fallback(self):
        text = (ROOT / "publish_pack.py").read_text(encoding="utf-8")
        self.assertIn("def local_publish_pack", text)
        self.assertIn("PUBLISH_PACK_FALLBACK=LOCAL", text)
        self.assertIn("PUBLISH_PACK_MODE=DEGRADED_LOCAL", text)

    def test_missing_api_key_no_longer_hard_blocks(self):
        text = (ROOT / "publish_pack.py").read_text(encoding="utf-8")
        self.assertNotIn('raise ValueError("GEMINI_API_KEY não configurada")', text)

    def test_local_fallback_keeps_publish_contract(self):
        text = (ROOT / "publish_pack.py").read_text(encoding="utf-8")
        for tag in (
            "#Shorts",
            "#Misterio",
            "#HistoriaReal",
            "#Documentario",
            "#Curiosidades",
        ):
            self.assertIn(tag, text)
        self.assertIn("return validate_payload", text)


if __name__ == "__main__":
    unittest.main()
