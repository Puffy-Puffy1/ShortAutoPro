#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1320_visual_director_policy.json"
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
    / "temp/vi1320/visual_plan.json"
)


def prepared_by_scene():
    return {
        int(item["scene"]):
            item

        for item in (
            PREPARED.get("prepared")
            or []
        )
    }


def source_by_scene():
    return {
        int(scene):
            asset

        for scene, asset in (
            DOWNLOAD.get("scene_map")
            or {}
        ).items()
    }


def main():
    prepared = prepared_by_scene()
    sources = source_by_scene()

    plans = []

    blockers = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1320 VISUAL DIRECTOR 2.0"
    )
    print(
        "=============================================="
    )

    for item in TIMELINE["timeline"]:
        number = int(
            item["scene"]
        )

        prep = prepared.get(
            number
        )

        source = sources.get(
            number
        )

        if not prep:
            blockers.append(
                f"scene_{number}_prepared_missing"
            )
            continue

        if not source:
            blockers.append(
                f"scene_{number}_source_missing"
            )
            continue

        direction = (
            POLICY[
                "scene_direction"
            ][
                str(number)
            ][
                "strategy"
            ]
        )

        # S2 deliberately reuses the verified Hotel Cecil
        # facade from S3, but focuses on the hotel sign.
        if number == 2:
            visual_input = (
                prepared[
                    3
                ][
                    "prepared_path"
                ]
            )

            source_mode = (
                "VERIFIED_HOTEL_CECIL_REFRAMED"
            )

        # S1/S4 use the authentic archive video itself.
        elif number in {
            1,
            4,
        }:
            visual_input = (
                source[
                    "path"
                ]
            )

            source_mode = (
                "AUTHENTIC_CASE_VIDEO"
            )

        else:
            visual_input = (
                prep[
                    "prepared_path"
                ]
            )

            source_mode = (
                "CERTIFIED_PREPARED_ASSET"
            )

        plan = {
            "scene":
                number,

            "start":
                item["start"],

            "end":
                item["end"],

            "duration":
                item["duration"],

            "strategy":
                direction,

            "visual_input":
                visual_input,

            "source_mode":
                source_mode,

            "overlay_label":
                POLICY[
                    "labels"
                ][
                    f"scene_{number}"
                ],

            "segment":
                item.get(
                    "segment"
                ),

            "production_mutation":
                False,
        }

        plans.append(
            plan
        )

        print(
            "SCENE",
            number,
            "|",
            direction,
            "|",
            source_mode,
            "|",
            Path(
                visual_input
            ).name
        )

    checks = {
        "exactly_12_scenes":
            len(plans) == 12,

        "scene_set_1_to_12":
            {
                item["scene"]
                for item in plans
            }
            ==
            set(
                range(
                    1,
                    13
                )
            ),

        "all_visual_inputs_exist":
            all(
                Path(
                    item[
                        "visual_input"
                    ]
                ).exists()

                for item in plans
            ),

        "scene1_real_archive":
            plans[
                0
            ][
                "source_mode"
            ]
            ==
            "AUTHENTIC_CASE_VIDEO",

        "scene4_real_archive":
            plans[
                3
            ][
                "source_mode"
            ]
            ==
            "AUTHENTIC_CASE_VIDEO",

        "scene5_labeled":
            plans[
                4
            ][
                "overlay_label"
            ]
            ==
            "IMAGEM ILUSTRATIVA",

        "scene7_labeled":
            plans[
                6
            ][
                "overlay_label"
            ]
            ==
            "IMAGEM ILUSTRATIVA",

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
        for key, value
        in checks.items()
        if value is not True
    ]

    status = (
        "VI1320_VISUAL_PLAN_CERTIFIED"
        if not failed
        and
        not blockers
        else
        "VI1320_VISUAL_PLAN_HOLD"
    )

    output = {
        "version":
            "1320.00",

        "status":
            status,

        "plans":
            plans,

        "checks":
            checks,

        "failed_checks":
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
        "PLANS:",
        len(plans)
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
        raise SystemExit(1)


if __name__ == "__main__":
    main()
