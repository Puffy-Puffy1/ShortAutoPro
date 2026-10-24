import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_visual_verifier import verify_image_requirements


class MediaVisualVerifierTests(unittest.TestCase):
    def _image(self, directory: str) -> Path:
        path = Path(directory) / "scene_01.jpg"
        path.write_bytes(b"\xff\xd8\xff" + b"fixture-image-pixels" * 16)
        return path

    def _payload(self, *, tent=True, snow=True, people=False, confidence=0.97):
        return json.dumps({
            "must": [
                {
                    "anchor": "torn tent",
                    "visible": tent,
                    "confidence": confidence,
                    "evidence": "A tent wall has a visible tear.",
                },
                {
                    "anchor": "snow",
                    "visible": snow,
                    "confidence": confidence,
                    "evidence": "Snow is visible on the ground.",
                },
            ],
            "avoid": [{
                "anchor": "people",
                "visible": people,
                "confidence": confidence,
                "evidence": "No people are visible." if not people else "A person is visible.",
            }],
        })

    @patch("media_visual_verifier.generate_text")
    def test_passes_only_when_all_musts_are_visible_and_all_avoids_absent(self, generate):
        generate.return_value = self._payload()
        with tempfile.TemporaryDirectory() as directory:
            image = self._image(directory)
            result = verify_image_requirements(image, ["torn tent", "snow"], ["people"])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["method"], "gemini_image_pixels")
        self.assertEqual([row["anchor"] for row in result["must"]], ["torn tent", "snow"])
        self.assertEqual(result["avoid"][0]["visible"], False)
        self.assertEqual(generate.call_args.kwargs["image_mime_type"], "image/jpeg")
        self.assertEqual(generate.call_args.kwargs["image_data"][:3], b"\xff\xd8\xff")

    @patch("media_visual_verifier.generate_text")
    def test_blocks_missing_must_even_when_other_requirements_pass(self, generate):
        generate.return_value = self._payload(tent=False)
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory), ["torn tent", "snow"], ["people"]
            )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "must_visibility_failed")
        self.assertEqual(result["must"][0]["anchor"], "torn tent")
        self.assertFalse(result["must"][0]["visible"])
        self.assertEqual(result["must"][1]["anchor"], "snow")
        self.assertTrue(result["must"][1]["visible"])
        self.assertEqual(result["avoid"][0]["anchor"], "people")

    @patch("media_visual_verifier.generate_text")
    def test_blocks_visible_avoid_element(self, generate):
        generate.return_value = self._payload(people=True)
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory), ["torn tent", "snow"], ["people"]
            )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "avoid_visibility_failed")

    @patch("media_visual_verifier.generate_text")
    def test_scene_intent_is_checked_as_composition_not_a_literal_object(self, generate):
        payload = {
            "must": [{
                "anchor": "manuscript",
                "visible": True,
                "confidence": 0.98,
                "evidence": "A handwritten manuscript page fills the frame.",
            }],
            "avoid": [{
                "anchor": "digital screen",
                "visible": False,
                "confidence": 0.97,
                "evidence": "No screen or digital display is visible.",
            }],
            "scene_match": {
                "matches": True,
                "confidence": 0.97,
                "evidence": "The central subject is a historic manuscript page with literary writing.",
            },
        }
        generate.return_value = json.dumps(payload)
        intent = "historic poetry manuscript page Edgar Allan Poe"
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory),
                ["manuscript"],
                ["digital screen"],
                scene_intent=intent,
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["scene_match"]["intent"], intent)
        self.assertTrue(result["scene_match"]["matches"])
        prompt = generate.call_args.args[0]
        self.assertIn("high-level semantic match", prompt)
        self.assertIn(intent, prompt)

    @patch("media_visual_verifier.generate_text")
    def test_generic_winter_town_can_match_specific_location_intent(self, generate):
        payload = {
            "must": [
                {"anchor": anchor, "visible": True, "confidence": 0.97, "evidence": evidence}
                for anchor, evidence in [
                    ("building", "Old low-rise buildings line the street."),
                    ("snow", "Snow is visibly covering the roadside."),
                    ("street", "A street runs between the buildings."),
                ]
            ],
            "avoid": [{
                "anchor": "modern skyscrapers",
                "visible": False,
                "confidence": 0.97,
                "evidence": "No tall glass skyline or high-rise buildings are visible.",
            }],
            "scene_match": {
                "matches": True,
                "confidence": 0.95,
                "evidence": "The image depicts a snow-covered low-rise town street with older buildings.",
            },
        }
        generate.return_value = json.dumps(payload)
        intent = "russian provincial town winter snow streets old buildings"
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory),
                ["building", "snow", "street"],
                ["modern skyscrapers"],
                scene_intent=intent,
            )
        self.assertEqual(result["status"], "PASS")
        prompt = generate.call_args.args[0]
        self.assertIn("cannot be authenticated from pixels alone", prompt)
        self.assertIn("Mark matches=false only for a clear conflict", prompt)
        self.assertTrue(result["scene_match"]["matches"])

    @patch("media_visual_verifier.generate_text")
    def test_blocks_scene_mismatch_even_when_must_objects_are_visible(self, generate):
        payload = json.loads(self._payload())
        payload["scene_match"] = {
            "matches": False,
            "confidence": 0.98,
            "evidence": "Dolphins are underwater; there is no empty horizon.",
        }
        generate.return_value = json.dumps(payload)
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory),
                ["torn tent", "snow"],
                ["people"],
                scene_intent="empty ocean horizon aerial view",
            )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "scene_intent_mismatch")
        self.assertFalse(result["scene_match"]["matches"])

    @patch("media_visual_verifier.generate_text")
    def test_scene_intent_requires_a_valid_scene_match_response(self, generate):
        generate.return_value = self._payload()
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory),
                ["torn tent", "snow"],
                ["people"],
                scene_intent="historic manuscript page",
            )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "invalid_scene_match_schema")

    @patch("media_visual_verifier.generate_text")
    def test_scene_intent_can_be_verified_when_explicit_musts_are_empty(self, generate):
        payload = json.loads(self._payload())
        payload["must"] = []
        payload["avoid"] = []
        payload["scene_match"] = {
            "matches": True,
            "confidence": 0.96,
            "evidence": "A historic manuscript page fills the frame.",
        }
        generate.return_value = json.dumps(payload)
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory),
                [],
                [],
                scene_intent="historic manuscript page",
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["must"], [])
        self.assertTrue(result["scene_match"]["matches"])

    @patch("media_visual_verifier.generate_text")
    def test_blocks_uncertain_confidence_and_malformed_responses(self, generate):
        with tempfile.TemporaryDirectory() as directory:
            image = self._image(directory)
            generate.return_value = self._payload(confidence=0.75)
            uncertain = verify_image_requirements(image, ["torn tent", "snow"], ["people"])
            generate.return_value = "not json"
            malformed = verify_image_requirements(image, ["torn tent", "snow"], ["people"])
        self.assertEqual(uncertain["status"], "BLOCK")
        self.assertEqual(uncertain["reason"], "must_confidence_below_threshold")
        self.assertEqual(malformed["status"], "BLOCK")
        self.assertEqual(malformed["reason"], "visual_model_invalid_json")

    @patch("media_visual_verifier.generate_text", side_effect=RuntimeError("API unavailable"))
    def test_api_failure_blocks_instead_of_failing_open(self, _generate):
        with tempfile.TemporaryDirectory() as directory:
            result = verify_image_requirements(
                self._image(directory), ["torn tent", "snow"], ["people"]
            )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "visual_model_unavailable:RuntimeError")

    @patch("media_visual_verifier.generate_text")
    def test_invalid_image_file_is_rejected_before_model_call(self, generate):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-an-image.jpg"
            path.write_bytes(b"not an image" * 4)
            result = verify_image_requirements(path, ["torn tent"], [])
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "image_missing_invalid_or_too_large")
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
