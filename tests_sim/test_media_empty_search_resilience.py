import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_external_resilience as resilience


class EmptySearchResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tmp.name) / "state.json"
        self.state_patch = mock.patch.object(resilience, "STATE_FILE", self.state_file)
        self.state_patch.start()
        resilience._STATE = None

    def tearDown(self):
        resilience._STATE = None
        self.state_patch.stop()
        self.tmp.cleanup()

    def test_repeated_empty_queries_do_not_open_provider_health_circuit(self):
        for _ in range(12):
            resilience.note_items("wikimedia", [])
        allowed, reason, remaining = resilience.provider_gate("wikimedia")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0.0)

    def test_legacy_empty_circuit_is_cleared_on_gate(self):
        resilience._STATE = {
            "version": "1.0",
            "providers": {
                "wikimedia": {
                    "open_until": 99999999999.0,
                    "open_reason": "EMPTY",
                    "empty_streak": 8,
                }
            },
            "bad_assets": {},
            "updated_at": 0.0,
        }
        allowed, reason, remaining = resilience.provider_gate("wikimedia")
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLOSED")
        self.assertEqual(remaining, 0.0)

    def test_real_separated_timeouts_still_open_circuit(self):
        resilience.note_provider_event("pixabay_video", "TIMEOUT")
        state = resilience._load()["providers"]["pixabay"]
        state["last_failure_at"] -= resilience.TRANSIENT_DEDUP_SECONDS + 1
        resilience.note_provider_event("pixabay_foto", "TIMEOUT")
        state["last_failure_at"] -= resilience.TRANSIENT_DEDUP_SECONDS + 1
        resilience.note_provider_event("pixabay_video", "TIMEOUT")

        allowed, reason, remaining = resilience.provider_gate("pixabay")
        self.assertFalse(allowed)
        self.assertEqual(reason, "TIMEOUT")
        self.assertGreater(remaining, 0.0)
        self.assertLessEqual(remaining, 8.5)


if __name__ == "__main__":
    unittest.main()
