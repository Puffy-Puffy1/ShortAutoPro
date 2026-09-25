import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
import media_must_priority
import media_must_verifier


class Stage6AnchorTimeoutAndIdFixTests(unittest.TestCase):
    def test_empty_golden_frames_becomes_picture_frame_anchor(self):
        result = media_must_priority.prioritize(
            ["empty golden frames", "wall"],
            query="empty ornate golden picture frames hanging on dark wall",
            visual_mode="object",
        )
        self.assertEqual(result["strict"], ["picture frame"])
        self.assertIn("empty golden frames", result["context"])
        self.assertIn("wall", result["context"])

    def test_picture_frame_aliases_match_plural_frame_metadata(self):
        candidate = {
            "description": "ornate vintage frames hanging in a gallery"
        }
        self.assertTrue(
            media_must_verifier.requirement_matches("picture frame", candidate)
        )

    def test_non_object_mode_keeps_count_but_normalizes_safe_modifiers(self):
        result = media_must_priority.prioritize(
            ["empty golden frames", "wall"],
            visual_mode="document",
        )
        self.assertEqual(
            result["strict"],
            ["frames", "wall"],
        )
        self.assertEqual(result["context"], ["empty golden frames"])

    def test_stale_short_id_with_existing_artifact_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            state.mkdir(parents=True)
            (state / "pipeline_old.json").write_text("{}", encoding="utf-8")

            with mock.patch.object(main, "BASE", base), \
                 mock.patch.object(main, "STATE_DIR", state), \
                 mock.patch.dict(os.environ, {"SHORT_ID": "old", "SAP_REUSE_SHORT_ID": "0"}, clear=False):
                allocated = main.allocate_id(reuse_existing=False)

            self.assertNotEqual(allocated, "old")

    def test_explicit_short_id_reuse_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            state.mkdir(parents=True)
            (state / "pipeline_old.json").write_text("{}", encoding="utf-8")

            with mock.patch.object(main, "BASE", base), \
                 mock.patch.object(main, "STATE_DIR", state), \
                 mock.patch.dict(os.environ, {"SHORT_ID": "old"}, clear=False):
                allocated = main.allocate_id(reuse_existing=True)

            self.assertEqual(allocated, "old")

    def test_parallel_provider_result_timeout_is_bounded(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        self.assertIn("SAP_MEDIA_PROVIDER_RESULT_TIMEOUT", text)
        self.assertIn("_PROVIDER_RESULT_TIMEOUT", text)
        self.assertIn("wait(", text)
        self.assertIn("timeout=_PROVIDER_RESULT_TIMEOUT", text)
        self.assertIn("round_deadline=", text)

    def test_parallel_provider_controller_timeout_does_not_poison_health(self):
        text = Path("midia.py").read_text(encoding="utf-8")
        self.assertIn("from concurrent.futures import", text)
        self.assertIn("wait", text)
        self.assertIn("SAP_MEDIA_PROVIDER_CONTROLLER_TIMEOUT", text)
        self.assertIn("health_penalty=NO", text)
        self.assertIn("SAP_MEDIA_PROVIDER_CIRCUIT_BACKOFF", text)

        start = text.index("if future not in _done:")
        end = text.index("continue", start)
        controller_block = text[start:end]
        self.assertNotIn("_sap_note_provider_event", controller_block)
        self.assertNotIn("_sap_note_provider_exception", controller_block)

    def test_wikimedia_multi_query_search_has_deadline(self):
        text = Path("wikimedia_source.py").read_text(encoding="utf-8")
        self.assertIn("SAP_WIKIMEDIA_SEARCH_DEADLINE", text)
        self.assertIn("SAP_WIKIMEDIA_DEADLINE=REACHED", text)
        self.assertIn("time.monotonic() - search_started", text)


if __name__ == "__main__":
    unittest.main()
