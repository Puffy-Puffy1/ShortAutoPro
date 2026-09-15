import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import client_job_runner as cjr


class ClientJobStatusReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.old_base = cjr.BASE
        self.old_jobs = cjr.JOBS
        self.old_profile_run = cjr.PROFILE_RUN
        cjr.BASE = self.base
        cjr.JOBS = self.base / "reports" / "evolution" / "client_jobs"
        cjr.PROFILE_RUN = self.base / "profile_run.sh"
        cjr.PROFILE_RUN.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    def tearDown(self):
        cjr.BASE = self.old_base
        cjr.JOBS = self.old_jobs
        cjr.PROFILE_RUN = self.old_profile_run
        self.temp.cleanup()

    def test_dry_run_preserves_pass_when_all_items_already_approved(self):
        job = {
            "job_id": "job_done",
            "client": "teste",
            "topic": "Caso real",
            "topic_mode": "exact",
            "quantity": 1,
            "language": "pt-BR",
            "profile": "true_crime",
            "status": "PASS",
            "items": [
                {
                    "index": 1,
                    "short_id": "client_job_done_001",
                    "status": "PASS",
                }
            ],
        }
        path = cjr.JOBS / "job_done.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(job), encoding="utf-8")

        with patch.object(cjr, "output_ok", return_value=True):
            rc = cjr.run_job(path, job, execute=False)

        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(saved["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
