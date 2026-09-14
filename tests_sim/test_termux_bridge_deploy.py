import unittest
from pathlib import Path


class TermuxBridgeDeployTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.bridge = (root / "automation" / "termux_bridge.sh").read_text(
            encoding="utf-8"
        )
        self.installer = (root / "automation" / "install_termux_bridge.sh").read_text(
            encoding="utf-8"
        )

    def test_bridge_defaults_to_approved_stable_branch(self):
        self.assertIn('BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"', self.bridge)
        self.assertIn('git merge --ff-only "origin/$BRANCH"', self.bridge)

    def test_bridge_blocks_tracked_local_changes(self):
        self.assertIn("BRIDGE_BLOCKED=tracked_local_changes", self.bridge)
        self.assertIn("git diff --cached --quiet", self.bridge)

    def test_bridge_keeps_automatic_rollback(self):
        self.assertIn('git reset --hard "$OLD_COMMIT"', self.bridge)
        self.assertIn("ROLLBACK=PASS", self.bridge)

    def test_installer_preserves_existing_crontab(self):
        self.assertIn("crontab.before_bridge.txt", self.installer)
        self.assertIn('grep -vF "$CRON_TAG"', self.installer)
        self.assertIn('crontab "$NEW_CRON"', self.installer)

    def test_installer_uses_tagged_15_minute_schedule(self):
        self.assertIn('CRON_TAG="# SHORTAUTOPRO_TERMUX_BRIDGE"', self.installer)
        self.assertIn('CRON_LINE="*/15 * * * * bash ', self.installer)

    def test_installer_refuses_dirty_tracked_worktree(self):
        self.assertIn("ha alteracoes locais rastreadas", self.installer)
        self.assertIn("git diff --cached --quiet", self.installer)

    def test_installer_does_not_change_tracked_bridge_file_mode(self):
        self.assertNotIn('chmod +x "$BRIDGE"', self.installer)
        self.assertIn('bash "$BRIDGE" || {', self.installer)


if __name__ == "__main__":
    unittest.main()
