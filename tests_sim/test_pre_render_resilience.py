import unittest
from pathlib import Path
from unittest import mock

import production_recovery


class PreRenderResilienceTests(unittest.TestCase):
    def _ready(self):
        return {
            "status": "READY",
            "checks": {
                "short_id": True,
                "ffmpeg": True,
                "ffprobe": True,
                "directories": True,
                "scene_map": True,
                "edit_plan": True,
                "assets": True,
                "audio": True,
                "subtitles": True,
            },
            "errors": [],
        }

    def test_ready_preflight_is_noop(self):
        with mock.patch.object(production_recovery.render_preflight, "inspect", return_value=self._ready()), \
             mock.patch.object(production_recovery, "_atomic_json"):
            report = production_recovery.repair("ready")
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["actions"], [])

    def test_missing_media_uses_bounded_media_repair_then_rechecks(self):
        failed = self._ready()
        failed["status"] = "FAILED"
        failed["checks"] = dict(failed["checks"])
        failed["checks"]["assets"] = False
        failed["errors"] = ["assets ausentes: 03"]

        with mock.patch.object(
            production_recovery.render_preflight,
            "inspect",
            side_effect=[failed, self._ready()],
        ), mock.patch.object(
            production_recovery, "_repair_media", return_value=True
        ) as repair_media, mock.patch.object(
            production_recovery, "_atomic_json"
        ):
            report = production_recovery.repair("media")

        self.assertEqual(report["status"], "RECOVERED")
        repair_media.assert_called_once()

    def test_main_certifies_render_inputs_before_renderer(self):
        text = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        start = text.index("def assemble_and_render")
        end = text.index("\ndef final_gates", start)
        block = text[start:end]
        recovery_pos = block.index('"production_recovery.py"')
        preflight_pos = block.index('"render_preflight.py"')
        renderer_pos = block.index('"video_professional.py"')
        self.assertLess(recovery_pos, renderer_pos)
        self.assertLess(preflight_pos, renderer_pos)
        self.assertIn("production_watchdog.record_heartbeat", text)
        self.assertIn('"production_health.py"', block)


if __name__ == "__main__":
    unittest.main()
