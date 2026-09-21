import tempfile
import unittest
from pathlib import Path

import media_external_resilience as resilience

ROOT = Path(__file__).resolve().parents[1]


class MediaExternalResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        resilience.STATE_FILE = Path(self.tmp.name) / "state.json"
        resilience._STATE = None

    def tearDown(self):
        resilience._STATE = None
        self.tmp.cleanup()

    def test_http_failures_are_classified(self):
        self.assertEqual(resilience.classify_http_status(403), "AUTH")
        self.assertEqual(resilience.classify_http_status(429), "RATE_LIMIT")
        self.assertEqual(resilience.classify_http_status(404), "REMOVED")
        self.assertEqual(resilience.classify_http_status(503), "SERVER")
        self.assertEqual(resilience.classify_http_status(200), "SUCCESS")

    def test_auth_failure_opens_provider_circuit(self):
        resilience.note_provider_event("coverr_video", "AUTH", status=403)
        allowed, reason, remaining = resilience.provider_gate("coverr_video")
        self.assertFalse(allowed)
        self.assertEqual(reason, "AUTH")
        self.assertGreater(remaining, 0)

    def test_rate_limit_uses_retry_after(self):
        resilience.note_provider_event(
            "pixabay_foto",
            "RATE_LIMIT",
            status=429,
            retry_after=120,
        )
        allowed, reason, remaining = resilience.provider_gate("pixabay_video")
        self.assertFalse(allowed)
        self.assertEqual(reason, "RATE_LIMIT")
        self.assertGreater(remaining, 100)

    def test_bad_asset_is_quarantined_by_provider_and_id(self):
        url = "https://example.test/media/a.jpg?signed=secret"
        resilience.mark_asset_bad(
            url,
            provider="Wikimedia",
            asset_id="123",
            reason="CORRUPT",
        )
        blocked, reason, remaining = resilience.asset_blocked(
            url,
            provider="Wikimedia",
            asset_id="123",
        )
        self.assertTrue(blocked)
        self.assertEqual(reason, "CORRUPT")
        self.assertGreater(remaining, 0)

    def test_midia_integrates_circuits_quarantine_and_bounded_download(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_CIRCUIT=SKIP", text)
        self.assertIn("SAP_MEDIA_ASSET_QUARANTINE", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_MAX_MB", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_WALL_SECONDS", text)
        self.assertIn("SAP_MEDIA_SEMANTIC_REJECT", text)
        self.assertIn("candidato=candidato", text)

    def test_wikimedia_has_typed_failure_and_metadata_control(self):
        text = (ROOT / "wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("SAP_WIKIMEDIA_CIRCUIT=SKIP", text)
        self.assertIn('"MALFORMED"', text)
        self.assertIn('"wiki_metadata_strength"', text)
        self.assertIn("_sap_note_provider_items", text)


if __name__ == "__main__":
    unittest.main()
