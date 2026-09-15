#!/usr/bin/env python3

from vi1400_01_common import (
    TMP,
    load_json,
    policy,
    save_json,
)


def run():
    rows = load_json(
        TMP
        / "frame_metrics.json"
    ).get(
        "scenes",
        []
    )


    config = policy()


    warning_threshold = float(
        config.get(
            "scene_warning_below",
            6.5
        )
    )


    block_threshold = float(
        config.get(
            "scene_block_below",
            4.0
        )
    )


    warnings = []

    blockers = []


    for row in rows:

        scene = row[
            "scene"
        ]


        score = row[
            "visual_strength"
        ]


        if score < block_threshold:

            blockers.append(
                f"scene_{scene}_visual_strength_critical"
            )


        elif score < warning_threshold:

            warnings.append(
                f"scene_{scene}_visual_strength_low"
            )


        if (
            row[
                "white_fraction"
            ]
            >
            0.55
        ):

            warnings.append(
                f"scene_{scene}_excess_white_space"
            )


        if row[
            "blur_band_proxy"
        ]:

            warnings.append(
                f"scene_{scene}_blur_band_layout"
            )


    average = (
        sum(
            row[
                "visual_strength"
            ]

            for row in rows
        )
        /
        max(
            len(
                rows
            ),
            1
        )
    )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "average_strength":
            round(
                average,
                2
            ),

        "warnings":
            warnings,

        "blockers":
            blockers,

        "scenes":
            rows,
    }


    save_json(
        TMP
        / "visual_qa.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 VISUAL QA=",
        report[
            "status"
        ]
    )

    print(
        "AVERAGE=",
        report[
            "average_strength"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )

    print(
        "BLOCKERS=",
        report[
            "blockers"
        ]
    )
