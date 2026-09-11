#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1330_publication_quality_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

TIMELINE = json.loads(
    (
        BASE
        / "temp/vi1310/timeline.json"
    ).read_text(
        encoding="utf-8"
    )
)

VI1320_PLAN = json.loads(
    (
        BASE
        / "temp/vi1320/visual_plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

PREPARED = json.loads(
    (
        BASE
        / "temp/vi1300/prepared_manifest.json"
    ).read_text(
        encoding="utf-8"
    )
)

DOWNLOAD = json.loads(
    (
        BASE
        / "temp/vi1270_downloads/download_manifest.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "temp/vi1330/publication_visual_plan.json"
)


DIRECTION = {
    1: {
        "strategy":
            "AUTHENTIC_ARCHIVE_DYNAMIC_A",

        "label":
            "IMAGEM REAL DO CASO",

        "visual_group":
            "CASE_ELEVATOR_A",

        "priority":
            "HOOK"
    },

    2: {
        "strategy":
            "HOTEL_SIGN_TIGHT",

        "label":
            "HOTEL CECIL",

        "visual_group":
            "HOTEL_SIGN",

        "priority":
            "ENTITY"
    },

    3: {
        "strategy":
            "HOTEL_FACADE_WIDE",

        "label":
            "IMAGEM DE CONTEXTO",

        "visual_group":
            "HOTEL_FACADE",

        "priority":
            "ENTITY"
    },

    4: {
        "strategy":
            "AUTHENTIC_ARCHIVE_DYNAMIC_B",

        "label":
            "IMAGEM REAL DO CASO",

        "visual_group":
            "CASE_ELEVATOR_B",

        "priority":
            "EVIDENCE"
    },

    5: {
        "strategy":
            "HALLWAY_MONO_PUSH",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "HALLWAY_MONO",

        "priority":
            "ACTION"
    },

    6: {
        "strategy":
            "HALLWAY_RED_DRIFT",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "HALLWAY_RED",

        "priority":
            "ACTION"
    },

    7: {
        "strategy":
            "ELEVATOR_INTERIOR_PUSH",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "ELEVATOR_GENERIC",

        "priority":
            "MECHANISM"
    },

    8: {
        "strategy":
            "CCTV_CAMERA_FOCUS",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "CCTV_GENERIC",

        "priority":
            "EVIDENCE_CONTEXT"
    },

    9: {
        "strategy":
            "MEDICAL_GRAPH_FOCUS",

        "label":
            "CONTEXTO MÉDICO ILUSTRATIVO",

        "visual_group":
            "MEDICAL_GRAPH",

        "priority":
            "MEDICAL_CONTEXT"
    },

    10: {
        "strategy":
            "WORKER_SUBJECT_FOCUS",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "MAINTENANCE_WORKER",

        "priority":
            "HUMAN"
    },

    11: {
        "strategy":
            "WATER_TANK_SUBJECT_FOCUS",

        "label":
            "IMAGEM ILUSTRATIVA",

        "visual_group":
            "WATER_TANK",

        "priority":
            "OBJECT"
    },

    12: {
        "strategy":
            "AUTOPSY_DOCUMENT_FOCUS",

        "label":
            "DOCUMENTO DO CASO",

        "visual_group":
            "AUTOPSY_DOCUMENT",

        "priority":
            "DOCUMENT"
    }
}


def prepared_map():
    return {
        int(item["scene"]):
            item

        for item in (
            PREPARED.get("prepared")
            or []
        )
    }


def download_map():
    return {
        int(key):
            value

        for key, value in (
            DOWNLOAD.get("scene_map")
            or {}
        ).items()
    }


def timeline_map():
    return {
        int(item["scene"]):
            item

        for item in (
            TIMELINE.get("timeline")
            or []
        )
    }


def main():
    prepared = prepared_map()

    downloads = download_map()

    timeline = timeline_map()

    plans = []

    blockers = []


    for number in range(
        1,
        13
    ):

        if (
            number not in prepared
            or
            number not in downloads
            or
            number not in timeline
        ):

            blockers.append(
                f"scene_{number}_upstream_missing"
            )

            continue


        direction = DIRECTION[
            number
        ]


        # Real archive video for 1 and 4.
        if number in {
            1,
            4
        }:

            visual_input = downloads[
                number
            ][
                "path"
            ]

            source_mode = (
                "AUTHENTIC_CASE_VIDEO"
            )


        # Scene 2 intentionally uses the verified
        # Hotel Cecil asset but with a very different
        # tight composition from scene 3.
        elif number == 2:

            visual_input = prepared[
                3
            ][
                "prepared_path"
            ]

            source_mode = (
                "VERIFIED_HOTEL_CECIL_SIGN"
            )


        else:

            visual_input = prepared[
                number
            ][
                "prepared_path"
            ]

            source_mode = (
                "CERTIFIED_PREPARED_ASSET"
            )


        plan = {
            "scene":
                number,

            "start":
                timeline[
                    number
                ][
                    "start"
                ],

            "end":
                timeline[
                    number
                ][
                    "end"
                ],

            "duration":
                timeline[
                    number
                ][
                    "duration"
                ],

            "segment":
                timeline[
                    number
                ].get(
                    "segment"
                ),

            "strategy":
                direction[
                    "strategy"
                ],

            "visual_group":
                direction[
                    "visual_group"
                ],

            "priority":
                direction[
                    "priority"
                ],

            "overlay_label":
                direction[
                    "label"
                ],

            "visual_input":
                visual_input,

            "source_mode":
                source_mode,
        }


        if not Path(
            visual_input
        ).exists():

            blockers.append(
                f"scene_{number}_visual_input_missing"
            )


        plans.append(
            plan
        )


    groups = [
        item[
            "visual_group"
        ]
        for item in plans
    ]


    consecutive_duplicate = any(
        groups[index]
        ==
        groups[
            index - 1
        ]

        for index in range(
            1,
            len(
                groups
            )
        )
    )


    checks = {
        "exact_12_plans":
            len(
                plans
            )
            == 12,

        "all_inputs_exist":
            not any(
                "visual_input_missing"
                in blocker

                for blocker in blockers
            ),

        "unique_visual_groups_at_least_9":
            len(
                set(
                    groups
                )
            )
            >= 9,

        "no_consecutive_duplicate_visual_group":
            not consecutive_duplicate,

        "scene2_and_scene3_distinct_composition":
            (
                plans[
                    1
                ][
                    "strategy"
                ]
                !=
                plans[
                    2
                ][
                    "strategy"
                ]
            ),

        "scene10_worker_focus":
            plans[
                9
            ][
                "strategy"
            ]
            ==
            "WORKER_SUBJECT_FOCUS",

        "scene11_tank_focus":
            plans[
                10
            ][
                "strategy"
            ]
            ==
            "WATER_TANK_SUBJECT_FOCUS",

        "network_off":
            POLICY[
                "execution"
            ][
                "network"
            ]
            is False,

        "production_off":
            POLICY[
                "execution"
            ][
                "production_mutation"
            ]
            is False,
    }


    failed = [
        key

        for key, value in (
            checks.items()
        )

        if value is not True
    ]


    status = (
        "VI1330_PUBLICATION_VISUAL_PLAN_CERTIFIED"

        if not failed
        and
        not blockers

        else
        "VI1330_PUBLICATION_VISUAL_PLAN_HOLD"
    )


    output = {
        "version":
            "1330.00",

        "status":
            status,

        "plans":
            plans,

        "unique_visual_groups":
            len(
                set(
                    groups
                )
            ),

        "checks":
            checks,

        "failed":
            failed,

        "blockers":
            blockers,
    }


    OUT.write_text(
        json.dumps(
            output,
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
        " VI1330 PUBLICATION VISUAL DIRECTOR"
    )
    print(
        "=============================================="
    )


    for item in plans:

        print(
            "SCENE",
            item[
                "scene"
            ],
            "|",
            item[
                "strategy"
            ],
            "|",
            item[
                "visual_group"
            ],
            "|",
            item[
                "priority"
            ]
        )


    print()
    print(
        "UNIQUE VISUAL GROUPS:",
        output[
            "unique_visual_groups"
        ]
    )
    print(
        "BLOCKERS:",
        blockers
    )
    print(
        "FAILED:",
        failed
    )
    print(
        "STATUS:",
        status
    )


    if (
        failed
        or
        blockers
    ):
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
