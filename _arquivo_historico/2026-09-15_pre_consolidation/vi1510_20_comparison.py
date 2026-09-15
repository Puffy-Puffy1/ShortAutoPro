#!/usr/bin/env python3

from vi1510_01_common import (
    BASE,
    ROOT,
    load_json,
    save_json,
)


def run():
    old = load_json(
        ROOT
        / "temp"
        / "vi1500"
        / "cross_topic_audit.json",
        {}
    )


    new = load_json(
        BASE
        / "cross_topic_v2.json",
        {}
    )


    old_by_label = {
        item.get(
            "label"
        ):
            item

        for item in old.get(
            "topics",
            []
        )
    }


    new_by_label = {
        item.get(
            "label"
        ):
            item

        for item in new.get(
            "results",
            []
        )
    }


    rows = []


    for label in [
        "A",
        "B",
        "C",
    ]:

        before = (
            old_by_label.get(
                label
            )
            or {}
        )


        after = (
            new_by_label.get(
                label
            )
            or {}
        )


        rows.append({
            "label":
                label,

            "vi1500_status":
                before.get(
                    "status"
                ),

            "vi1500_score":
                before.get(
                    "score"
                ),

            "vi1510_status":
                after.get(
                    "status"
                ),

            "vi1510_score":
                after.get(
                    "score"
                ),

            "vi1510_blockers":
                after.get(
                    "blockers"
                ),

            "control_reference_only":
                after.get(
                    "control_plane_references"
                ),
        })


    report = {
        "vi1500_status":
            old.get(
                "status"
            ),

        "vi1510_status":
            new.get(
                "status"
            ),

        "vi1500_releases":
            old.get(
                "release_count"
            ),

        "vi1510_releases":
            new.get(
                "release_count"
            ),

        "rows":
            rows,
    }


    save_json(
        BASE
        / "vi1500_vs_vi1510.json",
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
        " VI1500 VS VI1510"
    )

    print(
        "=============================================="
    )


    for row in report[
        "rows"
    ]:

        print(
            row[
                "label"
            ],
            "| VI1500",
            row[
                "vi1500_status"
            ],
            row[
                "vi1500_score"
            ],
            "| VI1510",
            row[
                "vi1510_status"
            ],
            row[
                "vi1510_score"
            ]
        )
