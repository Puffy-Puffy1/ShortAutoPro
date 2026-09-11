#!/usr/bin/env python3

from pathlib import Path

from vi1500_01_common import (
    BASE,
    RUNS,
    load_json,
    policy,
    save_json,
)


def run():
    queue = load_json(
        BASE
        / "queue_private.json"
    ).get(
        "topics",
        []
    )


    rows = []


    for topic in queue:
        label = topic[
            "label"
        ]


        candidates = sorted(
            RUNS.glob(
                (
                    label
                    +
                    "_*"
                )
            ),
            key=lambda path:
                path.stat().st_mtime,
            reverse=True,
        )


        if not candidates:
            rows.append({
                "label":
                    label,

                "status":
                    "MISSING",
            })

            continue


        run_dir = candidates[
            0
        ]


        gate = load_json(
            run_dir
            / "release_gate.json"
        )


        leak = load_json(
            run_dir
            / "semantic_leak_guard.json"
        )


        core = load_json(
            run_dir
            / "core_integrity.json"
        )


        rows.append({
            "label":
                label,

            "run_dir":
                str(
                    run_dir
                ),

            "status":
                gate.get(
                    "status"
                ),

            "ready":
                gate.get(
                    "ready"
                )
                is True,

            "score":
                gate.get(
                    "score"
                ),

            "leak_pass":
                leak.get(
                    "status"
                )
                == "PASS",

            "core_clean":
                (
                    not core.get(
                        "changed"
                    )
                ),
        })


    release_count = sum(
        row.get(
            "ready"
        )
        is True

        for row in rows
    )


    safe_hold_count = sum(
        row.get(
            "status"
        )
        == "SAFE_HOLD"

        for row in rows
    )


    contamination = [
        row[
            "label"
        ]

        for row in rows

        if (
            row.get(
                "leak_pass"
            )
            is False
        )
    ]


    core_drift = [
        row[
            "label"
        ]

        for row in rows

        if (
            row.get(
                "core_clean"
            )
            is False
        )
    ]


    required = int(
        policy().get(
            "minimum_releases_for_certification",
            2
        )
    )


    if (
        release_count == len(
            queue
        )

        and

        not contamination

        and

        not core_drift
    ):
        status = (
            "VI1500_PRODUCTION_QUALIFICATION_CERTIFIED"
        )


    elif (
        release_count >= required

        and

        not contamination

        and

        not core_drift
    ):
        status = (
            "VI1500_PRODUCTION_QUALIFICATION_CONDITIONAL_CERTIFIED"
        )


    else:
        status = (
            "VI1500_SAFE_HOLD_MORE_GENERALIZATION_WORK_REQUIRED"
        )


    report = {
        "status":
            status,

        "topics":
            rows,

        "release_count":
            release_count,

        "safe_hold_count":
            safe_hold_count,

        "required_releases":
            required,

        "contamination":
            contamination,

        "core_drift":
            core_drift,
    }


    save_json(
        BASE
        / "cross_topic_audit.json",
        report
    )


    return report


if __name__ == "__main__":
    report = run()

    print(
        "STATUS:",
        report[
            "status"
        ]
    )

    print(
        "RELEASES:",
        report[
            "release_count"
        ]
    )

    print(
        "SAFE_HOLDS:",
        report[
            "safe_hold_count"
        ]
    )
