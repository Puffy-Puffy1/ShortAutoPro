import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "first-video-live.yml"


class FirstVideoValidationContractTests(unittest.TestCase):
    def test_ffprobe_runs_after_pipeline_gate_failure_when_run_id_exists(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        start = content.index("      - name: Validate generated MP4 with FFprobe")
        next_step = content.find("\n      - name:", start + 1)
        block = content[start:] if next_step < 0 else content[start:next_step]

        self.assertIn(
            "if: always() && steps.run-first-video.outputs.short_id != ''",
            block,
        )
        self.assertIn('test -f "$latest"', block)
        self.assertIn("ffprobe -v error", block)
        self.assertIn('codec_type")=="audio"', block)
        self.assertIn('codec_type")=="video"', block)

    def test_ffprobe_does_not_override_pipeline_failure(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python main.py run", content)
        self.assertIn("Validate generated MP4 with FFprobe", content)
        self.assertIn('SAP_BRAIN_ENFORCE: "1"', content)
        self.assertNotIn("continue-on-error: true", content)


if __name__ == "__main__":
    unittest.main()
