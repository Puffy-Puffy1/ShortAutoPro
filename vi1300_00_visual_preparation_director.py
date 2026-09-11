#!/usr/bin/env python3

import hashlib
import json

from pathlib import Path


from vi1300_01_presentation_safety import (
    resolve_dimensions,
    choose_strategy,
    disclosure_label,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1300_visual_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

READINESS = (
    BASE
    / "temp/vi1290/"
    "scene_asset_manifest.json"
)

SELECTION = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

FORENSICS = (
    BASE
    / "logs/producao/"
    "vi1280_00_asset_forensics_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1300_00_visual_preparation_director_latest.json"
)

PLAN = (
    BASE
    / "temp/vi1300/"
    "visual_preparation_plan.json"
)


def read_json(
    path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(
    path,
    data,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def source_fingerprint(
    scene,
):
    raw = "|".join([
        str(
            scene.get(
                "source_group"
            )
            or ""
        ),

        str(
            scene.get(
                "sha256"
            )
            or ""
        ),

        str(
            scene.get(
                "strategy"
            )
            or ""
        ),

        str(
            scene.get(
                "overlay_label"
            )
            or ""
        ),
    ])


    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


def motion_profile(
    strategy,
    scene_number,
):
    if strategy == "ARCHIVAL_INSET":

        return {
            "motion":
                "SLOW_SCALE_INSET",

            "scale_start":
                1.00,

            "scale_end":
                1.04,

            "pan":
                "NONE",
        }


    if strategy == "DOCUMENT_PAGE_PREVIEW":

        return {
            "motion":
                "SLOW_DOCUMENT_PUSH",

            "scale_start":
                1.00,

            "scale_end":
                1.06,

            "pan":
                "VERTICAL_SUBTLE",
        }


    if strategy == "IMAGE_INSET":

        return {
            "motion":
                "SLOW_INSET_PUSH",

            "scale_start":
                1.00,

            "scale_end":
                1.05,

            "pan":
                "NONE",
        }


    if strategy == "IMAGE_COVER":

        variants = [
            "SLOW_PUSH",
            "SLOW_PULL",
            "SUBTLE_VERTICAL",
            "SUBTLE_HORIZONTAL",
        ]


        value = variants[
            (
                scene_number
                - 1
            )
            %
            len(
                variants
            )
        ]


        return {
            "motion":
                value,

            "scale_start":
                (
                    1.00
                    if value
                    != "SLOW_PULL"
                    else 1.06
                ),

            "scale_end":
                (
                    1.06
                    if value
                    != "SLOW_PULL"
                    else 1.00
                ),

            "pan":
                value,
        }


    if strategy == "VIDEO_COVER":

        return {
            "motion":
                "SOURCE_VIDEO",

            "scale_start":
                1.00,

            "scale_end":
                1.00,

            "pan":
                "SOURCE",
        }


    return {
        "motion":
            "NONE",

        "scale_start":
            1.00,

        "scale_end":
            1.00,

        "pan":
            "NONE",
    }


def main():
    required = [
        READINESS,
        SELECTION,
        FORENSICS,
    ]


    missing = [
        str(
            path
        )
        for path in required
        if not path.exists()
    ]


    if missing:

        print(
            "MISSING:",
            missing
        )

        raise SystemExit(
            1
        )


    readiness = read_json(
        READINESS
    )

    selection = read_json(
        SELECTION
    )

    forensic = read_json(
        FORENSICS
    ).get(
        "gate",
        {}
    )


    prerequisites = {
        "vi1290_certified":
            readiness.get(
                "status"
            )
            ==
            "VI1290_ASSET_READINESS_CERTIFIED",

        "vi1280_certified":
            forensic.get(
                "status"
            )
            ==
            "VI1280_ASSET_FORENSICS_CERTIFIED",

        "twelve_scene_records":
            len(
                readiness.get(
                    "scenes"
                )
                or {}
            )
            == 12,
    }


    if not all(
        prerequisites.values()
    ):

        print(
            "PREREQUISITES:",
            prerequisites
        )

        raise SystemExit(
            1
        )


    scenes = (
        readiness.get(
            "scenes"
        )
        or {}
    )

    selected = (
        selection.get(
            "selected"
        )
        or {}
    )

    forensic_assets = (
        forensic.get(
            "assets"
        )
        or []
    )


    output_scenes = {}

    failures = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1300 VISUAL PREPARATION DIRECTOR"
    )

    print(
        "=============================================="
    )


    for number in range(
        1,
        13
    ):

        key = str(
            number
        )


        scene = dict(
            scenes[
                key
            ]
        )


        selected_item = (
            selected.get(
                key
            )
            or {}
        )


        dimensions = (
            resolve_dimensions(
                scene.get(
                    "source_group"
                ),
                selected_item,
                forensic_assets,
            )
        )


        presentation = (
            choose_strategy(
                scene,
                dimensions,
            )
        )


        label = disclosure_label(
            scene
        )


        strategy = presentation[
            "strategy"
        ]


        constraints = (
            presentation[
                "constraints"
            ]
        )


        scene_failures = []


        if strategy == "HOLD":

            scene_failures.append(
                "no_visual_strategy"
            )


        if (
            scene.get(
                "generic"
            )
            and
            label
            !=
            "IMAGEM ILUSTRATIVA"
        ):

            scene_failures.append(
                "generic_disclosure_missing"
            )


        if (
            "CONTEXT"
            in str(
                scene.get(
                    "semantic_mode"
                )
                or ""
            )
            and
            not label
        ):

            scene_failures.append(
                "context_disclosure_missing"
            )


        if (
            presentation[
                "fullscreen_allowed"
            ]
            and
            not presentation[
                "quality_fullscreen_pass"
            ]
        ):

            scene_failures.append(
                "fullscreen_without_quality_gate"
            )


        record = {
            **scene,

            "dimensions":
                dimensions,

            "strategy":
                strategy,

            "fullscreen_allowed":
                presentation[
                    "fullscreen_allowed"
                ],

            "quality_fullscreen_pass":
                presentation[
                    "quality_fullscreen_pass"
                ],

            "overlay_label":
                label,

            "presentation_constraints":
                constraints,

            "motion_profile":
                motion_profile(
                    strategy,
                    number,
                ),

            "target_canvas": {
                "width":
                    POLICY[
                        "canvas"
                    ][
                        "width"
                    ],

                "height":
                    POLICY[
                        "canvas"
                    ][
                        "height"
                    ],

                "fps":
                    POLICY[
                        "canvas"
                    ][
                        "fps"
                    ],
            },

            "prepared_asset_path":
                None,

            "transformation_executed":
                False,

            "failures":
                scene_failures,
        }


        record[
            "preparation_fingerprint"
        ] = source_fingerprint(
            record
        )


        output_scenes[
            key
        ] = record


        if scene_failures:

            failures.append({
                "scene":
                    number,

                "failures":
                    scene_failures,
            })


        print(
            "SCENE",
            number,
            "|",
            (
                "READY"
                if not scene_failures
                else "HOLD"
            ),
            "|",
            strategy,
            "| source=",
            (
                (
                    str(
                        dimensions[
                            "width"
                        ]
                    )
                    + "x"
                    + str(
                        dimensions[
                            "height"
                        ]
                    )
                )
                if (
                    dimensions.get(
                        "width"
                    )
                    and
                    dimensions.get(
                        "height"
                    )
                )
                else "UNKNOWN"
            ),
            "| fullscreen=",
            presentation[
                "fullscreen_allowed"
            ],
            "| label=",
            label
        )


    scene1 = output_scenes[
        "1"
    ]

    scene3 = output_scenes[
        "3"
    ]

    scene4 = output_scenes[
        "4"
    ]

    scene12 = output_scenes[
        "12"
    ]


    checks = {
        "all_12_scenes_planned":
            len(
                output_scenes
            )
            == 12,

        "all_scenes_have_visual_strategy":
            not failures,

        "low_res_scene1_not_fullscreen":
            scene1[
                "fullscreen_allowed"
            ]
            is False,

        "low_res_scene4_not_fullscreen":
            scene4[
                "fullscreen_allowed"
            ]
            is False,

        "scene3_low_res_context_not_fullscreen":
            scene3[
                "fullscreen_allowed"
            ]
            is False,

        "scene12_pdf_document_strategy":
            scene12[
                "strategy"
            ]
            ==
            "DOCUMENT_PAGE_PREVIEW",

        "scene12_raw_pdf_not_fullscreen":
            scene12[
                "fullscreen_allowed"
            ]
            is False,

        "all_generic_assets_disclosed":
            all(
                (
                    not scene[
                        "generic"
                    ]
                    or
                    scene[
                        "overlay_label"
                    ]
                    ==
                    "IMAGEM ILUSTRATIVA"
                )

                for scene in (
                    output_scenes.values()
                )
            ),

        "no_transformations_executed":
            all(
                scene[
                    "transformation_executed"
                ]
                is False

                for scene in (
                    output_scenes.values()
                )
            ),

        "network_off":
            True,

        "downloads_off":
            True,

        "ffmpeg_off":
            True,

        "ffprobe_off":
            True,

        "renderer_off":
            True,

        "video_generation_off":
            True,

        "production_mutation_off":
            True,
    }


    failed_checks = [
        key

        for key, value
        in checks.items()

        if value is not True
    ]


    certified = (
        not failed_checks
    )


    status = (
        "VI1300_VISUAL_PREPARATION_CERTIFIED"

        if certified

        else
        "VI1300_VISUAL_PREPARATION_HOLD"
    )


    plan = {
        "version":
            "1300.00",

        "status":
            status,

        "canvas":
            POLICY[
                "canvas"
            ],

        "scenes":
            output_scenes,

        "failures":
            failures,

        "execution": {
            "network":
                False,

            "downloads":
                False,

            "ffmpeg":
                False,

            "ffprobe":
                False,

            "renderer":
                False,

            "video_generation":
                False,

            "production_mutation":
                False,
        },

        "ready_for_controlled_asset_transformation":
            certified,
    }


    report = {
        "version":
            "1300.00",

        "status":
            status,

        "scene_count":
            len(
                output_scenes
            ),

        "strategies": {
            key:
                value[
                    "strategy"
                ]

            for key, value
            in output_scenes.items()
        },

        "fullscreen_allowed": {
            key:
                value[
                    "fullscreen_allowed"
                ]

            for key, value
            in output_scenes.items()
        },

        "failures":
            failures,

        "checks":
            checks,

        "failed_checks":
            failed_checks,

        "ready_for_controlled_asset_transformation":
            certified,

        "network_executed":
            False,

        "download_executed":
            False,

        "ffmpeg_executed":
            False,

        "ffprobe_executed":
            False,

        "renderer_activated":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    write_json(
        PLAN,
        plan
    )


    write_json(
        OUT,
        {
            "gate":
                report
        }
    )


    print()
    print(
        "===== VI1300 CHECKS ====="
    )


    for key, value in checks.items():

        print(
            key,
            "=",
            (
                "PASS"
                if value
                else "FAIL"
            )
        )


    print(
        "FAILED:",
        failed_checks
    )


    print()
    print(
        "NETWORK EXECUTED: False"
    )

    print(
        "DOWNLOAD EXECUTED: False"
    )

    print(
        "FFMPEG EXECUTED: False"
    )

    print(
        "FFPROBE EXECUTED: False"
    )

    print(
        "VIDEO GENERATED: False"
    )

    print(
        "RENDERER ACTIVATED: False"
    )

    print(
        "PRODUCTION MUTATED: False"
    )

    print(
        "STATUS:",
        status
    )


    if not certified:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
