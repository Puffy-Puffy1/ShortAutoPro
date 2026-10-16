import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import media_external_resilience as resilience
import media_provider_router_v2 as media_router

ROOT = Path(__file__).resolve().parents[1]


class MediaExternalResilienceTests(unittest.TestCase):
    def test_wikimedia_download_sends_identifiable_user_agent(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.ok = True
        response.iter_content.return_value = [b"fake-image-bytes"]
        candidate = {
            "fonte": "wikimedia", "source": "wikimedia", "tipo": "image",
            "id": "123", "url": "https://upload.wikimedia.org/example.jpg",
            "provenance": {"provider": "wikimedia"},
        }
        with (
            tempfile.TemporaryDirectory() as root,
            patch.object(media_router, "BASE", Path(root)),
            patch.object(media_router, "asset_blocked", return_value=(False, "", 0)),
            patch.object(media_router, "validate", return_value={"valid": True}),
            patch.object(media_router.requests, "get", return_value=response) as get,
        ):
            ok, path, _ = media_router.MediaProviderRouterV2(providers=[]).download(
                candidate, scene_number=1, short_id="header-test"
            )
            self.assertTrue(ok)
            self.assertTrue(Path(path).is_file())
            kwargs = get.call_args.kwargs
            self.assertIn("User-Agent", kwargs["headers"])
            self.assertIn("ShortAutoPro/2.3", kwargs["headers"]["User-Agent"])
            self.assertIn("contact:", kwargs["headers"]["User-Agent"])
            self.assertEqual(kwargs["stream"], True)

    def test_non_wikimedia_download_also_sends_user_agent(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.ok = True
        response.iter_content.return_value = [b"fake-image-bytes"]
        candidate = {
            "fonte": "pexels", "tipo": "image", "id": "456",
            "url": "https://images.example.test/example.jpg",
        }
        with (
            tempfile.TemporaryDirectory() as root,
            patch.object(media_router, "BASE", Path(root)),
            patch.object(media_router, "asset_blocked", return_value=(False, "", 0)),
            patch.object(media_router, "validate", return_value={"valid": True}),
            patch.object(media_router.requests, "get", return_value=response) as get,
        ):
            ok, _, _ = media_router.MediaProviderRouterV2(providers=[]).download(
                candidate, scene_number=1, short_id="header-test"
            )
        self.assertTrue(ok)
        self.assertIn("User-Agent", get.call_args.kwargs["headers"])

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

    def test_persistent_empty_results_do_not_poison_provider_health(self):
        """Empty results are query-specific, not evidence of provider outage."""
        class Response:
            status_code = 200
            headers = {}

        for _ in range(4):
            resilience.note_response("pexels_foto", Response())
            resilience.note_items("pexels_foto", [])

        allowed, reason, remaining = resilience.provider_gate("pexels_video")
        self.assertTrue(allowed)
        # provider_gate uses CLOSED as its explicit healthy-state reason.
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0)

    def test_same_family_transient_burst_is_deduplicated(self):
        resilience.note_provider_event("pixabay_video", "TIMEOUT")
        resilience.note_provider_event("pixabay_foto", "TIMEOUT")

        allowed, reason, remaining = resilience.provider_gate("pixabay_video")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0)

        state = resilience._load()["providers"]["pixabay"]
        self.assertEqual(state.get("consecutive_failures"), 1)
        self.assertGreaterEqual(state.get("deduped_failures", 0), 1)

        # Three genuinely separated transient failures still open the circuit.
        state["last_failure_at"] -= resilience.TRANSIENT_DEDUP_SECONDS + 1
        resilience.note_provider_event("pixabay_video", "TIMEOUT")
        state["last_failure_at"] -= resilience.TRANSIENT_DEDUP_SECONDS + 1
        resilience.note_provider_event("pixabay_video", "TIMEOUT")

        allowed, reason, remaining = resilience.provider_gate("pixabay_foto")
        self.assertFalse(allowed)
        self.assertEqual(reason, "TIMEOUT")
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 8.5)

    def test_upgrade_clears_v11_transient_circuit_debt(self):
        resilience.STATE_FILE.write_text(
            '{"version":"1.1","providers":{"pixabay":{"open_until":9999999999,'
            '"open_reason":"TIMEOUT","consecutive_failures":9}},'
            '"bad_assets":{}}',
            encoding="utf-8",
        )
        resilience._STATE = None

        allowed, reason, remaining = resilience.provider_gate("pixabay_video")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0)

    def test_empty_response_resets_transient_failure_debt(self):
        resilience.note_provider_event("coverr_video", "TIMEOUT")
        resilience.note_provider_event("coverr_video", "EMPTY", item_count=0)
        resilience.note_provider_event("coverr_video", "TIMEOUT")

        state = resilience._load()["providers"]["coverr"]
        self.assertEqual(state.get("consecutive_failures"), 1)
        allowed, _, _ = resilience.provider_gate("coverr_video")
        self.assertTrue(allowed)

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

    def test_semantic_local_library_is_a_verified_retrieval_tier(self):
        import hashlib
        import shortauto_asset_library as library

        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            asset = root_path / "accepted_book.jpg"
            asset.write_bytes(b"accepted-real-media" * 200)
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            library.STATE = root_path / "asset_library.json"
            library.atomic(
                library.STATE,
                {
                    "version": "ASSET_LIBRARY_1.0",
                    "assets": [{
                        "asset_id": "sha256:" + digest[:16],
                        "sha256": digest,
                        "file": "scene_01.jpg",
                        "path": str(asset),
                        "width": 1200,
                        "height": 1600,
                        "source": "Pixabay",
                        "license": "Pixabay Content License",
                        "entities": ["book", "pages"],
                        "location": "",
                        "year_or_era": "antique",
                        "visual_style": "document",
                        "quality": 92,
                        "used_count": 0,
                        "short_ids": ["old-short"],
                    }],
                },
            )
            candidates = library.search_candidates(
                "old antique leather bound poetry book open pages",
                ["book", "pages"],
                [],
            )
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["fonte"], "LocalLibrary")
            self.assertEqual(candidates[0]["must_hits"], 2)
            self.assertEqual(candidates[0]["source"], "Pixabay")
            self.assertTrue(candidates[0]["sha256"] == digest)

        library.STATE = library.BASE / ".sap_state" / "asset_library.json"

    def test_midia_has_hash_verified_local_library_copy_path(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("_sap_local_library_candidates", text)
        self.assertIn('fonte") == "LocalLibrary"', text)
        self.assertIn("expected_sha", text)
        self.assertIn("HASH_MISMATCH", text)
        self.assertIn("SAP_MEDIA_LOCAL_LIBRARY=MERGED", text)

    def test_midia_integrates_circuits_quarantine_and_bounded_download(self):
        text = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_CIRCUIT=SKIP", text)
        self.assertIn("_sap_asset_blocked", text)
        self.assertIn("_sap_mark_asset_bad", text)
        self.assertIn("_sap_filter_quarantined", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_MAX_MB", text)
        self.assertIn("SAP_MEDIA_DOWNLOAD_WALL_SECONDS", text)
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
