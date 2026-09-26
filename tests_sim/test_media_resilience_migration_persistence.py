import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_external_resilience as mer


class MediaResilienceMigrationPersistenceTests(unittest.TestCase):
    def test_v11_transient_circuit_migration_is_persisted_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            state_file.write_text(json.dumps({
                "version": "1.1",
                "providers": {
                    "pixabay": {
                        "open_reason": "TIMEOUT",
                        "open_until": 9999999999.0,
                        "consecutive_failures": 9,
                        "last_failure_event": "TIMEOUT",
                        "last_failure_at": 123.0,
                    },
                    "wikimedia": {
                        "open_reason": "AUTH",
                        "open_until": 9999999999.0,
                        "consecutive_failures": 1,
                    },
                },
                "bad_assets": {},
                "updated_at": 0,
            }), encoding="utf-8")

            with (
                mock.patch.object(mer, "STATE_FILE", state_file),
                mock.patch.object(mer, "_STATE", None),
            ):
                state = mer._load()

            persisted = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["version"], mer.VERSION)
            self.assertEqual(persisted["version"], mer.VERSION)
            self.assertEqual(persisted["providers"]["pixabay"]["open_reason"], "")
            self.assertEqual(persisted["providers"]["pixabay"]["open_until"], 0.0)
            self.assertEqual(persisted["providers"]["pixabay"]["consecutive_failures"], 0)
            # Long-lived protection must not be erased by a transient migration.
            self.assertEqual(persisted["providers"]["wikimedia"]["open_reason"], "AUTH")


if __name__ == "__main__":
    unittest.main()
