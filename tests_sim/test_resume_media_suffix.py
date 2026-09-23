import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import production_doctor
import resume_short_runtime


class CanonicalMediaSuffixTests(unittest.TestCase):
    def test_resume_accepts_suffixed_primary_asset_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "suffix"
            (base / "roteiros").mkdir(parents=True)
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            (base / "roteiros" / f"media_quality_{sid}.json").write_text(
                json.dumps({"status": "PASS", "critical": False}),
                encoding="utf-8",
            )
            for number in range(1, 7):
                (media / f"scene_{number:02d}_primary.jpg").write_bytes(b"x" * 2048)

            with mock.patch.object(resume_short_runtime, "BASE", base), \
                 mock.patch.dict(os.environ, {"SHORT_QTD_CENAS": "6"}, clear=False):
                self.assertTrue(resume_short_runtime.media_ok(sid))

    def test_production_doctor_counts_suffixed_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "doctor"
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            (media / "scene_01_primary.jpg").write_bytes(b"x")
            (media / "scene_02_primary.mp4").write_bytes(b"x")
            with mock.patch.object(production_doctor, "BASE", base):
                report = production_doctor.media_inventory(sid)
            self.assertEqual(report["count"], 2)
            self.assertEqual(report["scenes"], [1, 2])
            self.assertEqual(report["photos"], 1)
            self.assertEqual(report["videos"], 1)


if __name__ == "__main__":
    unittest.main()
