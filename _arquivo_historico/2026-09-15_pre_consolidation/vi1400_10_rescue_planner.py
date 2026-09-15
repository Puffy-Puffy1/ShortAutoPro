#!/usr/bin/env python3

from vi1400_01_common import (
    TMP,
    load_json,
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


    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    plan = load_json(
        artifacts.get(
            "selection_plan"
        )
        or "",
        {}
    )


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )


    directives = []


    for row in rows:

        scene = row[
            "scene"
        ]


        actions = []


        if (
            row[
                "white_fraction"
            ]
            > 0.45
        ):

            actions += [
                "DARK_BACKDROP_CARD",
                "TIGHTER_CONTENT_CROP",
            ]


        if row[
            "blur_band_proxy"
        ]:

            actions += [
                "REDUCE_BLUR_BAND",
                "EXPAND_PRIMARY_MEDIA",
            ]


        if (
            row[
                "edge_density"
            ]
            < 0.07
        ):

            actions += [
                "SUBTLE_PUSH_IN"
            ]


        if (
            row[
                "visual_strength"
            ]
            < 6.5
        ):

            actions += [
                "EDITORIAL_REVIEW_PRIORITY"
            ]


        item = selected.get(
            str(
                scene
            ),
            {}
        )


        mode = str(
            (
                item.get(
                    "evaluation"
                )
                or {}
            ).get(
                "mode"
            )
            or ""
        )


        title = str(
            (
                item.get(
                    "candidate"
                )
                or {}
            ).get(
                "title"
            )
            or ""
        ).lower()


        if (
            "MEDICAL"
            in mode

            or

            "bipolar"
            in title
        ):

            actions += [
                "MEDICAL_GRAPH_TIGHT_CROP",
                "DARK_NEUTRAL_BACKGROUND",
            ]


        if (
            "MAINTENANCE_WORKER"
            in mode

            or

            "maintenance worker"
            in title
        ):

            actions += [
                "WORKER_SUBJECT_TIGHTER_CROP"
            ]


        if (
            "WATER_TANK"
            in mode

            or

            (
                "water"
                in title

                and

                "tower"
                in title
            )
        ):

            actions += [
                "WATER_TANK_FOCAL_PRIORITY"
            ]


        directives.append({
            "scene":
                scene,

            "actions":
                sorted(
                    set(
                        actions
                    )
                ),

            "priority":
                (
                    "HIGH"
                    if row[
                        "visual_strength"
                    ]
                    < 6.5
                    else "NORMAL"
                ),
        })


    save_json(
        TMP
        / "rescue_plan.json",
        {
            "directives":
                directives,

            "destructive":
                False,
        }
    )


    return directives


if __name__ == "__main__":

    directives = run()


    print(
        "VI1400 RESCUE PLAN=PASS"
    )


    for item in directives:

        if item[
            "actions"
        ]:

            print(
                "SCENE",
                item[
                    "scene"
                ],
                "=>",
                ",".join(
                    item[
                        "actions"
                    ]
                )
            )
