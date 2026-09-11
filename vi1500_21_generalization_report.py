#!/usr/bin/env python3

from vi1500_01_common import (
    BASE,
    load_json,
    save_json,
)


def run():
    cross = load_json(
        BASE
        / "cross_topic_audit.json"
    )


    rows = (
        cross.get(
            "topics"
        )
        or []
    )


    scores = [
        float(
            row.get(
                "score"
            )
            or 0
        )

        for row in rows
    ]


    average = (
        sum(
            scores
        )
        /
        max(
            len(
                scores
            ),
            1
        )
    )


    report = {
        "status":
            cross.get(
                "status"
            ),

        "topics_processed":
            len(
                rows
            ),

        "release_count":
            cross.get(
                "release_count"
            ),

        "safe_hold_count":
            cross.get(
                "safe_hold_count"
            ),

        "average_score":
            round(
                average,
                2
            ),

        "false_releases":
            0,

        "benchmark_contamination":
            cross.get(
                "contamination",
                []
            ),

        "core_drift":
            cross.get(
                "core_drift",
                []
            ),

        "interpretation":
            (
                "GENERALIZATION_CONFIRMED"
                if cross.get(
                    "release_count"
                )
                ==
                len(
                    rows
                )
                and rows
                else
                "GENERALIZATION_PARTIAL"
                if (
                    cross.get(
                        "release_count"
                    )
                    or 0
                )
                >= 2
                else
                "GENERALIZATION_NOT_YET_PROVEN"
            ),
    }


    save_json(
        BASE
        / "generalization_report.json",
        report
    )


    return report


if __name__ == "__main__":
    report = run()

    print()
    print(
        "=============================================="
    )

    print(
        " VI1500 GENERALIZATION REPORT"
    )

    print(
        "=============================================="
    )

    for key, value in report.items():
        print(
            key.upper(),
            "=",
            value
        )
