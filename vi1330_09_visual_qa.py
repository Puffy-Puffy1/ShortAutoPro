#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

PLAN = json.loads(
    (
        BASE
        / "temp/vi1330/publication_visual_plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1330_09_visual_qa_latest.json"
)


def main():
    plans = PLAN[
        "plans"
    ]


    groups = [
        item[
            "visual_group"
        ]
        for item in plans
    ]


    labels = [
        item[
            "overlay_label"
        ]
        for item in plans
    ]


    strategy = {
        item[
            "scene"
        ]:
            item[
                "strategy"
            ]

        for item in plans
    }


    consecutive = []


    for index in range(
        1,
        len(
            groups
        )
    ):

        if groups[
            index
        ] == groups[
            index - 1
        ]:

            consecutive.append(
                [
                    index,
                    index + 1,
                ]
            )


    checks = {
        "twelve_scenes":
            len(
                plans
            )
            == 12,

        "minimum_9_visual_groups":
            len(
                set(
                    groups
                )
            )
            >= 9,

        "no_consecutive_visual_duplicates":
            not consecutive,

        "all_labels_present":
            all(
                bool(
                    label
                )
                for label in labels
            ),

        "scene1_authentic":
            plans[
                0
            ][
                "source_mode"
            ]
            ==
            "AUTHENTIC_CASE_VIDEO",

        "scene4_authentic":
            plans[
                3
            ][
                "source_mode"
            ]
            ==
            "AUTHENTIC_CASE_VIDEO",

        "scene2_sign_focus":
            strategy[
                2
            ]
            ==
            "HOTEL_SIGN_TIGHT",

        "scene9_medical_focus":
            strategy[
                9
            ]
            ==
            "MEDICAL_GRAPH_FOCUS",

        "scene10_worker_focus":
            strategy[
                10
            ]
            ==
            "WORKER_SUBJECT_FOCUS",

        "scene11_tank_focus":
            strategy[
                11
            ]
            ==
            "WATER_TANK_SUBJECT_FOCUS",

        "scene12_document_focus":
            strategy[
                12
            ]
            ==
            "AUTOPSY_DOCUMENT_FOCUS",
    }


    passed_count = sum(
        1

        for value in checks.values()

        if value
    )


    score = round(
        (
            passed_count
            /
            len(
                checks
            )
        )
        *
        10,
        2
    )


    failed = [
        key

        for key, value in checks.items()

        if value is not True
    ]


    status = (
        "VI1330_VISUAL_QA_CERTIFIED"

        if not failed

        else
        "VI1330_VISUAL_QA_HOLD"
    )


    output = {
        "status":
            status,

        "score":
            score,

        "unique_visual_groups":
            len(
                set(
                    groups
                )
            ),

        "consecutive_duplicate_groups":
            consecutive,

        "checks":
            checks,

        "failed":
            failed,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    output
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "=============================================="
    )
    print(
        " VI1330 AUTOMATED VISUAL QA"
    )
    print(
        "=============================================="
    )

    print(
        "VISUAL GROUPS:",
        len(
            set(
                groups
            )
        )
    )
    print(
        "SCORE:",
        score,
        "/ 10"
    )
    print(
        "FAILED:",
        failed
    )
    print(
        "STATUS:",
        status
    )


    if failed:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
