import unittest
from pathlib import Path


class TermuxStablePromotionTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        workflows = root / ".github" / "workflows"
        self.workflow = (workflows / "promote-termux-stable.yml").read_text(encoding="utf-8")
        self.portable = (workflows / "shortautopro-portable.yml").read_text(encoding="utf-8")

    def test_promotion_waits_for_approved_validator_success(self):
        self.assertIn('"ShortAutoPro Remote Control"', self.workflow)
        self.assertIn('"ShortAutoPro Portable Validation"', self.workflow)
        self.assertIn("types: [completed]", self.workflow)
        self.assertIn("workflow_run.conclusion == 'success'", self.workflow)
        self.assertIn("workflow_run.head_branch == 'main'", self.workflow)
        self.assertIn("workflow_run.name == 'ShortAutoPro Remote Control'", self.workflow)
        self.assertIn("workflow_run.name == 'ShortAutoPro Portable Validation'", self.workflow)

    def test_portable_validator_is_github_hosted_and_read_only(self):
        self.assertIn("runs-on: ubuntu-latest", self.portable)
        self.assertIn("contents: read", self.portable)
        self.assertNotIn("contents: write", self.portable)
        self.assertNotIn("runs-on: [self-hosted", self.portable)

    def test_write_token_stays_off_self_hosted_runner(self):
        self.assertIn("contents: write", self.workflow)
        self.assertIn("runs-on: ubuntu-latest", self.workflow)
        self.assertNotIn("runs-on: [self-hosted", self.workflow)

    def test_exact_tested_sha_is_promoted(self):
        self.assertIn("github.event.workflow_run.head_sha", self.workflow)
        self.assertIn('test "$actual" = "$TESTED_SHA"', self.workflow)

    def test_promotion_is_fast_forward_only(self):
        self.assertIn("git merge-base --is-ancestor origin/termux-stable HEAD", self.workflow)
        self.assertIn("PROMOTION_BLOCKED=termux_stable_diverged", self.workflow)
        self.assertNotIn("--force", self.workflow)


if __name__ == "__main__":
    unittest.main()
