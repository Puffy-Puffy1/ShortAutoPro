#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY_PATH = (
    BASE
    / "config/"
    "vi1300_asset_preparation_policy.json"
)

PLAN_PATH = (
    BASE
    / "temp/vi1290/"
    "render_readiness_plan.json"
)

OUT_ROOT = (
    BASE
    / "temp/vi1300_prepared"
)

REPORT_PATH = (
    BASE
    / "logs/producao/"
    "vi1300_00_asset_preparation_canary_latest.json"
)

PREP_PLAN = (
    BASE
    / "temp/vi1300/"
    "prepared_manifest.json"
)


def read_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(path, data):
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


def sha256_file(path):
    sha = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


def run(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    return {
        "returncode":
            result.returncode,

        "stdout":
            result.stdout,

        "stderr":
            result.stderr,
    }


def ffprobe_json(path):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "stream=index,codec_type,codec_name,"
            "width,height,duration,avg_frame_rate:"
            "format=duration,size"
        ),
        "-of",
        "json",
        str(path),
    ])

    if result["returncode"] != 0:
        return {
            "ok":
                False,

            "error":
                result["stderr"][-1000:],
        }

    try:
        payload = json.loads(
            result["stdout"]
        )

    except Exception as exc:
        return {
            "ok":
                False,

            "error":
                "json:"
                + str(exc),
        }

    return {
        "ok":
            True,

        "data":
            payload,
    }


def escape_filter_text(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )


def fullscreen_filter():
    return (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setsar=1"
    )


def insert_filter():
    return (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=30:15"
        "[bg];"

        "[0:v]"
        "scale=1000:1720:"
        "force_original_aspect_ratio=decrease"
        "[fg];"

        "[bg][fg]"
        "overlay="
        "(W-w)/2:"
        "(H-h)/2,"
        "setsar=1"
    )


def prepare_image(
    source,
    destination,
    strategy,
):
    if strategy == "FULLSCREEN_CENTER_CROP":

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            fullscreen_filter(),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(destination),
        ]

    else:

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            insert_filter(),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(destination),
        ]

    return run(command)


def prepare_video_preview(
    source,
    destination,
):
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "1",
        "-i",
        str(source),
        "-filter_complex",
        insert_filter(),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(destination),
    ]

    return run(command)


def rasterize_pdf(
    source,
    temporary_prefix,
):
    command = [
        "pdftoppm",
        "-f",
        "1",
        "-singlefile",
        "-jpeg",
        "-r",
        "160",
        str(source),
        str(temporary_prefix),
    ]

    result = run(command)

    output = Path(
        str(temporary_prefix)
        + ".jpg"
    )

    return (
        result,
        output
    )


def prepare_pdf(
    source,
    destination,
    work_prefix,
):
    raster_result, raster = rasterize_pdf(
        source,
        work_prefix,
    )

    if (
        raster_result["returncode"] != 0
        or
        not raster.exists()
    ):
        return {
            "returncode":
                (
                    raster_result[
                        "returncode"
                    ]
                    or 1
                ),

            "stdout":
                raster_result["stdout"],

            "stderr":
                raster_result["stderr"],
        }

    result = prepare_image(
        raster,
        destination,
        "DOCUMENT_PAGE_INSERT",
    )

    raster.unlink(
        missing_ok=True
    )

    return result


