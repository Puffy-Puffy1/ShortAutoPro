import tempfile
import unittest
from pathlib import Path

import media_resilience as mr


class MediaExternalResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        mr.BASE = root
        mr.STATE_DIR = root / ".sap_state" / "media_resilience"
        mr.CACHE_DIR = root / ".sap_cache" / "media"
        mr.QUERY_STATE = mr.STATE_DIR / "query_cache.json"
        mr.PROVIDER_STATE = mr.STATE_DIR / "provider_health.json"
        mr.QUARANTINE_STATE = mr.STATE_DIR / "url_quarantine.json"
        mr.BLOB_INDEX = mr.STATE_DIR / "blob_index.json"
        mr.LOCK_FILE = mr.STATE_DIR / ".lock"

    def tearDown(self):
        self.tmp.cleanup()

    def test_403_api_opens_provider_circuit(self):
        mr.record_provider_result(
            "wikimedia",
            ok=False,
            status_code=403,
            reason="auth",
        )
        allowed, reason = mr.provider_allowed("wikimedia")
        self.assertFalse(allowed)
        self.assertEqual(reason, "auth")

    def test_rate_limit_respects_retry_after(self):
        before = mr._now()
        record = mr.record_provider_result(
            "pixabay",
            ok=False,
            status_code=429,
            reason="rate_limit",
            retry_after=120,
        )
        self.assertGreaterEqual(
            float(record.get("circuit_until", 0)),
            before + 119,
        )

    def test_success_resets_provider_circuit(self):
        mr.record_provider_result(
            "coverr",
            ok=False,
            status_code=503,
            reason="server",
        )
        mr.record_provider_result(
            "coverr",
            ok=True,
            status_code=200,
        )
        allowed, reason = mr.provider_allowed("coverr")
        self.assertTrue(allowed)
        self.assertEqual(reason, "OK")

    def test_quarantine_blocks_removed_url_only(self):
        bad = "https://example.invalid/removed.jpg"
        good = "https://example.invalid/other.jpg"
        mr.quarantine_url(
            bad,
            reason="http_404",
            status_code=404,
        )
        self.assertFalse(mr.url_allowed(bad)[0])
        self.assertTrue(mr.url_allowed(good)[0])

    def test_query_cache_survives_provider_outage(self):
        payload = {
            "query": "edgar allan poe portrait",
            "limit": 12,
        }
        rows = [{"id": 1, "title": "File:Edgar Allan Poe.jpg"}]
        mr.cache_query_result("wikimedia", payload, rows)
        cached, state = mr.get_cached_query(
            "wikimedia",
            payload,
            allow_stale=True,
        )
        self.assertEqual(state, "FRESH")
        self.assertEqual(cached, rows)

    def test_validated_blob_can_be_restored_without_network(self):
        src = Path(self.tmp.name) / "source.bin"
        src.write_bytes(b"x" * 4096)
        url = "https://cdn.example.invalid/media/asset.jpg"
        self.assertTrue(
            mr.cache_validated_media(
                url,
                src,
                provider="example",
                metadata={
                    "candidate": {
                        "fonte": "Example",
                        "tipo": "foto",
                        "descricao": "historical portrait",
                        "url": url,
                    }
                },
            )
        )
        dest = Path(self.tmp.name) / "restored.jpg"
        self.assertTrue(mr.restore_cached_media(url, dest))
        self.assertEqual(dest.read_bytes(), src.read_bytes())

    def test_corrupted_cached_blob_is_rejected(self):
        src = Path(self.tmp.name) / "source.bin"
        src.write_bytes(b"a" * 4096)
        url = "https://cdn.example.invalid/media/corrupt.jpg"
        self.assertTrue(mr.cache_validated_media(url, src))
        record = mr.cached_media_candidates()
        # No candidate metadata was stored, so semantic reuse is intentionally absent.
        self.assertEqual(record, [])

        index = mr._load(mr.BLOB_INDEX, {"items": {}})
        item = next(iter(index["items"].values()))
        Path(item["blob"]).write_bytes(b"tampered")
        dest = Path(self.tmp.name) / "restored.jpg"
        self.assertFalse(mr.restore_cached_media(url, dest))

    def test_cache_prune_is_bounded(self):
        for i in range(3):
            src = Path(self.tmp.name) / f"src_{i}.bin"
            src.write_bytes(bytes([65 + i]) * 4096)
            mr.cache_validated_media(
                f"https://cache.invalid/{i}.jpg",
                src,
            )
        result = mr.prune_cache(
            max_bytes=5000,
            max_age_days=30,
        )
        self.assertLessEqual(result["remaining_bytes"], 5000)


class Stage6ResilienceContractTests(unittest.TestCase):
    def test_downloader_restores_cache_before_network(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        restore_at = text.index("_sap_restore_cached_media")
        request_at = text.index('_sap_http_session("download").get')
        self.assertLess(restore_at, request_at)

    def test_offline_reuse_rechecks_current_musts(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        self.assertIn("_sap_mustv.verified_must", text)
        self.assertIn('if candidate["must_hits"] < total_must:', text)
        self.assertIn("avaliar_evidencia(", text)

    def test_stage_reports_resilience_state(self):
        text = Path("media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn("MEDIA_RESILIENCE ", text)
        self.assertIn("open_circuits=", text)
        self.assertIn("quarantine=", text)


if __name__ == "__main__":
    unittest.main()
