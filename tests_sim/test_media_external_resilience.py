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

    def test_persistent_empty_results_open_short_circuit(self):
        class Response:
            status_code = 200
            headers = {}

        for _ in range(4):
            resilience.note_response("pexels_foto", Response())
            resilience.note_items("pexels_foto", [])

        allowed, reason, remaining = resilience.provider_gate("pexels_video")
        self.assertFalse(allowed)
        self.assertEqual(reason, "EMPTY")
        self.assertGreater(remaining, 0)

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


    def test_download_resource_miss_does_not_poison_provider_circuit(self):
        class Response:
            status_code = 403
            headers = {}

        event = resilience.note_response("download_pexels", Response())
        self.assertEqual(event, "AUTH")
        allowed, reason, remaining = resilience.provider_gate("download_pexels")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0.0)
        snap = resilience.snapshot()
        self.assertEqual(snap["download_pexels"]["resource_misses"], 1)

    def test_malformed_persisted_numbers_are_sanitized(self):
        resilience.STATE_FILE.write_text(
            '{"providers":{"pexels":{"open_until":"broken","probe_lease_until":"bad"}},'
            '"bad_assets":{"x":{"expires_at":"broken"}}}',
            encoding="utf-8",
        )
        allowed, reason, remaining = resilience.provider_gate("pexels")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0.0)
        diag = resilience.diagnostics()
        self.assertEqual(diag["bad_assets_active"], 0)

    def test_quarantine_rotates_primary_and_prunes_blocked_variants(self):
        primary = "https://example.test/a.jpg"
        blocked_variant = "https://example.test/b.jpg"
        good_variant = "https://example.test/c.jpg"
        candidate = {
            "fonte": "Pexels",
            "id": "asset-7",
            "url": primary,
            "_download_variants": [blocked_variant, good_variant],
        }
        resilience.mark_asset_bad(primary, provider="Pexels", asset_id="asset-7", reason="HTTP_403")
        resilience.mark_asset_bad(blocked_variant, provider="Pexels", asset_id="asset-7", reason="HTTP_403")
        filtered = resilience.filter_quarantined([candidate])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["url"], good_variant)
        self.assertEqual(filtered[0]["_download_variants"], [])

    def test_current_pexels_video_endpoint_is_used(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("https://api.pexels.com/v1/videos/search", text)
        self.assertNotIn("https://api.pexels.com/videos/search", text)

    def test_midia_integrates_circuits_quarantine_and_bounded_download(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_CIRCUIT=SKIP", text)
        self.assertIn("SAP_MEDIA_ASSET_QUARANTINE", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_MAX_MB", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_WALL_SECONDS", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_MAX_PIXELS", text)
        self.assertIn('"HTTP_401"', text)
        self.assertIn("SAP_MEDIA_SEMANTIC_REJECT", text)
        self.assertIn("candidato=candidato", text)

    def test_media_gate_surfaces_provider_health(self):
        text = (ROOT / "media_master_gate.py").read_text(encoding="utf-8")
        self.assertIn('"provider_health"', text)
        self.assertIn('"provider_circuits_open"', text)
        self.assertIn("Provider circuits abertos", text)

    def test_wikimedia_has_typed_failure_and_metadata_control(self):
        text = (ROOT / "wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("SAP_WIKIMEDIA_CIRCUIT=SKIP", text)
        self.assertIn('"MALFORMED"', text)
        self.assertIn('"wiki_metadata_strength"', text)
        self.assertIn("_sap_note_provider_items", text)


if __name__ == "__main__":
    unittest.main()
