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
            candidate_low = {
                "fonte": "Mock", "id": "low", "tipo": "imagem", "must_hits": 1,
                "descricao": "ship at sea",
            }
            candidate_good = {
                "fonte": "Mock", "id": "good", "tipo": "imagem", "must_hits": 1,
                "descricao": "ship at sea",
            }
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
            candidate={"fonte":"Mock","id":"1","tipo":"imagem","must_hits":1,"descricao":"ship on the ocean"}
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

    def test_visual_fallback_checks_next_candidate_after_pixel_rejections(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            destination = media / "scene_04_wikimedia.jpg"
            candidates = [
                {
                    "fonte": "Wikimedia",
                    "id": "scene4-first-false-positive",
                    "tipo": "image",
                    "url": "https://example.test/scene_04_first.jpg",
                    "title": "Vintage Soviet hikers outdoors",
                    "must_hits": 1,
                    "avoid_hits": 0,
                    "score": 90,
                },
                {
                    "fonte": "Wikimedia",
                    "id": "scene4-second-false-positive",
                    "tipo": "image",
                    "url": "https://example.test/scene_04_second.jpg",
                    "title": "Soviet vintage scene outdoors",
                    "must_hits": 1,
                    "avoid_hits": 0,
                    "score": 80,
                },
                {
                    "fonte": "Wikimedia",
                    "id": "scene4-third-valid-candidate",
                    "tipo": "image",
                    "url": "https://example.test/scene_04_third.jpg",
                    "title": "Soviet people",
                    "must_hits": 1,
                    "avoid_hits": 0,
                    "score": 70,
                },
            ]

            def download(candidate, _number, _sid):
                destination.write_bytes(candidate["id"].encode("utf-8"))
                return True, str(destination), {}

            def validate(path):
                path = Path(path)
                return {
                    "sha256": media_engine_v2.sha256(path),
                    "probe": {"width": 1920, "height": 1080},
                }

            blocked = {
                "status": "BLOCK",
                "method": "gemini_image_pixels",
                "reason": "must_visibility_failed",
                "must": [
                    {"anchor": "people", "visible": True, "confidence": 0.97, "evidence": "people are visible"},
                    {"anchor": "winter clothing", "visible": False, "confidence": 0.95, "evidence": "winter clothing is not visible"},
                ],
                "avoid": [],
            }
            passed = {
                "status": "PASS",
                "method": "gemini_image_pixels",
                "must": [
                    {"anchor": "people", "visible": True, "confidence": 0.97, "evidence": "people are visible"},
                    {"anchor": "winter clothing", "visible": True, "confidence": 0.96, "evidence": "heavy winter clothing is visible"},
                ],
                "avoid": [],
            }

            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[candidates, candidates]
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[]
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 1, "total": 2, "missing": ["winter clothing"]},
            ), patch.object(
                media_engine_v2.PROVIDER, "download", side_effect=download
            ), patch.object(
                media_engine_v2, "validate_asset", side_effect=validate
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch(
                "media_visual_verifier.verify_image_requirements",
                side_effect=[blocked, blocked, passed],
            ) as visual_verify:
                result = media_engine_v2.acquire_scene(
                    "X",
                    4,
                    {
                        "query": "group of vintage Soviet skiers walking outdoors",
                        "must_have": ["people", "winter clothing"],
                        "avoid": [],
                    },
                    media,
                )

            self.assertEqual(visual_verify.call_count, 3)
            self.assertEqual(result["asset_id"], "scene4-third-valid-candidate")
            self.assertEqual(result["verification_mode"], "gemini_visual_must")
            self.assertEqual(result["evidence_class"], "visual_model")
            self.assertEqual(result["must_hits"], 2)
            self.assertEqual(result["metadata_must_hits"], 1)
            self.assertEqual(result["visual_verification"]["status"], "PASS")

    def test_visual_fallback_does_not_mutate_rejected_provider_candidates(self):
        candidate = {
            "fonte": "Wikimedia",
            "id": "rejected-without-context",
            "tipo": "image",
            "url": "https://example.test/people_winter.jpg",
            "title": "people in winter clothing",
            "must_hits": 2,
            "avoid_hits": 0,
            "score": 80,
        }
        original = dict(candidate)
        selected = media_engine_v2._visual_fallback_candidates(
            "group of vintage Soviet skiers walking outdoors",
            [candidate],
            must=["people", "winter clothing"],
            limit=2,
        )
        self.assertEqual(selected, [])
        self.assertEqual(candidate, original)

    def test_visual_fallback_rejects_candidates_matching_only_must_terms(self):
        candidate = {
            "fonte": "Wikimedia",
            "id": "must-only-context",
            "tipo": "image",
            "url": "https://example.test/people_winter_clothing.jpg",
            "title": "people in winter clothing",
            "must_hits": 2,
            "avoid_hits": 0,
            "score": 90,
        }
        selected = media_engine_v2._visual_fallback_candidates(
            "group of vintage Soviet skiers walking outdoors",
            [candidate],
            must=["people", "winter clothing"],
            limit=2,
        )
        self.assertEqual(selected, [])

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

    def test_visual_fallback_prioritizes_primary_must_over_background_only_hits(self):
        candidates = [
            {
                "fonte": "Wikimedia", "id": "snow-background", "tipo": "image",
                "url": "https://example.test/snow.jpg",
                "title": "Vintage snow-covered mountain winter landscape with drifting snow",
                "descricao": "Vintage snow-covered mountain winter landscape with drifting snow",
                "must_hits": 1, "avoid_hits": 0, "score": 100,
            },
            {
                "fonte": "Wikimedia", "id": "train-in-winter", "tipo": "image",
                "url": "https://example.test/train.jpg",
                "title": "A vintage train crossing a winter landscape",
                "descricao": "A vintage train crossing a winter landscape",
                "must_hits": 1, "avoid_hits": 0, "score": 50,
            },
        ]
        selected = media_engine_v2._visual_fallback_candidates(
            "vintage train traveling through snow winter landscape",
            candidates,
            must=["train", "snow"],
            limit=5,
        )
        self.assertTrue(selected, "the test candidates should be eligible for pixel verification")
        self.assertEqual(selected[0]["id"], "train-in-winter")
        self.assertLessEqual(len(selected), 5)

    def test_strict_provider_must_hits_are_reverified_against_asset_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            candidate = {
                "fonte": "Wikimedia",
                "id": "forged-must-hits",
                "tipo": "image",
                "url": "https://example.test/documents.jpg",
                "title": "Old paper documents on a table",
                "descricao": "Archival documents and paper pages",
                "must_hits": 1,
                "avoid_hits": 0,
                "score": 100,
                "query_relevance": {
                    "ok": True, "matched_terms": ["ship", "ocean"],
                    "matched_count": 2, "query_term_count": 4,
                    "required_terms": 1, "ratio": 0.5,
                },
            }
            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[candidate], [candidate]]
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[candidate]
            ), patch.object(
                media_engine_v2, "_visual_fallback_candidates", return_value=[]
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch.object(
                media_engine_v2.PROVIDER, "download"
            ) as download:
                with self.assertRaisesRegex(RuntimeError, "MEDIA_INCOMPLETE"):
                    media_engine_v2.acquire_scene(
                        "X", 1,
                        {"query": "historic ship crossing open ocean", "must_have": ["ship"]},
                        media,
                    )
            download.assert_not_called()


    def test_download_failure_uses_pixel_verified_fallback_before_blocking_scene(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            destination = media / "scene_01_wikimedia.jpg"
            strict_candidate = {
                "fonte": "Wikimedia",
                "id": "strict-bad-download",
                "tipo": "image",
                "url": "https://example.test/strict.jpg",
                "title": "Torn tent in snow beneath snowy mountains",
                "descricao": "Torn tent in snow beneath snowy mountains",
                "must_hits": 2,
                "avoid_hits": 0,
                "score": 95,
            }
            fallback_candidate = {
                "fonte": "Wikimedia",
                "id": "visual-fallback-valid",
                "tipo": "image",
                "url": "https://example.test/fallback.jpg",
                "title": "Torn canvas tent in a mountain landscape",
                "image_description": "A torn canvas tent in a mountain landscape",
                "descricao": "Torn canvas tent in a mountain landscape",
                "must_hits": 1,
                "avoid_hits": 0,
                "score": 80,
            }

            def evidence(candidate, _policy):
                if candidate["id"] == "strict-bad-download":
                    return {"hits": 2, "total": 2, "matched": ["torn tent", "snow"], "missing": []}
                return {"hits": 1, "total": 2, "matched": ["torn tent"], "missing": ["snow"]}

            def download(candidate, _number, _sid):
                if candidate["id"] == "strict-bad-download":
                    return False, "", {"error_class": "VALIDATION_FAILED"}
                destination.write_bytes(b"pixel-verified-fallback")
                return True, str(destination), {}

            def validate(path):
                path = Path(path)
                return {
                    "sha256": media_engine_v2.sha256(path),
                    "probe": {"width": 1920, "height": 1080},
                }

            passed = {
                "status": "PASS",
                "method": "gemini_image_pixels",
                "must": [
                    {"anchor": "torn tent", "visible": True, "confidence": 0.97, "evidence": "torn tent is visible"},
                    {"anchor": "snow", "visible": True, "confidence": 0.96, "evidence": "snow is visible"},
                ],
                "avoid": [
                    {"anchor": "people", "visible": False, "confidence": 0.97, "evidence": "no people visible"}
                ],
            }

            with patch.object(
                media_engine_v2.PROVIDER,
                "search",
                side_effect=[
                    [strict_candidate, fallback_candidate],
                    [strict_candidate, fallback_candidate],
                ],
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[strict_candidate]
            ), patch(
                "media_must_verifier.verified_must", side_effect=evidence
            ), patch.object(
                media_engine_v2.PROVIDER, "download", side_effect=download
            ) as download_mock, patch.object(
                media_engine_v2, "validate_asset", side_effect=validate
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch(
                "media_visual_verifier.verify_image_requirements", return_value=passed
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

            self.assertEqual(
                [call.args[0]["id"] for call in download_mock.call_args_list],
                ["strict-bad-download", "visual-fallback-valid"],
            )
            self.assertEqual(result["asset_id"], "visual-fallback-valid")
            self.assertEqual(result["verification_mode"], "gemini_visual_must")
            self.assertEqual(result["visual_verification"]["status"], "PASS")
            self.assertEqual(result["metadata_must_hits"], 1)


    def test_icon_library_artwork_is_rejected_for_documentary_photo_scene(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            icon_candidate = {
                "fonte": "Wikimedia",
                "id": "pinhead-icon",
                "tipo": "image",
                "url": "https://example.test/person-walking.svg.png",
                "title": "Person walking in shelter Pinhead icon",
                "descricao": "Plain black vector icon depicting a person walking",
                "must_hits": 1,
                "avoid_hits": 0,
                "score": 100,
            }
            with patch.object(
                media_engine_v2.PROVIDER, "search",
                side_effect=[[icon_candidate], [icon_candidate]],
            ), patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[icon_candidate]
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch.object(
                media_engine_v2.PROVIDER, "download"
            ) as download:
                with self.assertRaisesRegex(RuntimeError, "MEDIA_INCOMPLETE"):
                    media_engine_v2.acquire_scene(
                        "X", 7,
                        {
                            "query": "person walking through an old mountain shelter",
                            "must_have": ["person walking"],
                            "avoid": [],
                        },
                        media,
                    )
            download.assert_not_called()

    def test_icon_assets_are_allowed_when_the_scene_explicitly_requests_icons(self):
        candidate = {
            "title": "Simple black icon of a walking person",
            "descricao": "Vector pictogram",
        }
        self.assertFalse(
            media_engine_v2._is_non_photographic_asset(candidate, "minimal walking person icon")
        )


    def test_targeted_visual_search_queries_missing_must_with_context(self):
        queries = media_engine_v2._targeted_visual_search_queries(
            "plotting course on aeronautical navigation map",
            ["map", "pencil"],
        )
        self.assertEqual(
            queries,
            ["pencil plotting course aeronautical navigation"],
        )

    def test_targeted_visual_search_recovers_asset_only_after_pixel_verification(self):
        with tempfile.TemporaryDirectory() as td:
            media = Path(td) / "media"
            media.mkdir()
            destination = media / "scene_06_wikimedia.jpg"
            candidate = {
                "fonte": "Wikimedia",
                "id": "targeted-map-pencil",
                "tipo": "image",
                "url": "https://example.test/aeronautical-map-pencil.jpg",
                "title": "Aeronautical navigation chart with pencil",
                "descricao": "Aeronautical navigation chart with pencil",
                "must_hits": 0,
                "avoid_hits": 0,
                "score": 50,
            }

            def download(item, _number, _sid):
                destination.write_bytes(item["id"].encode("utf-8"))
                return True, str(destination), {}

            passed = {
                "status": "PASS",
                "method": "gemini_image_pixels",
                "must": [
                    {"anchor": "map", "visible": True, "confidence": 0.97},
                    {"anchor": "pencil", "visible": True, "confidence": 0.96},
                ],
                "avoid": [],
            }

            with patch.object(
                media_engine_v2.PROVIDER, "search", side_effect=[[], [], [candidate]]
            ) as search, patch.object(
                media_engine_v2.PROVIDER, "prepare", return_value=[]
            ), patch(
                "media_provider_router_v2.query_relevance",
                return_value={
                    "ok": True,
                    "matched_terms": ["aeronautical", "navigation", "map", "pencil"],
                    "matched_count": 4,
                },
            ), patch(
                "media_must_verifier.verified_must",
                return_value={"hits": 0, "total": 2, "matched": [], "missing": ["map", "pencil"]},
            ), patch.object(
                media_engine_v2.PROVIDER, "download", side_effect=download
            ), patch.object(
                media_engine_v2, "validate_asset",
                side_effect=lambda path: {
                    "sha256": media_engine_v2.sha256(Path(path)),
                    "probe": {"width": 1920, "height": 1080},
                },
            ), patch.object(
                media_engine_v2, "_local_library_asset", return_value=None
            ), patch(
                "media_visual_verifier.verify_image_requirements", return_value=passed
            ):
                result = media_engine_v2.acquire_scene(
                    "X",
                    6,
                    {
                        "query": "plotting course on aeronautical navigation map",
                        "must_have": ["map", "pencil"],
                        "avoid": ["tablet", "neon light"],
                    },
                    media,
                )

            self.assertEqual(
                search.call_args_list[2].args[0],
                "pencil plotting course aeronautical navigation",
            )
            self.assertEqual(result["asset_id"], "targeted-map-pencil")
            self.assertEqual(result["verification_mode"], "gemini_visual_must")
            self.assertEqual(result["visual_verification"]["status"], "PASS")

if __name__=="__main__": unittest.main()
