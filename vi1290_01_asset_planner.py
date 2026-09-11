#!/usr/bin/env python3

import json
import math

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY_PATH = (
    BASE
    / "config/"
    "vi1290_render_readiness_policy.json"
)

FORENSICS_PATH = (
    BASE
    / "logs/producao/"
    "vi1280_00_asset_forensics_latest.json"
)

MANIFEST_PATH = (
    BASE
    / "temp/vi1270_downloads/"
    "download_manifest.json"
)

SELECTION_PATH = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

PLAN_OUT = (
    BASE
    / "temp/vi1290/"
    "render_readiness_plan.json"
)

REPORT_OUT = (
    BASE
    / "logs/producao/"
    "vi1290_01_asset_planner_latest.json"
)


def load_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(
    path,
    data
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


def asset_reports_by_group(
    forensic_gate
):
    output = {}


    for item in (
        forensic_gate.get(
            "assets"
        )
        or []
    ):

        group = item.get(
            "source_group"
        )


        if group:

            output[
                group
            ] = item


    return output


def scene_number_map(
    manifest
):
    output = {}


    for key, asset in (
        manifest.get(
            "scene_map"
        )
        or {}
    ).items():

        try:

            number = int(
                key
            )

        except Exception:

            continue


        output[
            number
        ] = asset


    return output


def selection_number_map(
    selection
):
    output = {}


    for key, item in (
        selection.get(
            "selected"
        )
        or {}
    ).items():

        try:

            number = int(
                key
            )

        except Exception:

            continue


        output[
            number
        ] = item


    return output


def required_crop(
    width,
    height,
    target_ratio
):
    source_ratio = (
        width
        /
        height
    )


    if math.isclose(
        source_ratio,
        target_ratio,
        rel_tol=0.02,
        abs_tol=0.01,
    ):

        return {
            "mode":
                "NONE",

            "crop_width":
                width,

            "crop_height":
                height,

            "retained_fraction":
                1.0,
        }


    if source_ratio > target_ratio:

        crop_height = height

        crop_width = int(
            round(
                height
                *
                target_ratio
            )
        )


        retained = (
            crop_width
            /
            width
        )


        return {
            "mode":
                "HORIZONTAL_CROP",

            "crop_width":
                crop_width,

            "crop_height":
                crop_height,

            "retained_fraction":
                retained,
        }


    crop_width = width

    crop_height = int(
        round(
            width
            /
            target_ratio
        )
    )


    retained = (
        crop_height
        /
        height
    )


    return {
        "mode":
            "VERTICAL_CROP",

        "crop_width":
            crop_width,

        "crop_height":
            crop_height,

        "retained_fraction":
            retained,
    }


def upscale_factor(
    crop_width,
    crop_height,
    target_width,
    target_height
):
    return max(
        target_width
        /
        crop_width,

        target_height
        /
        crop_height,
    )


def image_strategy(
    dimensions,
    policy,
    semantic_constraints
):
    if not dimensions:

        return {
            "ready":
                False,

            "strategy":
                "IMAGE_DIMENSIONS_REQUIRED",

            "blockers": [
                "image_dimensions_missing"
            ],
        }


    width = int(
        dimensions[
            "width"
        ]
    )

    height = int(
        dimensions[
            "height"
        ]
    )


    target = policy[
        "target"
    ]

    quality = policy[
        "quality"
    ]


    crop = required_crop(
        width,
        height,
        float(
            target[
                "aspect_ratio"
            ]
        )
    )


    factor = upscale_factor(
        crop[
            "crop_width"
        ],
        crop[
            "crop_height"
        ],
        int(
            target[
                "width"
        ]
        ),
        int(
            target[
                "height"
        ]
        ),
    )


    retained = float(
        crop[
            "retained_fraction"
        ]
    )


    force_context = (
        "NO_FULLSCREEN"
        in semantic_constraints
    )


    if (
        not force_context
        and
        factor
        <= float(
            quality[
                "maximum_fullscreen_upscale"
            ]
        )
        and
        retained >= 0.38
    ):

        strategy = (
            "FULLSCREEN_CENTER_CROP"
        )

        ready = True

        blockers = []


    elif (
        width
        >= int(
            quality[
                "minimum_insert_width"
            ]
        )
        and
        height
        >= int(
            quality[
                "minimum_insert_height"
            ]
        )
        and
        factor
        <= float(
            quality[
                "maximum_context_upscale"
            ]
        )
    ):

        strategy = (
            "FOREGROUND_INSERT_WITH_DERIVED_BLUR_BACKGROUND"
        )

        ready = True

        blockers = []


    else:

        strategy = (
            "CONTEXT_INSERT_LOW_RES"
        )

        ready = False

        blockers = [
            "image_resolution_insufficient_for_safe_presentation"
        ]


    return {
        "ready":
            ready,

        "strategy":
            strategy,

        "source_width":
            width,

        "source_height":
            height,

        "source_aspect_ratio":
            round(
                width
                /
                height,
                5
            ),

        "crop":
            crop,

        "required_upscale":
            round(
                factor,
                3
            ),

        "blockers":
            blockers,
    }


def presentation_label(
    scene_selection
):
    evaluation = (
        scene_selection.get(
            "evaluation"
        )
        or {}
    )


    explicit = evaluation.get(
        "overlay_label"
    )


    if explicit:

        return explicit


    mode = str(
        evaluation.get(
            "mode"
        )
        or ""
    )


    if (
        "ILLUSTRATION"
        in mode
        or
        "GENERIC"
        in mode
    ):

        return (
            "IMAGEM ILUSTRATIVA"
        )


    if (
        "CONTEXT"
        in mode
        or
        "ARCHIVAL"
        in mode
    ):

        return (
            "IMAGEM DE CONTEXTO"
        )


    return None


def plan_scene(
    number,
    asset,
    forensic,
    selection,
    policy
):
    kind = forensic.get(
        "magic_kind"
    )


    dimensions = forensic.get(
        "dimensions"
    )


    evaluation = (
        selection.get(
            "evaluation"
        )
        or {}
    )


    constraints = sorted(
        set(
            evaluation.get(
                "presentation_constraints"
            )
            or []
        )
    )


    label = presentation_label(
        selection
    )


    base = {
        "scene":
            number,

        "source_group":
            asset.get(
                "source_group"
            ),

        "title":
            asset.get(
                "title"
            ),

        "path":
            asset.get(
                "path"
            ),

        "sha256":
            asset.get(
                "sha256"
            ),

        "kind":
            kind,

        "semantic_mode":
            evaluation.get(
                "mode"
            ),

        "claim_visualized":
            evaluation.get(
                "claim_visualized"
            ),

        "overlay_label":
            label,

        "presentation_constraints":
            constraints,

        "network_required":
            False,

        "download_required":
            False,

        "ffmpeg_executed":
            False,

        "render_executed":
            False,
    }


    if kind in {
        "JPEG",
        "PNG",
        "WEBP",
    }:

        image_plan = image_strategy(
            dimensions,
            policy,
            constraints
        )


        base.update(
            image_plan
        )


        base[
            "pre_render_action"
        ] = (
            "IMAGE_PREP"
        )


        return base


    if kind == "WEBM":

        base.update({
            "ready":
                True,

            "strategy":
                "ARCHIVAL_VIDEO_INSERT",

            "pre_render_action":
                "VIDEO_PROBE_AND_CLIP_PLAN",

            "probe_required":
                True,

            "fullscreen_allowed":
                False,

            "blockers":
                [],
        })


        if (
            "NO_FULLSCREEN"
            not in constraints
        ):

            constraints.append(
                "NO_FULLSCREEN"
            )


        base[
            "presentation_constraints"
        ] = sorted(
            set(
                constraints
            )
        )


        if not base[
            "overlay_label"
        ]:

            base[
                "overlay_label"
            ] = (
                "IMAGEM DE CONTEXTO"
            )


        return base


    if kind == "PDF":

        base.update({
            "ready":
                True,

            "strategy":
                "DOCUMENT_PAGE_INSERT",

            "pre_render_action":
                "PDF_PAGE_RASTERIZATION_PLAN",

            "page":
                int(
                    policy[
                        "special_media"
                    ][
                        "pdf"
                    ][
                        "page"
                    ]
                ),

            "fullscreen_allowed":
                False,

            "blockers":
                [],
        })


        constraints.append(
            "DOCUMENT_CONTEXT_ONLY"
        )


        base[
            "presentation_constraints"
        ] = sorted(
            set(
                constraints
            )
        )


        if not base[
            "overlay_label"
        ]:

            base[
                "overlay_label"
            ] = (
                "DOCUMENTO DO CASO"
            )


        return base


    base.update({
        "ready":
            False,

        "strategy":
            "UNSUPPORTED_MEDIA",

        "pre_render_action":
            "HOLD",

        "blockers": [
            "unsupported_magic_kind"
        ],
    })


    return base


def main():
    policy = load_json(
        POLICY_PATH
    )


    forensic_gate = (
        load_json(
            FORENSICS_PATH
        ).get(
            "gate",
            {}
        )
    )


    manifest = load_json(
        MANIFEST_PATH
    )


    selection = load_json(
        SELECTION_PATH
    )


    if (
        forensic_gate.get(
            "status"
        )
        !=
        "VI1280_1_ASSET_FORENSICS_CERTIFIED"
    ):

        raise SystemExit(
            "VI1290 BLOCKED: VI1280.1 NOT CERTIFIED"
        )


    assets_by_group = (
        asset_reports_by_group(
            forensic_gate
        )
    )


    scenes = scene_number_map(
        manifest
    )


    selections = (
        selection_number_map(
            selection
        )
    )


    plans = []

    blockers = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1290 ASSET PREPARATION + RENDER READINESS"
    )

    print(
        "=============================================="
    )


    for number in range(
        1,
        13
    ):

        asset = scenes.get(
            number
        )


        selected = selections.get(
            number
        )


        if not asset:

            blockers.append(
                f"scene_{number}_asset_missing"
            )

            continue


        if not selected:

            blockers.append(
                f"scene_{number}_selection_missing"
            )

            continue


        group = asset.get(
            "source_group"
        )


        forensic = (
            assets_by_group.get(
                group
            )
        )


        if not forensic:

            blockers.append(
                f"scene_{number}_forensic_record_missing"
            )

            continue


        plan = plan_scene(
            number,
            asset,
            forensic,
            selected,
            policy
        )


        plans.append(
            plan
        )


        if not plan.get(
            "ready"
        ):

            blockers.extend(
                [
                    (
                        f"scene_{number}:"
                        + reason
                    )

                    for reason in (
                        plan.get(
                            "blockers"
                        )
                        or []
                    )
                ]
            )


        dims = "-"


        if forensic.get(
            "dimensions"
        ):

            dims = (
                str(
                    forensic[
                        "dimensions"
                    ][
                        "width"
                    ]
                )
                + "x"
                + str(
                    forensic[
                        "dimensions"
                    ][
                        "height"
                    ]
                )
            )


        print(
            "SCENE",
            number,
            "|",
            plan.get(
                "kind"
            ),
            "|",
            dims,
            "|",
            plan.get(
                "strategy"
            ),
            "| label=",
            plan.get(
                "overlay_label"
            ),
            "|",
            (
                "READY"
                if plan.get(
                    "ready"
                )
                else "HOLD"
            )
        )


    exact_12 = (
        len(
            plans
        )
        == 12
    )


    all_ready = (
        exact_12
        and
        all(
            item.get(
                "ready"
            )
            is True

            for item in plans
        )
    )


    labels_correct = all(
        (
            item.get(
                "overlay_label"
            )
            is not None
        )

        if (
            "ILLUSTRATION"
            in str(
                item.get(
                    "semantic_mode"
                )
                or ""
            )

            or

            "GENERIC"
            in str(
                item.get(
                    "semantic_mode"
                )
                or ""
            )
        )

        else True

        for item in plans
    )


    no_false_fullscreen = all(
        not (
            "NO_FULLSCREEN"
            in (
                item.get(
                    "presentation_constraints"
                )
                or []
            )

            and

            item.get(
                "strategy"
            )
            ==
            "FULLSCREEN_CENTER_CROP"
        )

        for item in plans
    )


    checks = {
        "vi1280_1_certified":
            forensic_gate.get(
                "status"
            )
            ==
            "VI1280_1_ASSET_FORENSICS_CERTIFIED",

        "exactly_12_scene_plans":
            exact_12,

        "all_scene_assets_ready":
            all_ready,

        "generic_media_labeled":
            labels_correct,

        "no_restricted_asset_fullscreen":
            no_false_fullscreen,

        "network_off":
            policy[
                "execution"
            ][
                "network"
            ]
            is False,

        "downloads_off":
            policy[
                "execution"
            ][
                "downloads"
            ]
            is False,

        "ffmpeg_off":
            policy[
                "execution"
            ][
                "ffmpeg"
            ]
            is False,

        "ffprobe_off":
            policy[
                "execution"
            ][
                "ffprobe"
            ]
            is False,

        "renderer_off":
            policy[
                "execution"
            ][
                "renderer"
            ]
            is False,

        "video_generation_off":
            policy[
                "execution"
            ][
                "video_generation"
            ]
            is False,

        "production_mutation_off":
            policy[
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


    certified = (
        not failed
        and
        not blockers
    )


    status = (
        "VI1290_RENDER_READINESS_CERTIFIED"

        if certified

        else
        "VI1290_RENDER_READINESS_HOLD"
    )


    result = (
        "READY_FOR_CONTROLLED_ASSET_PREPARATION_CANARY"

        if certified

        else
        "ASSET_PREPARATION_REPAIR_REQUIRED"
    )


    output = {
        "version":
            "1290.00",

        "status":
            status,

        "result":
            result,

        "target":
            policy[
                "target"
            ],

        "scene_plans":
            plans,

        "checks":
            checks,

        "failed_checks":
            failed,

        "blockers":
            blockers,

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
    }


    write_json(
        PLAN_OUT,
        output
    )


    write_json(
        REPORT_OUT,
        {
            "gate":
                output
        }
    )


    print()
    print(
        "===== VI1290 SUMMARY ====="
    )

    print(
        "SCENE PLANS:",
        len(
            plans
        )
    )

    print(
        "READY:",
        sum(
            1
            for item in plans
            if item.get(
                "ready"
            )
        )
    )

    print(
        "BLOCKERS:",
        blockers
    )


    print()
    print(
        "===== CHECKS ====="
    )


    for key, value in (
        checks.items()
    ):

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
        failed
    )


    print()
    print(
        "NETWORK EXECUTED: False"
    )

    print(
        "DOWNLOAD EXECUTED: False"
    )

    print(
        "FFPROBE EXECUTED: False"
    )

    print(
        "FFMPEG EXECUTED: False"
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


    print()
    print(
        "STATUS:",
        status
    )

    print(
        "VI1290 RESULT:",
        result
    )


    if not certified:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
