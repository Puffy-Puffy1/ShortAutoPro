#!/usr/bin/env python3

import hashlib
import json

from pathlib import Path


from vi1400_01_transform_core import (
    transform,
)


BASE = Path.home() / "ShortAutoPro"

PLAN = (
    BASE
    / "temp/vi1300/"
    "visual_preparation_plan.json"
)

OUT_DIR = (
    BASE
    / "temp/vi1400/prepared"
)

WORK = (
    BASE
    / "temp/vi1400/work"
)

MANIFEST = (
    BASE
    / "temp/vi1400/"
    "prepared_manifest.json"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1400_02_asset_transformer_latest.json"
)


def read_json(
    path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256_file(
    path,
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


def main():
    data = read_json(
        PLAN
    )

    if (
        data.get(
            "status"
        )
        !=
        "VI1300_VISUAL_PREPARATION_CERTIFIED"
    ):

        raise SystemExit(
            "VI1300_NOT_CERTIFIED"
        )

    scenes = (
        data.get(
            "scenes"
        )
        or {}
    )

    if len(
        scenes
    ) != 12:

        raise SystemExit(
            "EXPECTED_12_SCENES"
        )

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    WORK.mkdir(
        parents=True,
        exist_ok=True
    )

    results = {}

    failures = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1400 CONTROLLED ASSET TRANSFORMATION"
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

        scene = scenes[
            key
        ]

        source = Path(
            scene[
                "path"
            ]
        )

        strategy = scene[
            "strategy"
        ]

        output = (
            OUT_DIR
            /
            f"scene_{number:02d}.png"
        )

        work_dir = (
            WORK
            /
            f"scene_{number:02d}"
        )

        if not source.exists():

            failures.append({
                "scene":
                    number,

                "reason":
                    "source_missing",
            })

            continue

        source_sha = (
            sha256_file(
                source
            )
        )

        expected_source_sha = str(
            scene.get(
                "sha256"
            )
            or ""
        )

        if (
            source_sha
            !=
            expected_source_sha
        ):

            failures.append({
                "scene":
                    number,

                "reason":
                    "source_sha_changed",
            })

            continue

        try:

            transform(
                strategy=strategy,
                source=source,
                output=output,
                work_dir=work_dir,
                scene_number=number,
            )

            prepared_sha = (
                sha256_file(
                    output
                )
            )

            results[
                key
            ] = {
                "scene":
                    number,

                "strategy":
                    strategy,

                "source_group":
                    scene.get(
                        "source_group"
                    ),

                "source_path":
                    str(
                        source.resolve()
                    ),

                "source_sha256":
                    source_sha,

                "prepared_path":
                    str(
                        output.resolve()
                    ),

                "prepared_sha256":
                    prepared_sha,

                "prepared_bytes":
                    output.stat().st_size,

                "overlay_label":
                    scene.get(
                        "overlay_label"
                    ),

                "semantic_mode":
                    scene.get(
                        "semantic_mode"
                    ),

                "source_class":
                    scene.get(
                        "source_class"
                    ),

                "generic":
                    scene.get(
                        "generic"
                    ),

                "presentation_constraints":
                    scene.get(
                        "presentation_constraints"
                    )
                    or [],
            }

            print(
                "SCENE",
                number,
                "| PREPARED",
                "|",
                strategy,
                "|",
                output.stat().st_size,
                "bytes"
            )

        except Exception as exc:

            output.unlink(
                missing_ok=True
            )

            failures.append({
                "scene":
                    number,

                "reason":
                    (
                        type(exc).__name__
                        + ":"
                        + str(exc)
                    ),
            })

            print(
                "SCENE",
                number,
                "| HOLD |",
                type(exc).__name__,
                str(exc)[:300]
            )

    certified = (
        len(results) == 12
        and
        not failures
    )

    status = (
        "VI1400_ASSET_TRANSFORMATION_CERTIFIED"
        if certified
        else
        "VI1400_ASSET_TRANSFORMATION_HOLD"
    )

    manifest = {
        "version":
            "1400.00",

        "status":
            status,

        "scene_count":
            len(results),

        "scenes":
            results,

        "failures":
            failures,

        "production_mutation":
            False,
    }

    write_json(
        MANIFEST,
        manifest
    )

    write_json(
        REPORT,
        {
            "gate":
                {
                    "status":
                        status,

                    "scene_count":
                        len(results),

                    "failures":
                        failures,

                    "ffmpeg_executed":
                        True,

                    "production_mutated":
                        False,
                }
        }
    )

    print()
    print(
        "PREPARED SCENES:",
        len(results)
    )

    print(
        "FAILURES:",
        failures
    )

    print(
        "STATUS:",
        status
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
