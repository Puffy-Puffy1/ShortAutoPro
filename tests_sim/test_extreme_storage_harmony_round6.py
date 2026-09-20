import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExtremeStorageHarmonyRound6Tests(unittest.TestCase):
    def test_retention_is_planned_per_storage_group(self):
        text = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn("def candidate_groups()", text)
        self.assertIn("for items in candidate_groups():", text)
        self.assertIn("transient temp directories cannot consume", text)
        self.assertNotIn("items=sorted(candidates()", text)

    def test_storage_env_values_have_safe_fallbacks(self):
        text = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn('bounded_int("SHORT_STORAGE_KEEP_PROJECTS",3,1,20)', text)
        self.assertIn('bounded_int("SHORT_STORAGE_KEEP_DAYS",7,1,90)', text)
        self.assertIn("def min_free_bytes()", text)
        self.assertIn("except (TypeError,ValueError):value=1.2", text)

    def test_cleanup_tolerates_disappearing_files(self):
        text = (ROOT / "storage_manager.py").read_text(encoding="utf-8")
        self.assertIn("def safe_mtime(", text)
        self.assertIn("except OSError:return 0.0", text)
        self.assertIn("except OSError:continue", text)

    def test_shell_preflight_uses_same_disk_threshold(self):
        text = (ROOT / "preflight_check.sh").read_text(encoding="utf-8")
        self.assertIn('MIN_FREE_GB="${SAP_MIN_FREE_GB:-1.2}"', text)
        self.assertIn('if [ "$LIVRE_MB" -ge "$MIN_FREE_MB" ]; then', text)
        self.assertNotIn('elif [ "$LIVRE_MB" -ge 800 ]; then', text)


if __name__ == "__main__":
    unittest.main()
