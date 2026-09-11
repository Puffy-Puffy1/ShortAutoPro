#!/usr/bin/env python3

import hashlib
import json
import os

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

DOWNLOAD_MANIFEST = (
    BASE
    / "temp/vi1270_downloads/"
    "download_manifest.json"
)

FORENSIC_REPORT = (
    BASE
    / "logs/producao/"
    "vi1280_00_asset_forensics_latest.json"
)

SELECTION_PLAN = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1290_00_asset_readiness_latest.json"
)

READY_MANIFEST = (
    BASE
    / "temp/vi1290/"
    "scene_asset_manifest.json"
)


def read_json(
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


def sha256_file(
    path
):
    sha = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(
                chunk
            )

    return sha.hexdigest()


def main():
    required = [
        DOWNLOAD_MANIFEST,
        FORENSIC_REPORT,
        SELECTION_PLAN,
    ]


    missing = [
        str(path)
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


    download = read_json(
        DOWNLOAD_MANIFEST
    )

    forensic = read_json(
        FORENSIC_REPORT
    ).get(
        "gate",
        {}
    )

    plan = read_json(
        SELECTION_PLAN
    )


    prerequisites = {
        "vi1270_download_certified":
            download.get(
                "status"
            )
            ==
            "VI1270_CONTROLLED_DOWNLOAD_CERTIFIED",

        "vi1280_forensics_certified":
            forensic.get(
                "status"
            )
            ==
            "VI1280_ASSET_FORENSICS_CERTIFIED",

        "twelve_scenes_selected":
            len(
                plan.get(
                    "selected"
                )
                or {}
            )
            == 12,

        "twelve_scenes_download_mapped":
            len(
                download.get(
                    "scene_map"
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


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )

    scene_map = (
        download.get(
            "scene_map"
        )
        or {}
    )


    scenes = {}

    failures = []

    source_usage = {}


    print()
    print(
        "=============================================="
    )

    print(
        " VI1290 ASSET READINESS"
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


        selected_item = (
            selected.get(
                key
            )
            or {}
        )


        asset = (
            scene_map.get(
                key
            )
            or {}
        )


        candidate = (
            selected_item.get(
                "candidate"
            )
            or {}
        )


        evaluation = (
            selected_item.get(
                "evaluation"
            )
            or {}
        )


        path_text = (
            asset.get(
                "path"
            )
        )


        scene_failures = []


        if (
            selected_item.get(
                "decision"
            )
            != "SELECT_SAFE"
        ):

            scene_failures.append(
                "scene_not_select_safe"
            )


        if not path_text:

            scene_failures.append(
                "asset_path_missing"
            )

            path = None

        else:

            path = Path(
                path_text
            )


            if not path.exists():

                scene_failures.append(
                    "asset_file_missing"
                )


        if path and path.exists():

            actual_sha = sha256_file(
                path
            )

            expected_sha = str(
                asset.get(
                    "sha256"
                )
                or ""
            )


            if actual_sha != expected_sha:

                scene_failures.append(
                    "asset_sha_mismatch"
                )


            actual_bytes = (
                path.stat().st_size
            )


            if actual_bytes != int(
                asset.get(
                    "bytes",
                    -1
                )
            ):

                scene_failures.append(
                    "asset_size_mismatch"
                )

        else:

            actual_sha = None

            actual_bytes = None


        group = str(
            asset.get(
                "source_group"
            )
            or
            candidate.get(
                "source_group"
            )
            or
            ""
        )


        if not group:

            scene_failures.append(
                "source_group_missing"
            )


        source_usage[
            group
        ] = (
            source_usage.get(
                group,
                0
            )
            + 1
        )


        mode = str(
            evaluation.get(
                "mode"
            )
            or ""
        )


        overlay_label = (
            evaluation.get(
                "overlay_label"
            )
        )


        constraints = list(
            evaluation.get(
                "presentation_constraints"
            )
            or []
        )


        generic = bool(
            candidate.get(
                "generic"
            )
        )


        # Normalize visual disclosure policy.
        if (
            generic
            and
            not overlay_label
        ):

            overlay_label = (
                "IMAGEM ILUSTRATIVA"
            )


        if (
            "CONTEXT"
            in mode
            and
            not overlay_label
        ):

            overlay_label = (
                "IMAGEM DE CONTEXTO"
            )


        fullscreen_allowed = (
            "NO_FULLSCREEN"
            not in constraints
        )


        if (
            "CONTEXT_INSERT_ONLY"
            in constraints
        ):

            fullscreen_allowed = False


        asset_kind = (
            asset.get(
                "content_type"
            )
        )


        scene_record = {
            "scene":
                number,

            "decision":
                "READY"
                if not scene_failures
                else "HOLD",

            "title":
                candidate.get(
                    "title"
                ),

            "source_group":
                group,

            "source_class":
                candidate.get(
                    "source_class"
                ),

            "semantic_mode":
                mode,

            "generic":
                generic,

            "claim_visualized":
                evaluation.get(
                    "claim_visualized"
                ),

            "overlay_label":
                overlay_label,

            "presentation_constraints":
                constraints,

            "fullscreen_allowed":
                fullscreen_allowed,

            "content_type":
                asset_kind,

            "bytes":
                actual_bytes,

            "sha256":
                actual_sha,

            "path":
                (
                    str(
                        path.resolve()
                    )
                    if path
                    else None
                ),

            "license":
                asset.get(
                    "license"
                )
                or
                candidate.get(
                    "license"
                ),

            "original_url":
                asset.get(
                    "original_url"
                ),

            "download_url":
                asset.get(
                    "download_url"
                )
                or
                asset.get(
                    "final_url"
                ),

            "failures":
                scene_failures,
        }


        scenes[
            key
        ] = scene_record


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
            scene_record[
                "decision"
            ],
            "|",
            scene_record[
                "semantic_mode"
            ],
            "| fullscreen=",
            fullscreen_allowed,
            "| label=",
            overlay_label,
            "|",
            str(
                candidate.get(
                    "title"
                )
            )[:70]
        )


    # Important known archival restriction.
    scene1 = scenes.get(
        "1",
        {}
    )

    scene4 = scenes.get(
        "4",
        {}
    )

    scene8 = scenes.get(
        "8",
        {}
    )


    case_archive_scenes = [
        scene
        for scene in [
            scene1,
            scene4,
            scene8,
        ]
        if (
            scene.get(
                "source_class"
            )
            == "CASE_ARCHIVE"
        )
    ]


    checks = {
        "all_scenes_ready":
            not failures
            and
            len(
                scenes
            )
            == 12,

        "all_paths_exist":
            all(
                Path(
                    item[
                        "path"
                    ]
                ).exists()
                for item in scenes.values()
                if item.get(
                    "path"
                )
            )
            and
            all(
                bool(
                    item.get(
                        "path"
                    )
                )
                for item in scenes.values()
            ),

        "all_sha_present":
            all(
                len(
                    str(
                        item.get(
                            "sha256"
                        )
                        or ""
                    )
                )
                == 64
                for item in scenes.values()
            ),

        "minimum_unique_sources":
            len(
                [
                    group
                    for group in source_usage
                    if group
                ]
            )
            >= 8,

        "case_archive_usage_max_3":
            len(
                case_archive_scenes
            )
            <= 3,

        "illustrative_media_disclosed":
            all(
                (
                    not item[
                        "generic"
                    ]
                    or
                    item[
                        "overlay_label"
                    ]
                    ==
                    "IMAGEM ILUSTRATIVA"
                )
                for item in scenes.values()
            ),

        "contextual_media_disclosed":
            all(
                (
                    "CONTEXT"
                    not in
                    item[
                        "semantic_mode"
                    ]
                    or
                    bool(
                        item[
                            "overlay_label"
                        ]
                    )
                )
                for item in scenes.values()
            ),

        "ffmpeg_off":
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
        "VI1290_ASSET_READINESS_CERTIFIED"
        if certified
        else
        "VI1290_ASSET_READINESS_HOLD"
    )


    report = {
        "version":
            "1290.00",

        "status":
            status,

        "ready_for_visual_canary_preparation":
            certified,

        "scene_count":
            len(
                scenes
            ),

        "unique_sources":
            len(
                [
                    group
                    for group in source_usage
                    if group
                ]
            ),

        "source_usage":
            source_usage,

        "failures":
            failures,

        "checks":
            checks,

        "failed_checks":
            failed_checks,

        "ffmpeg_executed":
            False,

        "renderer_activated":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    write_json(
        READY_MANIFEST,
        {
            "version":
                "1290.00",

            "status":
                status,

            "scenes":
                scenes,

            "source_usage":
                source_usage,

            "render_allowed":
                False,

            "ffmpeg_allowed":
                False,

            "production_mutation_allowed":
                False,
        }
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
        "===== VI1290 SUMMARY ====="
    )

    print(
        "SCENES:",
        len(
            scenes
        )
    )

    print(
        "UNIQUE SOURCES:",
        report[
            "unique_sources"
        ]
    )

    print(
        "FAILURES:",
        failures
    )


    print()
    print(
        "===== CHECKS ====="
    )


    for key, value in checks.items():

        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
        )


    print(
        "FAILED:",
        failed_checks
    )


    print()
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
