import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import media_stage_runtime as stage6


class Stage6CompletionContractTests(unittest.TestCase):
    def _write_scene_map(self, base: Path, sid: str, count: int = 3) -> None:
        folder = base / "roteiros"
        folder.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "short_id": sid,
            "scene_count": count,
            "scenes": [
                {"scene_id": f"scene_{number:02d}", "text": f"scene {number}"}
                for number in range(1, count + 1)
            ],
        }
        (folder / f"scene_map_{sid}.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def test_scene_contract_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "dup"
            self._write_scene_map(base, sid, 2)
            path = base / "roteiros" / f"scene_map_{sid}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["scenes"][1]["scene_id"] = payload["scenes"][0]["scene_id"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(stage6, "BASE", base), mock.patch.object(stage6, "SID", sid):
                expected, errors = stage6.scene_contract()
            self.assertEqual(expected, 2)
            self.assertIn("SAP-E002:duplicate_scene_ids", errors)

    def test_zero_exit_cannot_certify_missing_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "missing"
            self._write_scene_map(base, sid, 3)
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            (media / "scene_1.jpg").write_bytes(b"x" * 2000)
            (media / "scene_2.jpg").write_bytes(b"x" * 2000)
            with mock.patch.object(stage6, "BASE", base), \
                 mock.patch.object(stage6, "SID", sid), \
                 mock.patch.object(stage6, "REPORT", base / "reports" / "none.json"):
                ok, detail = stage6.validate_media_completion()
            self.assertFalse(ok)
            self.assertEqual(detail["expected"], 3)
            self.assertEqual(detail["valid"], 2)
            self.assertEqual(detail["missing"], [3])

    def test_runtime_contains_false_success_recovery_path(self):
        text = (Path(__file__).resolve().parents[1] / "media_stage_runtime.py").read_text(encoding="utf-8")
        self.assertIn("MEDIA_STAGE_RUNTIME=V2_FALSE_SUCCESS", text)
        self.assertIn("completion_override", text)
        self.assertIn("invalid_scenes", text)
        self.assertIn("MEDIA_STAGE_RUNTIME=V2_RETRY_MISSING_ONLY", text)

    def test_complete_assets_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "ok"
            self._write_scene_map(base, sid, 3)
            media = base / "imagens" / f"short_{sid}"
            media.mkdir(parents=True)
            for number in range(1, 4):
                (media / f"scene_{number}.jpg").write_bytes(b"x" * 2000)
            with mock.patch.object(stage6, "BASE", base), \
                 mock.patch.object(stage6, "SID", sid), \
                 mock.patch.object(stage6, "REPORT", base / "reports" / "none.json"):
                ok, detail = stage6.validate_media_completion()
            self.assertTrue(ok)
            self.assertEqual(detail["valid"], 3)
            self.assertEqual(detail["missing"], [])


if __name__ == "__main__":
    unittest.main()
