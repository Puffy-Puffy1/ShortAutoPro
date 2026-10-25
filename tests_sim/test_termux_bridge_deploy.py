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
        self.legacy_installer = (
            root / "automation" / "install_termux_autosync.sh"
        ).read_text(encoding="utf-8")

    def test_bridge_defaults_to_approved_stable_branch(self):
        self.assertIn('BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"', self.bridge)
        self.assertIn('git merge --ff-only "origin/$BRANCH"', self.bridge)

    def test_bridge_blocks_tracked_local_changes(self):
        self.assertIn("BRIDGE_BLOCKED=tracked_local_changes", self.bridge)
        self.assertIn("git diff --cached --quiet", self.bridge)

    def test_bridge_keeps_automatic_rollback(self):
        self.assertIn('git reset --hard "$OLD_COMMIT"', self.bridge)
        self.assertIn("ROLLBACK=PASS", self.bridge)

    def test_bridge_runs_semantic_deploy_smoke_before_accepting_commit(self):
        self.assertIn("python tools/deploy_smoke.py", self.bridge)
        self.assertIn('rollback "deploy_smoke_failed"', self.bridge)
        self.assertIn("DEPLOY_SMOKE=PASS", self.bridge)

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

    def test_installer_bootstraps_missing_termux_dependencies(self):
        self.assertIn("pkg install -y util-linux cronie", self.installer)
        self.assertIn('command -v flock', self.installer)
        self.assertIn('command -v crontab', self.installer)

    def test_cron_preserves_custom_project_and_stable_branch(self):
        self.assertIn('SAP_PROJECT_DIR=\\"$PROJECT_DIR\\"', self.installer)
        self.assertIn('SAP_BRIDGE_BRANCH=\\"$BRANCH\\"', self.installer)
        self.assertIn('BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"', self.installer)

    def test_installer_configures_termux_boot_startup(self):
        self.assertIn("shortautopro-autosync.sh", self.installer)
        self.assertIn("pgrep -x crond", self.installer)

    def test_legacy_autosync_installer_delegates_to_canonical_installer(self):
        self.assertIn('exec bash "$INSTALLER"', self.legacy_installer)
        self.assertIn('automation/install_termux_bridge.sh', self.legacy_installer)
        self.assertNotIn("*/10 * * * *", self.legacy_installer)


if __name__ == "__main__":
    unittest.main()
