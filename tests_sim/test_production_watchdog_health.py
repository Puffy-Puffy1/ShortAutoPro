import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import production_health
import production_watchdog


class ProductionWatchdogHealthTests(unittest.TestCase):
    def test_watchdog_detects_stale_orphaned_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sid = "stale"
            state_dir = base / ".sap_state"
            state_dir.mkdir(parents=True)
            heartbeat = (datetime.now().astimezone() - timedelta(hours=2)).isoformat(timespec="seconds")
            (state_dir / f"pipeline_{sid}.json").write_text(
                json.dumps({
                    "short_id": sid,
                    "status": "RUNNING",
                    "heartbeat_at": heartbeat,
                    "current_stage": "media_stage_runtime.py",
                }),
                encoding="utf-8",
            )
            report_dir = base / "reports" / "production"
            with mock.patch.object(production_watchdog, "BASE", base), \
                 mock.patch.object(production_watchdog, "REPORT_DIR", report_dir), \
                 mock.patch.object(production_watchdog, "_pid_from_lock", return_value=123), \
                 mock.patch.object(production_watchdog, "_pid_alive", return_value=False), \
                 mock.patch.dict(os.environ, {"SAP_WATCHDOG_STALE_SECONDS": "120"}, clear=False):
                report = production_watchdog.inspect(sid)
            self.assertEqual(report["status"], "STALE")
            self.assertTrue(any(item["severity"] == "BLOCK" for item in report["issues"]))

    def test_health_snapshot_is_healthy_when_core_contract_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in production_health.CORE_FILES:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# test\n", encoding="utf-8")
            report_dir = base / "reports" / "production"
            with mock.patch.object(production_health, "BASE", base), \
                 mock.patch.object(production_health, "REPORT_DIR", report_dir), \
                 mock.patch.object(production_health.shutil, "which", return_value="/bin/tool"), \
                 mock.patch.object(
                     production_health.shutil,
                     "disk_usage",
                     return_value=SimpleNamespace(free=2 * 1024 * 1024 * 1024),
                 ):
                report = production_health.snapshot("health", "test")
            self.assertEqual(report["status"], "HEALTHY")
            self.assertTrue((report_dir / "production_health_health.json").is_file())


if __name__ == "__main__":
    unittest.main()
