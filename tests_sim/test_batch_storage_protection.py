import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import storage_manager as sm


class BatchStorageProtectionTests(unittest.TestCase):
    def test_retry_pending_batch_item_is_protected_from_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "queue").mkdir(parents=True)
            (base / "imagens" / "short_batch_02").mkdir(parents=True)
            (base / "queue" / "batch_state.json").write_text(json.dumps({
                "version": "BATCH_STATE_3.0_PER_ITEM",
                "items": [
                    {"short_id": "batch_02", "status": "retry_pending"},
                    {"short_id": "batch_03", "status": "queued"},
                ],
            }), encoding="utf-8")
            with (
                mock.patch.object(sm, "BASE", base),
                mock.patch.object(sm, "SID", ""),
            ):
                ids = sm.active_ids()
                self.assertIn("batch_02", ids)
                self.assertNotIn("batch_03", ids)
                self.assertTrue(sm.protected(base / "imagens" / "short_batch_02"))


if __name__ == "__main__":
    unittest.main()
