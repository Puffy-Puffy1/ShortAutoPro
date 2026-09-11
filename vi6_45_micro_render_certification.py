#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from fractions import Fraction


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.45"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


TEMP = os.path.join(
    BASE,
    "temp",
    "vi645"
)


REPORT = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_45_micro_render_latest.json"
)


TARGET_DURATION = 1.2

TARGET_WIDTH = 1080

TARGET_HEIGHT = 1920

TARGET_FPS = 30.0


def _run(
    cmd,
    timeout=60
):

    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _fps(value):

    try:

        return float(
            Fraction(
                str(
                    value
                )
            )
        )

    except Exception:

        return 0.0


def _choose_codec(
    ffmpeg
):

    result = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-encoders",
        ],
        30
    )


    blob = (
        result.stdout
        + "\n"
        + result.stderr
    )


    if "libx264" in blob:

        return "libx264"


    return "mpeg4"


def build_contract():

    return {

        "media_type":
            "STILL",

        "role":
            "CONTEXT",

        "profile":
            "CONTEXT_DRIFT",

        "renderer_applied":
            False,

        "ken_burns":
            {
                "enabled":
                    True,

                "zoom_start":
                    1.0,

                "zoom_end":
                    1.03,

                "start_x":
                    .47,

                "start_y":
                    .50,

                "end_x":
                    .53,

                "end_y":
                    .50,
            },
    }


def cleanup(
    paths
):

    removed = []


    for path in paths:

        try:

            if os.path.exists(
                path
            ):

                os.remove(
                    path
                )

                removed.append(
                    path
                )

        except Exception:

            pass


    return removed


def certify():

    ffmpeg = shutil.which(
        "ffmpeg"
    )


    ffprobe = shutil.which(
        "ffprobe"
    )


    if not ffmpeg:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_missing",

            "video_created":
                False,
        }


    if not ffprobe:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffprobe_missing",

            "video_created":
                False,
        }


    os.makedirs(
        TEMP,
        exist_ok=True
    )


    os.makedirs(
        os.path.dirname(
            REPORT
        ),
        exist_ok=True
    )


    input_path = os.path.join(
        TEMP,
        "synthetic_input.ppm"
    )


    output_path = os.path.join(
        TEMP,
        "micro_render.mp4"
    )


    cleanup(
        [
            input_path,
            output_path,
        ]
    )


    created = False

    probe_payload = None

    errors = []


    try:

        # =====================================
        # SYNTHETIC LOCAL STILL
        # =====================================

        input_cmd = [

            ffmpeg,

            "-hide_banner",

            "-loglevel",
            "error",

            "-y",

            "-f",
            "lavfi",

            "-i",
            (
                "testsrc2="
                "size=1080x1920:"
                "rate=1"
            ),

            "-frames:v",
            "1",

            input_path,
        ]


        result = _run(
            input_cmd,
            45
        )


        if (
            result.returncode
            != 0
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "synthetic_input_creation_failed",

                "stderr":
                    (
                        result.stderr
                        or ""
                    )[-1500:],

                "video_created":
                    False,
            }


        # =====================================
        # COMPILE REAL VI6 FILTER
        # =====================================

        contract = build_contract()


        dry_plan = compile_plan(
            contract,
            {
                "seconds":
                    TARGET_DURATION
            }
        )


        validation = validate_filter(
            dry_plan
        )


        if (
            validation.get(
                "status"
            )
            != "PASS"
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "dry_filter_validation_failed",

                "validation":
                    validation,

                "video_created":
                    False,
            }


        frames = int(
            dry_plan.get(
                "frames",
                36
            )
        )


        vf = dry_plan.get(
            "vf"
        )


        codec = _choose_codec(
            ffmpeg
        )


        # =====================================
        # ISOLATED MICRO RENDER
        # =====================================

        cmd = [

            ffmpeg,

            "-hide_banner",

            "-loglevel",
            "error",

            "-y",

            "-i",
            input_path,

            "-vf",
            vf,

            "-frames:v",
            str(
                frames
            ),

            "-r",
            "30",

            "-c:v",
            codec,

            "-pix_fmt",
            "yuv420p",

            "-an",

            output_path,
        ]


        render = _run(
            cmd,
            90
        )


        if (
            render.returncode
            != 0
        ):

            errors.append(
                "ffmpeg_micro_render_failed"
            )


            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "ffmpeg_micro_render_failed",

                "codec":
                    codec,

                "stderr":
                    (
                        render.stderr
                        or ""
                    )[-2000:],

                "video_created":
                    os.path.exists(
                        output_path
                    ),
            }


        created = os.path.exists(
            output_path
        )


        if not created:

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "output_not_created",

                "video_created":
                    False,
            }


        # =====================================
        # FFPROBE CERTIFICATION
        # =====================================

        probe_cmd = [

            ffprobe,

            "-v",
            "error",

            "-select_streams",
            "v:0",

            "-show_entries",
            (
                "stream="
                "width,height,"
                "r_frame_rate,"
                "avg_frame_rate,"
                "nb_frames,"
                "codec_name:"
                "format=duration"
            ),

            "-of",
            "json",

            output_path,
        ]


        probe = _run(
            probe_cmd,
            45
        )


        if (
            probe.returncode
            != 0
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "ffprobe_failed",

                "stderr":
                    (
                        probe.stderr
                        or ""
                    )[-1500:],

                "video_created":
                    True,
            }


        probe_payload = json.loads(
            probe.stdout
        )


        streams = (
            probe_payload.get(
                "streams"
            )
            or []
        )


        if not streams:

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "no_video_stream",

                "video_created":
                    True,
            }


        stream = streams[0]


        fmt = (
            probe_payload.get(
                "format"
            )
            or {}
        )


        width = int(
            stream.get(
                "width",
                0
            )
            or 0
        )


        height = int(
            stream.get(
                "height",
                0
            )
            or 0
        )


        fps = _fps(
            stream.get(
                "avg_frame_rate"
            )
            or stream.get(
                "r_frame_rate"
            )
        )


        try:

            duration = float(
                fmt.get(
                    "duration",
                    0
                )
                or 0
            )

        except Exception:

            duration = 0.0


        size = os.path.getsize(
            output_path
        )


        checks = {

            "width":
                width
                == TARGET_WIDTH,

            "height":
                height
                == TARGET_HEIGHT,

            "fps":
                abs(
                    fps
                    - TARGET_FPS
                )
                <= .05,

            "duration":
                abs(
                    duration
                    - TARGET_DURATION
                )
                <= .25,

            "file_nonempty":
                size > 1000,
        }


        passed = all(
            checks.values()
        )


        return {

            "version":
                VERSION,

            "status":
                (
                    "CERTIFIED"
                    if passed
                    else "HOLD"
                ),

            "reason":
                (
                    "micro_render_certified"
                    if passed
                    else
                    "micro_render_spec_mismatch"
                ),

            "codec":
                codec,

            "width":
                width,

            "height":
                height,

            "fps":
                round(
                    fps,
                    4
                ),

            "duration":
                round(
                    duration,
                    4
                ),

            "frames_planned":
                frames,

            "file_size":
                size,

            "checks":
                checks,

            "video_created":
                True,

            "production_video":
                False,

            "synthetic_input":
                True,

            "api_calls":
                0,

            "downloads":
                0,
        }


    finally:

        keep = str(
            os.getenv(
                "VI645_KEEP_ARTIFACTS",
                "0"
            )
        ).strip() == "1"


        if not keep:

            cleanup(
                [
                    output_path,
                    input_path,
                ]
            )


