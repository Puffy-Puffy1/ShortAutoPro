import base64
import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gemini_runtime

ROOT = Path(__file__).resolve().parents[1]


class GeminiRuntimeTests(unittest.TestCase):
    def _response(self, status, text="", payload=None):
        response = Mock()
        response.status_code = status
        response.ok = 200 <= status < 300
        response.text = text
        response.headers = {}
        if payload is not None:
            response.json.return_value = payload
        return response

    @patch("gemini_runtime.time.sleep", return_value=None)
    @patch("gemini_runtime.requests.post")
    def test_503_fails_over_to_next_model(self, post, _sleep):
        post.side_effect = [
            self._response(503, "high demand"),
            self._response(
                200,
                payload={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "ok"}]
                            }
                        }
                    ]
                },
            ),
        ]
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "SAP_GEMINI_ATTEMPTS_PER_MODEL": "1",
            },
            clear=False,
        ):
            result = gemini_runtime.generate_text(
                "hello",
                models=["model-a", "model-b"],
                component="Test",
            )
        self.assertEqual(result, "ok")
        self.assertEqual(post.call_count, 2)
        self.assertIn("model-a", post.call_args_list[0].args[0])
        self.assertIn("model-b", post.call_args_list[1].args[0])

    @patch("gemini_runtime.time.sleep", return_value=None)
    @patch("gemini_runtime.requests.post")
    def test_explicit_attempt_budget_fails_over_without_retrying_same_model(self, post, sleep):
        post.side_effect = [
            self._response(429, "rate limited"),
            self._response(
                200,
                payload={
                    "candidates": [{
                        "content": {"parts": [{"text": "ok"}]}
                    }]
                },
            ),
        ]
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "SAP_GEMINI_ATTEMPTS_PER_MODEL": "3",
            },
            clear=False,
        ):
            result = gemini_runtime.generate_text(
                "verify",
                models=["model-a", "model-b"],
                attempts_per_model=1,
                component="Visual test",
            )
        self.assertEqual(result, "ok")
        self.assertEqual(post.call_count, 2)
        self.assertIn("model-a", post.call_args_list[0].args[0])
        self.assertIn("model-b", post.call_args_list[1].args[0])
        sleep.assert_not_called()

    def test_missing_key_is_typed_temporary_failure(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with self.assertRaises(gemini_runtime.GeminiTemporaryUnavailable):
                gemini_runtime.generate_text("hello")

    @patch("gemini_runtime.requests.post")
    def test_image_bytes_use_shared_multimodal_runtime(self, post):
        post.return_value = self._response(
            200,
            payload={
                "candidates": [{
                    "content": {"parts": [{"text": '{"ok": true}'}]}
                }]
            },
        )
        image = b"\xff\xd8\xfffixture-image-bytes"
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key", "SAP_GEMINI_ATTEMPTS_PER_MODEL": "1"},
            clear=False,
        ):
            result = gemini_runtime.generate_text(
                "verify visible objects",
                response_mime_type="application/json",
                image_data=image,
                image_mime_type="image/jpeg",
                models=["model-image"],
                component="Visual test",
            )

        self.assertEqual(result, '{"ok": true}')
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "verify visible objects")
        self.assertEqual(
            payload["contents"][0]["parts"][1]["inline_data"],
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image).decode("ascii"),
            },
        )

    @patch("gemini_runtime.requests.post")
    def test_oversized_or_unsupported_inline_images_are_rejected(self, post):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with self.assertRaises(gemini_runtime.GeminiInvalidResponse):
                gemini_runtime.generate_text(
                    "verify",
                    image_data=b"x" * (6 * 1024 * 1024 + 1),
                    image_mime_type="image/jpeg",
                )
            with self.assertRaises(gemini_runtime.GeminiInvalidResponse):
                gemini_runtime.generate_text(
                    "verify",
                    image_data=b"small image",
                    image_mime_type="image/svg+xml",
                )
        post.assert_not_called()

    def test_default_timeout_is_mobile_bounded(self):
        text = (ROOT / "gemini_runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            'env_float("SAP_GEMINI_TIMEOUT", 28.0, 8.0, 60.0)',
            text,
        )


class GeminiUnificationContractTests(unittest.TestCase):
    def test_production_modules_do_not_call_generatecontent_directly(self):
        modules = [
            "topic_engine.py",
            "roteiro.py",
            "hook_engine.py",
            "narrative_director.py",
            "documentary_director.py",
            "cold_open_director.py",
            "scene_director.py",
            "visual_director.py",
        ]
        for module in modules:
            with self.subTest(module=module):
                text = (ROOT / module).read_text(encoding="utf-8")
                self.assertNotIn("generativelanguage.googleapis.com", text)
                self.assertNotIn("requests.post(", text)
                self.assertIn("gemini_runtime", text)

    def test_scene_director_has_offline_local_fallback(self):
        text = (ROOT / "scene_director.py").read_text(encoding="utf-8")
        self.assertIn("def fallback_local_scenes", text)
        self.assertIn("SCENE_DIRECTOR_FALLBACK=LOCAL_SEMANTIC_SPLIT", text)
        self.assertIn('os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")', text)

    def test_documentary_director_preserves_valid_input_on_ai_outage(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn("DOCUMENTARY_DIRECTOR=DEGRADED_FAIL_OPEN", text)
        self.assertIn('"preserved_original_scene_map": True', text)
        self.assertIn("raise SystemExit(0)", text)

    def test_topic_engine_runtime_paths_are_present(self):
        text = (ROOT / "topic_engine.py").read_text(encoding="utf-8")
        for name in (
            "HISTORICO",
            "SAIDA",
            "VERIFICACAO",
            "REJEITADOS_RUNTIME",
        ):
            self.assertIn(name + " =", text)


if __name__ == "__main__":
    unittest.main()
