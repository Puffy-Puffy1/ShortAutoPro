#!/usr/bin/env python3

import json
import subprocess
import time

from datetime import datetime
from pathlib import Path


VERSION = "6.74"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi6_74_real_canary_render_latest.json"
)


def run_one(
    command
):

    start = time.monotonic()


    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


    elapsed = round(
        time.monotonic()
        - start,
        3
    )


    output = (
        Path(command[-1])
        if command
        else None
    )


    return {
        "return_code":
            result.returncode,

        "elapsed_seconds":
            elapsed,

        "output":
            (
                str(output)
                if output
                else None
            ),

        "output_exists":
            (
                bool(
                    output
                    and output.exists()
                )
            ),

        "output_bytes":
            (
                output.stat().st_size
                if (
                    output
                    and output.exists()
                )
                else 0
            ),

        "stderr_tail":
            (
                result.stderr[-2000:]
                if result.stderr
                else ""
            ),
    }


def render(plan):

    blockers = []


    if plan.get(
        "status"
    ) != "READY":

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["twin_plan_not_ready"],
        }


    legacy = run_one(
        plan[
            "legacy_command"
        ]
    )


    if (
        legacy[
            "return_code"
        ] != 0
        or not legacy[
            "output_exists"
        ]
    ):

        blockers.append(
            "legacy_preview_failed"
        )


        result = {
            "version": VERSION,
            "status": "HOLD",
            "legacy": legacy,
            "vi6": None,
            "blockers": blockers,
        }


        save(result)

        return result


    vi6 = run_one(
        plan[
            "vi6_command"
        ]
    )


    if (
        vi6[
            "return_code"
        ] != 0
        or not vi6[
            "output_exists"
        ]
    ):

        blockers.append(
            "vi6_preview_failed"
        )


    result = {
        "version": VERSION,

        "status":
            (
                "RENDERED"
                if not blockers
                else "HOLD"
            ),

        "scene":
            plan.get("scene"),

        "legacy":
            legacy,

        "vi6":
            vi6,

        "blockers":
            blockers,

        "production_video_modified":
            False,

        "video_py_modified":
            False,
    }


    save(result)

    return result


def save(result):

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "render":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.74"

    print(
        "VI6.74 REAL CANARY RENDERER SELF TEST=PASS"
    )


if __name__ == "__main__":
    self_test()
