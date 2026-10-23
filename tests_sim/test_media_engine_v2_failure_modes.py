import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import media_engine_v2

class MediaEngineV2FailureTests(unittest.TestCase):

    def test_critical_low_resolution_candidate_is_rejected_and_next_candidate_used(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            destination = media / "scene_01.jpg"
            candidate_low = {"fonte": "Mock", "id": "low", "tipo": "imagem", "must_hits": 1}
            candidate_good = {"fonte": "Mock", "id": "good", "tipo": "imagem", "must_hits": 1}
            def download(candidate, number, sid):
                destination.write_bytes(b"asset-bytes-" + candidate["id"].encode())
                return True, str(destination), {}
            def validate(path):
                is_low = b"low" in Path(path).read_bytes()
                return {
                    "sha256": media_engine_v2.sha256(Path(path)),
                    "probe": {"width": 100, "height": 100} if is_low else {"width": 1920, "height": 1080},
                }
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[candidate_low, candidate_good]), \
                 patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[candidate_low, candidate_good]), \
                 patch.object(media_engine_v2.PROVIDER, "download", side_effect=download), \
                 patch.object(media_engine_v2, "validate_asset", side_effect=validate), \
                 patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                result = media_engine_v2.acquire_scene(
                    "X", 1, {"query": "ship", "must_have": ["ship"]}, media
                )
            self.assertEqual(result["asset_id"], "good")
            self.assertEqual(result["probe"]["width"], 1920)

    def test_minimum_visual_resolution_matches_visual_qa_critical_threshold(self):
        self.assertIsNotNone(media_engine_v2._resolution_issue({"width": 100, "height": 100}))
        self.assertIsNone(media_engine_v2._resolution_issue({"width": 320, "height": 180}))
        self.assertIsNotNone(media_engine_v2._resolution_issue({"width": 0, "height": 0}))

    def test_empty_provider_is_media_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media=base/"imagens"/"short_X"; media.mkdir(parents=True)
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[]), patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_INCOMPLETE"):
                    media_engine_v2.acquire_scene("X", 1, {"query":"ship","must_have":["ship"]}, media)

    def test_download_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media=base/"imagens"/"short_X"; media.mkdir(parents=True)
            candidate={"fonte":"Mock","id":"1","tipo":"imagem","must_hits":1}
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "download", return_value=(False, str(media/"scene_01.jpg"), {"error_class":"DOWNLOAD_FAILED"})),                  patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_DOWNLOAD_FAILED"):
                    media_engine_v2.acquire_scene("X",1,{"query":"ship","must_have":["ship"]},media)

    def test_local_library_is_only_fallback_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media = base/"imagens"/"short_X"
            media.mkdir(parents=True)
            asset = media/"scene_01.jpg"
            asset.write_bytes(b"valid-local-asset")
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[]), \
                 patch.object(media_engine_v2, "_local_library_asset", return_value={
                     "source":"LocalLibrary","asset_id":"sha256:test",
                     "path":str(asset),"checksum_sha256":"expected","validated":True
                 }) as local:
                result = media_engine_v2.acquire_scene(
                    "X", 1, {"query":"ship","must_have":["ship"]}, media
                )
                local.assert_called_once()
                self.assertEqual(result["source"], "LocalLibrary")

    def test_relaxed_verified_candidate_keeps_must_hits_in_manifest_record(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            destination = media / "scene_01.jpg"
            destination.write_bytes(b"mock image bytes")
            candidate = {
                "fonte": "Mock", "id": "verified-1", "tipo": "imagem",
                "must_hits": 0, "avoid_hits": 0, "score": 80,
                "descricao": "ship on the ocean",
            }
            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]
            ) as search, patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[]
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 1, "total": 1, "missing": []},
            ), patch.object(
                media_engine_v2.PROVIDER,
                "download",
                return_value=(True, str(destination), {}),
            ), patch.object(
                media_engine_v2, "validate_asset",
                return_value={"sha256": media_engine_v2.sha256(destination), "probe": {"width": 1920, "height": 1080}},
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ):
                result = media_engine_v2.acquire_scene(
                    "X", 1, {"query": "long query", "must_have": ["ship"]}, media
                )
            self.assertEqual(search.call_args_list[1].args[0], "long query ship")
            self.assertEqual(result["must_hits"], 1)
            self.assertEqual(result["must_total"], 1)
            self.assertEqual(result["verification_mode"], "strict_evidence_query_relaxed")

    def test_relaxed_query_does_not_accept_irrelevant_asset_even_if_must_matches(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            candidate = {
                "fonte": "Wikimedia", "id": "generic-money-image", "tipo": "imagem",
                "must_hits": 1, "avoid_hits": 0, "score": 100,
                "descricao": "Portrait of Lord Buddha created with money",
                "query_relevance": {
                    "ok": False, "matched_terms": ["money"],
                    "matched_count": 1, "query_term_count": 6,
                    "required_terms": 4, "ratio": 0.167,
                },
            }
            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[candidate]
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 1, "total": 1, "missing": []},
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ):
                with self.assertRaisesRegex(RuntimeError, "query_relevance_rejected=1"):
                    media_engine_v2.acquire_scene(
                        "X", 1,
                        {"query": "bundle of twenty dollar bills ransom money", "must_have": ["money"]},
                        media,
                    )

    def test_query_relaxation_requires_independent_must_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media = base/"imagens"/"short_X"
            media.mkdir(parents=True)
            candidate = {
                "fonte": "Mock", "id": "1", "tipo": "imagem",
                "must_hits": 0, "avoid_hits": 0, "score": 80,
                "descricao": "ship on the ocean",
            }
            with patch.object(
                media_engine_v2.PROVIDER,
                "search",
                side_effect=[[candidate], [candidate]],
            ), patch.object(
                media_engine_v2.PROVIDER,
                "prepare",
                return_value=[],
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 0, "total": 1},
            ), patch.object(
                media_engine_v2,
                "_local_library_asset",
                return_value=None,
            ):
                with self.assertRaisesRegex(RuntimeError, "no_verified_asset"):
                    media_engine_v2.acquire_scene(
                        "X", 1, {"query": "long query", "must_have": ["ship"]}, media
                    )

            with patch.object(
                media_engine_v2.PROVIDER,
                "search",
                side_effect=[[candidate], [candidate]],
            ), patch.object(
                media_engine_v2.PROVIDER,
                "prepare",
                return_value=[],
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 1, "total": 1},
            ), patch.object(
                media_engine_v2.PROVIDER,
                "download",
                return_value=(False, "", {"error_class": "DOWNLOAD_FAILED"}),
            ), patch.object(
                media_engine_v2,
                "_local_library_asset",
                return_value=None,
            ):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_DOWNLOAD_FAILED"):
                    media_engine_v2.acquire_scene(
                        "X", 1, {"query": "long query", "must_have": ["ship"]}, media
                    )

    def test_visual_fallback_accepts_only_after_pixel_verification_passes(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media = base / "imagens" / "short_X"
            media.mkdir(parents=True)
            destination = media / "scene_01_wikimedia.jpg"
            candidate = {
                "fonte": "Wikimedia",
                "id": "pixel-fixture",
                "tipo": "image",
                "url": "https://example.test/scene_01.jpg",
                "title": "Torn tent in snow beneath snowy mountains",
                "image_description": "A torn tent in a snowy mountain landscape",
                "descricao": "Torn tent in snow beneath snowy mountains",
                "must_hits": 0,
                "avoid_hits": 0,
                "score": 80,
            }

            def download(_candidate, _number, _sid):
                destination.write_bytes(b"mock image data")
                return True, str(destination), {}

            def validate(path):
                path = Path(path)
                return {
                    "sha256": media_engine_v2.sha256(path),
                    "probe": {"width": 1920, "height": 1080},
                }

            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[]
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 0, "total": 2, "missing": ["torn tent", "snow"]},
            ), patch.object(
                media_engine_v2.PROVIDER, "download", side_effect=download
            ), patch.object(
                media_engine_v2, "validate_asset", side_effect=validate
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch(
                "media_visual_verifier.verify_image_requirements",
                return_value={
                    "status": "PASS",
                    "method": "gemini_image_pixels",
                    "must": [
                        {"anchor": "torn tent", "visible": True, "confidence": 0.97, "evidence": "visible tear"},
                        {"anchor": "snow", "visible": True, "confidence": 0.98, "evidence": "snow on ground"},
                    ],
                    "avoid": [
                        {"anchor": "people", "visible": False, "confidence": 0.97, "evidence": "no people visible"}
                    ],
                },
            ):
                result = media_engine_v2.acquire_scene(
                    "X",
                    1,
                    {
                        "query": "torn vintage canvas tent fabric in snowy mountain landscape",
                        "must_have": ["torn tent", "snow"],
                        "avoid": ["people"],
                    },
                    media,
                )

            self.assertEqual(result["verification_mode"], "gemini_visual_must")
            self.assertEqual(result["evidence_class"], "visual_model")
            self.assertEqual(result["must_hits"], 2)
            self.assertEqual(result["metadata_must_hits"], 0)
            self.assertEqual(result["visual_verification"]["status"], "PASS")

    def test_visual_fallback_blocks_and_deletes_image_when_avoid_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media = base / "imagens" / "short_X"
            media.mkdir(parents=True)
            destination = media / "scene_01_wikimedia.jpg"
            candidate = {
                "fonte": "Wikimedia",
                "id": "blocked-pixel-fixture",
                "tipo": "image",
                "url": "https://example.test/scene_01.jpg",
                "title": "Torn tent in snow beneath snowy mountains",
                "image_description": "A torn tent in a snowy mountain landscape",
                "descricao": "Torn tent in snow beneath snowy mountains",
                "must_hits": 0,
                "avoid_hits": 0,
                "score": 80,
            }

            def download(_candidate, _number, _sid):
                destination.write_bytes(b"mock image data")
                return True, str(destination), {}

            def validate(path):
                path = Path(path)
                return {
                    "sha256": media_engine_v2.sha256(path),
                    "probe": {"width": 1920, "height": 1080},
                }

            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[]
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 0, "total": 2, "missing": ["torn tent", "snow"]},
            ), patch.object(
                media_engine_v2.PROVIDER, "download", side_effect=download
            ), patch.object(
                media_engine_v2, "validate_asset", side_effect=validate
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch(
                "media_visual_verifier.verify_image_requirements",
                return_value={"status": "BLOCK", "reason": "avoid_visibility_failed"},
            ):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_INCOMPLETE"):
                    media_engine_v2.acquire_scene(
                        "X",
                        1,
                        {
                            "query": "torn vintage canvas tent fabric in snowy mountain landscape",
                            "must_have": ["torn tent", "snow"],
                            "avoid": ["people"],
                        },
                        media,
                    )
            self.assertFalse(destination.exists())

if __name__=="__main__": unittest.main()
