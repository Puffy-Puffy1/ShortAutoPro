#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.41"


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_41_ffmpeg_probe_latest.json"
)


def sample_plan():

    contract = {

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
                    1.04,

                "start_x":
                    .46,

                "start_y":
                    .50,

                "end_x":
                    .54,

                "end_y":
                    .50,
            },
    }


    duration = {
        "seconds":
            4.0
    }


    return compile_plan(
        contract,
        duration
    )


def build_probe_command(
    dry_plan
):

    vf = str(
        dry_plan.get(
            "vf"
        )
        or ""
    )


    return [
        "ffmpeg",

        "-hide_banner",

        "-loglevel",
        "error",

        "-f",
        "lavfi",

        "-i",
        (
            "color="
            "c=black:"
            "s=1080x1920:"
            "r=30:"
            "d=0.2"
        ),

        "-vf",
        vf,

        "-frames:v",
        "1",

        "-f",
        "null",

        "-"
    ]


def probe(
    dry_plan=None
):

    if dry_plan is None:

        dry_plan = sample_plan()


    static = validate_filter(
        dry_plan
    )


    if (
        static.get(
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
                "static_filter_validation_failed",

            "static":
                static,

            "ffmpeg_found":
                bool(
                    shutil.which(
                        "ffmpeg"
                    )
                ),

            "executed":
                False,

            "output_file_created":
                False,
        }


    binary = shutil.which(
        "ffmpeg"
    )


    if not binary:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_not_found",

            "static":
                static,

            "ffmpeg_found":
                False,

            "executed":
                False,

            "output_file_created":
                False,
        }


    cmd = build_probe_command(
        dry_plan
    )


    cmd[
        0
    ] = binary


    try:

        completed = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )


        return_code = (
            completed.returncode
        )


        stderr = (
            completed.stderr
            or ""
        )[-2000:]


        stdout = (
            completed.stdout
            or ""
        )[-1000:]


        status = (
            "PASS"
            if return_code == 0
            else "HOLD"
        )


        reason = (
            "ffmpeg_filter_probe_pass"
            if return_code == 0
            else "ffmpeg_filter_probe_failed"
        )


        return {

            "version":
                VERSION,

            "status":
                status,

            "reason":
                reason,

            "ffmpeg_found":
                True,

            "ffmpeg_binary":
                binary,

            "executed":
                True,

            "execution_type":
                "NULL_OUTPUT_FILTER_PROBE",

            "return_code":
                return_code,

            "stderr_tail":
                stderr,

            "stdout_tail":
                stdout,

            "renderer_mode":
                dry_plan.get(
                    "renderer_mode"
                ),

            "filter":
                dry_plan.get(
                    "vf"
                ),

            "output_target":
                "null",

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


    except subprocess.TimeoutExpired:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_probe_timeout",

            "ffmpeg_found":
                True,

            "executed":
                True,

            "execution_type":
                "NULL_OUTPUT_FILTER_PROBE",

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


    except Exception as exc:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                (
                    "ffmpeg_probe_exception:"
                    + type(
                        exc
                    ).__name__
                ),

            "ffmpeg_found":
                True,

            "executed":
                True,

            "error":
                str(
                    exc
                )[:300],

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


def save(
    result,
    path=REPORT
):

    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "probe":
            result,
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def load_latest():

    if not os.path.exists(
        REPORT
    ):

        return None


    try:

        with open(
            REPORT,
            "r",
            encoding="utf-8"
        ) as file:

            return (
                json.load(
                    file
                ).get(
                    "probe"
                )
            )


    except Exception:

        return None


def self_test():

    plan = sample_plan()


    static = validate_filter(
        plan
    )


    assert (
        static[
            "status"
        ]
        == "PASS"
    )


    cmd = build_probe_command(
        plan
    )


    assert (
        cmd[
            0
        ]
        == "ffmpeg"
    )


    assert (
        "-vf"
        in cmd
    )


    assert (
        cmd[-2:]
        == [
            "null",
            "-"
        ]
    )


    assert (
        "{OUTPUT}"
        not in cmd
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.41 PROBE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Synthetic Lavfi Input"
    )
    print(
        "OK Real Filter String"
    )
    print(
        "OK Output = null"
    )
    print(
        "OK No MP4 Path"
    )
    print(
        "OK No User Media"
    )
    print()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--probe",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.probe:

        return


    result = probe()

    path = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.41 REAL FFMPEG NULL PROBE"
    )
    print(
        "======================================"
    )

    print(
        "STATUS:",
        result.get(
            "status"
        )
    )

    print(
        "REASON:",
        result.get(
            "reason"
        )
    )

    print(
        "FFMPEG FOUND:",
        result.get(
            "ffmpeg_found"
        )
    )

    print(
        "EXECUTED:",
        result.get(
            "executed"
        )
    )

    print(
        "OUTPUT TARGET:",
        result.get(
            "output_target",
            "null"
        )
    )

    print(
        "VIDEO FILE CREATED:",
        result.get(
            "video_file_created",
            False
        )
    )

    print(
        "REPORT:",
        path
    )


    if (
        result.get(
            "status"
        )
        != "PASS"
    ):

        stderr = result.get(
            "stderr_tail"
        )

        if stderr:

            print()
            print(
                "FFMPEG ERROR TAIL:"
            )

            print(
                stderr
            )


if __name__ == "__main__":

    main()