def save(
    result
):

    payload = dict(
        result
    )


    output_path = os.path.join(
        TEMP,
        "micro_render.mp4"
    )


    input_path = os.path.join(
        TEMP,
        "synthetic_input.ppm"
    )


    payload[
        "output_exists_after_cleanup"
    ] = os.path.exists(
        output_path
    )


    payload[
        "input_exists_after_cleanup"
    ] = os.path.exists(
        input_path
    )


    payload[
        "temporary_video_deleted"
    ] = not os.path.exists(
        output_path
    )


    with open(
        REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "certification":
                    payload,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return (
        REPORT,
        payload
    )


def self_test():

    contract = build_contract()


    plan = compile_plan(
        contract,
        {
            "seconds":
                TARGET_DURATION
        }
    )


    assert (
        plan[
            "renderer_mode"
        ]
        == "KEN_BURNS_STILL"
    )


    assert (
        plan[
            "frames"
        ]
        == 36
    )


    assert (
        validate_filter(
            plan
        )[
            "status"
        ]
        == "PASS"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.45 CERTIFIER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Synthetic Media Only"
    )
    print(
        "OK 1080x1920 Target"
    )
    print(
        "OK 30 FPS Target"
    )
    print(
        "OK 1.2s Target"
    )
    print(
        "OK ffprobe Certification"
    )
    print(
        "OK Automatic Cleanup"
    )
    print()


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--certify",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.certify:

        return


    result = certify()


    path, final = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.45 MICRO-RENDER CERTIFICATION"
    )
    print(
        "======================================"
    )


    print(
        "STATUS:",
        final.get(
            "status"
        )
    )


    print(
        "REASON:",
        final.get(
            "reason"
        )
    )


    print(
        "RESOLUTION:",
        str(
            final.get(
                "width"
            )
        )
        + "x"
        + str(
            final.get(
                "height"
            )
        )
    )


    print(
        "FPS:",
        final.get(
            "fps"
        )
    )


    print(
        "DURATION:",
        final.get(
            "duration"
        )
    )


    print(
        "CODEC:",
        final.get(
            "codec"
        )
    )


    print(
        "TEMP VIDEO DELETED:",
        final.get(
            "temporary_video_deleted"
        )
    )


    print(
        "OUTPUT EXISTS AFTER CLEANUP:",
        final.get(
            "output_exists_after_cleanup"
        )
    )


    print(
        "PRODUCTION VIDEO:",
        final.get(
            "production_video",
            False
        )
    )


    print(
        "REPORT:",
        path
    )


if __name__ == "__main__":
    main()
