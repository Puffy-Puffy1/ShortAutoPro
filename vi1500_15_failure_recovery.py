#!/usr/bin/env python3

from vi1500_01_common import (
    save_json,
)


TRANSIENT = [
    "429",
    "too many requests",
    "503",
    "502",
    "504",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "connection reset",
]


def classify_failure(
    generator_report,
):
    text = (
        str(
            generator_report.get(
                "stderr_tail",
                ""
            )
        )
        +
        "\n"
        +
        str(
            generator_report.get(
                "stdout_tail",
                ""
            )
        )
    ).lower()


    transient = any(
        token in text

        for token
        in TRANSIENT
    )


    return {
        "transient":
            transient,

        "recommended_action":
            (
                "RETRY"
                if transient
                else "SAFE_HOLD"
            ),
    }


def write_recovery(
    generator_report,
    run_dir,
):
    result = classify_failure(
        generator_report
    )


    save_json(
        run_dir
        / "recovery_plan.json",
        result
    )


    return result
