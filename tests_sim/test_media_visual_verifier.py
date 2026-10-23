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
