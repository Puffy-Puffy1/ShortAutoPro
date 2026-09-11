#!/usr/bin/env python3

from vi1500_01_common import (
    free_mb,
    policy,
    save_json,
)


def run(
    run_dir,
):
    config = policy()

    free = free_mb()


    warning_limit = int(
        config.get(
            "disk_free_warn_mb",
            1500
        )
    )


    block_limit = int(
        config.get(
            "disk_free_block_mb",
            700
        )
    )


    warnings = []

    blockers = []


    if free < block_limit:
        blockers.append(
            "storage_critical"
        )


    elif free < warning_limit:
        warnings.append(
            "storage_low"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "free_mb":
            free,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "resource_guard.json",
        report
    )


    return report
