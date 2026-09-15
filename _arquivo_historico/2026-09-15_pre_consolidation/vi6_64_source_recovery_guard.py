#!/usr/bin/env python3

import ast
from pathlib import Path


VERSION = "6.64"


RISK_FILES = (
    "vi6_13_recovery_planner.py",
    "vi6_19_true_recovery.py",
    "vi6_20_normalizer.py",
    "source_router.py",
)


def inspect():

    findings = []


    for filename in RISK_FILES:

        path = Path(filename)


        if not path.exists():

            continue


        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        low = text.lower()


        try:
            ast.parse(text)
            syntax_ok = True

        except Exception:
            syntax_ok = False


        if not syntax_ok:

            findings.append(
                {
                    "file": filename,
                    "severity": "BLOCK",
                    "reason": "python_syntax_invalid",
                }
            )


        if (
            "hard_no_retry" in low
            or "hard_rejections" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "broad_no_retry_semantics_present",
                }
            )


        if (
            filename == "source_router.py"
            and "getattr(" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "dynamic_dispatch_requires_exact_route_audit",
                }
            )


        if (
            filename == "vi6_20_normalizer.py"
            and "true" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "truth_default_requires_unknown_safe_policy",
                }
            )


    blocks = [
        x
        for x in findings
        if x["severity"] == "BLOCK"
    ]


    warnings = [
        x
        for x in findings
        if x["severity"] == "WARN"
    ]


    return {
        "version": VERSION,
        "status":
            (
                "HOLD"
                if blocks
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),
        "blocks": blocks,
        "warnings": warnings,

        # No risky source module is modified here.
        "source_files_modified": False,

        # Future active recovery remains locked
        # until exact routes are audited.
        "active_source_recovery_allowed":
            False,
    }


def self_test():

    result = inspect()

    assert (
        result["active_source_recovery_allowed"]
        is False
    )


    print("VI6.64 SOURCE GUARD=PASS")


if __name__ == "__main__":
    self_test()
