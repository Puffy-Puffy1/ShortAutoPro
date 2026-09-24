import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class FreshRunAfterSuccessTests(unittest.TestCase):
    def test_normal_run_ignores_persistent_reuse_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            videos = base / "videos"
            roteiros = base / "roteiros"
            for path in (state, videos, roteiros):
                path.mkdir(parents=True, exist_ok=True)

            old = "completed_short"
            (videos / f"short_v6_{old}.mp4").write_bytes(b"x")

            with (
                mock.patch.object(main, "BASE", base),
                mock.patch.object(main, "STATE_DIR", state),
                mock.patch.dict(
                    os.environ,
                    {
                        "SHORT_ID": old,
                        # Simulates a stale value accidentally left in config.sh.
                        "SAP_REUSE_SHORT_ID": "1",
                    },
                    clear=False,
                ),
            ):
                fresh = main.allocate_id(reuse_existing=False)

            self.assertNotEqual(fresh, old)
            self.assertTrue(fresh)

    def test_resume_can_explicitly_reuse_existing_short_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            state.mkdir(parents=True)
            old = "resume_me"
            (state / f"pipeline_{old}.json").write_text("{}", encoding="utf-8")

            with (
                mock.patch.object(main, "BASE", base),
                mock.patch.object(main, "STATE_DIR", state),
                mock.patch.dict(os.environ, {"SHORT_ID": old}, clear=False),
            ):
                reused = main.allocate_id(reuse_existing=True)

            self.assertEqual(reused, old)

    def test_user_supplied_unused_short_id_is_preserved_for_new_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / ".sap_state"
            state.mkdir(parents=True)

            with (
                mock.patch.object(main, "BASE", base),
                mock.patch.object(main, "STATE_DIR", state),
                mock.patch.dict(os.environ, {"SHORT_ID": "brand_new_id"}, clear=False),
            ):
                allocated = main.allocate_id(reuse_existing=False)

            self.assertEqual(allocated, "brand_new_id")

    def test_resume_uses_private_cli_flag_not_reuse_environment(self):
        text = Path("resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn('"run", "--reuse-short-id"', text)
        self.assertNotIn('env["SAP_REUSE_SHORT_ID"] = "1"', text)

    def test_normal_cli_run_has_hidden_explicit_reuse_flag(self):
        text = Path("main.py").read_text(encoding="utf-8")
        self.assertIn('"--reuse-short-id"', text)
        self.assertIn("reuse_existing=reuse_short_id", text)
        self.assertNotIn('os.getenv("SAP_REUSE_SHORT_ID"', text)


if __name__ == "__main__":
    unittest.main()