def main():
    policy = read_json(
        POLICY_PATH
    )

    plan = read_json(
        PLAN_PATH
    )

    if (
        plan.get("status")
        !=
        "VI1290_RENDER_READINESS_CERTIFIED"
    ):
        raise SystemExit(
            "VI1300 BLOCKED: VI1290 NOT CERTIFIED"
        )

    OUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    for old in OUT_ROOT.glob(
        "scene_*"
    ):
        if old.is_file():
            old.unlink()

    prepared = []

    failures = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1300 CONTROLLED ASSET PREPARATION CANARY"
    )
    print(
        "=============================================="
    )

    scene_plans = (
        plan.get(
            "scene_plans"
        )
        or []
    )

    for scene in scene_plans:
        number = int(
            scene["scene"]
        )

        source = Path(
            scene["path"]
        )

        destination = (
            OUT_ROOT
            /
            f"scene_{number:02d}_prepared.jpg"
        )

        kind = scene.get(
            "kind"
        )

        strategy = scene.get(
            "strategy"
        )

        print(
            "SCENE",
            number,
            "|",
            kind,
            "|",
            strategy,
        )

        if not source.exists():

            failures.append({
                "scene":
                    number,

                "reason":
                    "source_missing",
            })

            continue

        source_sha_before = (
            sha256_file(
                source
            )
        )

        source_size_before = (
            source.stat().st_size
        )

        source_probe = None

        if kind == "WEBM":

            source_probe = ffprobe_json(
                source
            )

            if not source_probe.get(
                "ok"
            ):
                failures.append({
                    "scene":
                        number,

                    "reason":
                        "webm_probe_failed",

                    "detail":
                        source_probe,
                })

                continue

            result = prepare_video_preview(
                source,
                destination,
            )

        elif kind == "PDF":

            work_prefix = (
                OUT_ROOT
                /
                f".scene_{number:02d}_pdf"
            )

            result = prepare_pdf(
                source,
                destination,
                work_prefix,
            )

        elif kind in {
            "JPEG",
            "PNG",
            "WEBP",
        }:

            result = prepare_image(
                source,
                destination,
                strategy,
            )

        else:

            failures.append({
                "scene":
                    number,

                "reason":
                    "unsupported_kind:"
                    + str(kind),
            })

            continue

        if result["returncode"] != 0:

            failures.append({
                "scene":
                    number,

                "reason":
                    "preparation_process_failed",

                "stderr":
                    result[
                        "stderr"
                    ][-1500:],
            })

            destination.unlink(
                missing_ok=True
            )

            continue

        if not destination.exists():

            failures.append({
                "scene":
                    number,

                "reason":
                    "prepared_output_missing",
            })

            continue

        source_sha_after = (
            sha256_file(
                source
            )
        )

        source_size_after = (
            source.stat().st_size
        )

        if (
            source_sha_before
            !=
            source_sha_after
            or
            source_size_before
            !=
            source_size_after
        ):

            failures.append({
                "scene":
                    number,

                "reason":
                    "source_asset_mutated",
            })

            continue

        output_probe = ffprobe_json(
            destination
        )

        if not output_probe.get(
            "ok"
        ):

            failures.append({
                "scene":
                    number,

                "reason":
                    "prepared_probe_failed",

                "detail":
                    output_probe,
            })

            continue

        streams = (
            output_probe[
                "data"
            ].get(
                "streams"
            )
            or []
        )

        video_stream = next(
            (
                item

                for item in streams

                if item.get(
                    "codec_type"
                )
                ==
                "video"
            ),
            None,
        )

        if not video_stream:

            failures.append({
                "scene":
                    number,

                "reason":
                    "prepared_video_stream_missing",
            })

            continue

        width = int(
            video_stream.get(
                "width"
            )
            or 0
        )

        height = int(
            video_stream.get(
                "height"
            )
            or 0
        )

        if (
            width != 1080
            or
            height != 1920
        ):

            failures.append({
                "scene":
                    number,

                "reason":
                    (
                        "wrong_prepared_dimensions:"
                        + str(width)
                        + "x"
                        + str(height)
                    ),
            })

            continue

        prepared_sha = (
            sha256_file(
                destination
            )
        )

        record = {
            "scene":
                number,

            "source_group":
                scene.get(
                    "source_group"
                ),

            "source_title":
                scene.get(
                    "title"
                ),

            "source_path":
                str(
                    source
                ),

            "source_sha256":
                source_sha_after,

            "kind":
                kind,

            "strategy":
                strategy,

            "semantic_mode":
                scene.get(
                    "semantic_mode"
                ),

            "overlay_label":
                scene.get(
                    "overlay_label"
                ),

            "presentation_constraints":
                scene.get(
                    "presentation_constraints"
                )
                or [],

            "prepared_path":
                str(
                    destination
                ),

            "prepared_sha256":
                prepared_sha,

            "prepared_bytes":
                destination.stat().st_size,

            "prepared_width":
                width,

            "prepared_height":
                height,

            "source_probe":
                source_probe,

            "renderer_allowed":
                False,

            "production_allowed":
                False,
        }

        prepared.append(
            record
        )

        print(
            "   PREPARED",
            width,
            "x",
            height,
            "|",
            destination.name,
            "|",
            record[
                "prepared_bytes"
            ],
            "bytes",
        )

    prepared.sort(
        key=lambda item:
            item["scene"]
    )

    scene_numbers = [
        item["scene"]
        for item in prepared
    ]

    unique_prepared_hashes = {
        item[
            "prepared_sha256"
        ]
        for item in prepared
    }

    checks = {
        "vi1290_certified":
            plan.get(
                "status"
            )
            ==
            "VI1290_RENDER_READINESS_CERTIFIED",

        "prepared_12_scenes":
            len(
                prepared
            )
            == 12,

        "scene_numbers_exact_1_to_12":
            scene_numbers
            ==
            list(
                range(
                    1,
                    13
                )
            ),

        "all_outputs_1080x1920":
            all(
                item[
                    "prepared_width"
                ]
                == 1080
                and
                item[
                    "prepared_height"
                ]
                == 1920

                for item in prepared
            ),

        "source_assets_unchanged":
            not any(
                item.get(
                    "reason"
                )
                ==
                "source_asset_mutated"

                for item in failures
            ),

        "no_network":
            policy[
                "execution"
            ][
                "network"
            ]
            is False,

        "no_downloads":
            policy[
                "execution"
            ][
                "downloads"
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

    failed_checks = [
        key

        for key, value
        in checks.items()

        if value is not True
    ]

    certified = (
        not failures
        and
        not failed_checks
    )

    status = (
        "VI1300_ASSET_PREPARATION_CANARY_CERTIFIED"

        if certified

        else
        "VI1300_ASSET_PREPARATION_CANARY_HOLD"
    )

    result = (
        "READY_FOR_FIRST_CONTROLLED_RENDER_CANARY"

        if certified

        else
        "ASSET_PREPARATION_REPAIR_REQUIRED"
    )

    output = {
        "version":
            "1300.00",

        "status":
            status,

        "result":
            result,

        "prepared":
            prepared,

        "prepared_count":
            len(
                prepared
            ),

        "unique_prepared_hashes":
            len(
                unique_prepared_hashes
            ),

        "failures":
            failures,

        "checks":
            checks,

        "failed_checks":
            failed_checks,

        "execution": {
            "network":
                False,

            "download":
                False,

            "ffprobe":
                True,

            "ffmpeg":
                True,

            "pdf_rasterization":
                True,

            "renderer":
                False,

            "video_generation":
                False,

            "production_mutation":
                False,
        },
    }

    write_json(
        PREP_PLAN,
        output
    )

    write_json(
        REPORT_PATH,
        {
            "gate":
                output
        }
    )

    print()
    print(
        "===== VI1300 SUMMARY ====="
    )

    print(
        "PREPARED:",
        len(
            prepared
        ),
        "/ 12"
    )

    print(
        "UNIQUE PREPARED HASHES:",
        len(
            unique_prepared_hashes
        )
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
        "FFPROBE EXECUTED: True"
    )
    print(
        "FFMPEG EXECUTED: True"
    )
    print(
        "FINAL VIDEO GENERATED: False"
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
        "VI1300 RESULT:",
        result
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
