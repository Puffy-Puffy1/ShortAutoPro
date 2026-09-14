import json
import tempfile
import unittest
from pathlib import Path

from quality_check import evaluate


class QualityCheckHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.video = self.base / "videos" / "short_v6_case.mp4"
        self.media = self.base / "imagens" / "short_case"
        self.scene_map = self.base / "roteiros" / "scene_map_case.json"
        self.supervisor = self.base / "roteiros" / "supervisor_case.json"

        self.video.parent.mkdir(parents=True)
        self.media.mkdir(parents=True)
        self.scene_map.parent.mkdir(parents=True)

        # evaluate() accepts injected ffprobe data, so this only needs to meet
        # the file-size contract; no real render/codec work runs in CI.
        self.video.write_bytes(b"0" * 600_000)
        for index in range(1, 7):
            suffix = ".webp" if index == 1 else ".jpg"
            (self.media / f"scene_{index:02d}{suffix}").write_bytes(b"asset")

        self.scene_map.write_text(
            json.dumps(
                {
                    "scenes": [
                        {"scene": index, "query": f"scene {index}"}
                        for index in range(1, 7)
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.supervisor.write_text(
            json.dumps({"status": "PASS"}),
            encoding="utf-8",
        )

        self.probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "avg_frame_rate": "30/1",
                },
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "45.0"},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self):
        return evaluate(
            self.video,
            self.media,
            self.scene_map,
            self.supervisor,
            6,
            probe_data=self.probe,
        )

    def test_valid_v6_contract_passes(self):
        result = self.evaluate()
        self.assertEqual(result["errors"], [], result["errors"])
        self.assertEqual(result["media_count"], 6)
        self.assertEqual(result["width"], 1080)
        self.assertEqual(result["height"], 1920)

    def test_missing_supervisor_blocks(self):
        self.supervisor.unlink()
        result = self.evaluate()
        self.assertTrue(
            any("Supervisor" in error for error in result["errors"]),
            result["errors"],
        )

    def test_nonsequential_scene_map_blocks(self):
        payload = json.loads(self.scene_map.read_text(encoding="utf-8"))
        payload["scenes"][2]["scene"] = 4
        self.scene_map.write_text(json.dumps(payload), encoding="utf-8")
        result = self.evaluate()
        self.assertIn("Numeração do scene_map não é sequencial.", result["errors"])

    def test_duplicate_physical_scene_blocks(self):
        (self.media / "scene_01.jpg").write_bytes(b"duplicate")
        result = self.evaluate()
        self.assertTrue(result["errors"])
        self.assertTrue(
            any("Cenas físicas" in error or "duplicadas" in error for error in result["errors"]),
            result["errors"],
        )

    def test_overlong_short_blocks(self):
        self.probe["format"]["duration"] = "181"
        result = self.evaluate()
        self.assertTrue(
            any("longo demais" in error for error in result["errors"]),
            result["errors"],
        )


if __name__ == "__main__":
    unittest.main()
