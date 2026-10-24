import json
import tempfile
import unittest
from pathlib import Path

from first_video_run_contract import evaluate_run_result


class FirstVideoRunContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.short_id = "gha_12345_1"
        (self.base / "videos").mkdir()
        (self.base / "manifests").mkdir()
        (self.base / "videos" / f"short_v6_{self.short_id}.mp4").write_bytes(b"mp4-fixture")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_report(self, *, decision="BLOCK", critical=None, brain_decision="HUMAN_APPROVAL_REQUIRED", brain_enforced=True):
        report = {
            "short_id": self.short_id,
            "decision": decision,
            "critical": ["shortauto_brain_approval_required"] if critical is None else critical,
            "brain_enforced": brain_enforced,
            "shortauto_brain": {
                "status": "PASS",
                "decision": brain_decision,
                "quality": {"decision": brain_decision},
            },
        }
        (self.base / "manifests" / f"{self.short_id}_release.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    def test_expected_human_approval_block_confirms_generation_only(self):
        self.write_report()
        accepted, reason = evaluate_run_result(self.base, self.short_id, 1)
        self.assertTrue(accepted)
        self.assertEqual(reason, "generation_pass_release_held_for_human_approval")

    def test_successful_pipeline_requires_allowed_release_decision(self):
        self.write_report(decision="PUBLISH", critical=[])
        accepted, reason = evaluate_run_result(self.base, self.short_id, 0)
        self.assertTrue(accepted)
        self.assertEqual(reason, "generation_and_release_gate_pass")

    def test_missing_mp4_never_counts_as_success(self):
        (self.base / "videos" / f"short_v6_{self.short_id}.mp4").unlink()
        self.write_report()
        accepted, reason = evaluate_run_result(self.base, self.short_id, 1)
        self.assertFalse(accepted)
        self.assertEqual(reason, "current_run_mp4_missing")

    def test_empty_mp4_never_counts_as_success(self):
        (self.base / "videos" / f"short_v6_{self.short_id}.mp4").write_bytes(b"")
        self.write_report()
        accepted, reason = evaluate_run_result(self.base, self.short_id, 1)
        self.assertFalse(accepted)
        self.assertEqual(reason, "current_run_mp4_empty")

    def test_other_release_blockers_remain_failures(self):
        self.write_report(critical=[
            "shortauto_brain_approval_required",
            "visual_qa_block",
        ])
        accepted, reason = evaluate_run_result(self.base, self.short_id, 1)
        self.assertFalse(accepted)
        self.assertEqual(reason, "pipeline_failed_or_release_gate_has_additional_blockers")

    def test_non_approval_release_block_remains_failure(self):
        self.write_report(critical=["visual_qa_block"], brain_decision="BLOCK")
        accepted, reason = evaluate_run_result(self.base, self.short_id, 1)
        self.assertFalse(accepted)

    def test_zero_exit_cannot_hide_a_blocked_release_report(self):
        self.write_report()
        accepted, reason = evaluate_run_result(self.base, self.short_id, 0)
        self.assertFalse(accepted)
        self.assertEqual(reason, "pipeline_exit_success_conflicts_with_release_report")

    def test_invalid_short_id_is_rejected(self):
        accepted, reason = evaluate_run_result(self.base, "../unsafe", 1)
        self.assertFalse(accepted)
        self.assertEqual(reason, "invalid_short_id")


if __name__ == "__main__":
    unittest.main()
