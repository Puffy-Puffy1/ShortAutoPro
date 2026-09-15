#!/usr/bin/env python3

import json
from pathlib import Path


VERSION = "6.60-source-audit"


FILES = [
    "vi6_13_recovery_planner.py",
    "vi6_19_true_recovery.py",
    "vi6_20_normalizer.py",
    "source_router.py",
    "evidence_guard.py",
]


def audit():

    findings = []


    for filename in FILES:

        path = Path(
            filename
        )


        if not path.exists():
            continue


        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        low = text.lower()


        # Audit only. No automatic patching.
        if (
            "truth"
            in low
            and "true"
            in low
            and "unknown"
            not in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "truth_default_requires_manual_review",
                }
            )


        if (
            "hard_no_retry"
            in low
            or "hard_rejections"
            in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "broad_no_retry_policy_requires_review",
                }
            )


        if (
            "source_router"
            in filename
            and "getattr("
            in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "dynamic_source_dispatch_present",
                }
            )


    return {

        "version":
            VERSION,

        "status":
            (
                "REVIEW"
                if findings
                else "PASS"
            ),

        "findings":
            findings,

        "files_modified":
            False,
    }


if __name__ == "__main__":

    print(
        json.dumps(
            audit(),
            ensure_ascii=False,
            indent=2
        )
    )
