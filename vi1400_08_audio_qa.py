#!/usr/bin/env python3

import json
import re

from vi1400_01_common import (
    TMP,
    load_json,
    run,
    save_json,
)


def run_audio():
    video = load_json(
        TMP
        / "artifacts.json"
    )[
        "final_video"
    ]


    rc, stdout, stderr = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        video,

        "-af",
        (
            "loudnorm="
            "I=-14:"
            "TP=-1.5:"
            "LRA=7:"
            "print_format=json"
        ),

        "-f",
        "null",
        "-",
    ],
        timeout=120,
    )


    text = (
        stderr
        +
        stdout
    )


    data = {}


    matches = re.findall(
        r'\{\s*"input_i".*?\}',
        text,
        re.S,
    )


    if matches:

        try:

            data = json.loads(
                matches[
                    -1
                ]
            )

        except Exception:

            data = {}


    rc2, stdout2, stderr2 = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        video,

        "-af",
        (
            "silencedetect="
            "noise=-42dB:"
            "d=0.8"
        ),

        "-f",
        "null",
        "-",
    ],
        timeout=120,
    )


    silence_events = len(
        re.findall(
            r"silence_start:",
            stderr2
        )
    )


    warnings = []

    blockers = []


    try:

        true_peak = float(
            data.get(
                "input_tp"
            )
        )


        if true_peak > 0.2:

            blockers.append(
                "audio_true_peak_above_safe_limit"
            )


        elif true_peak > -0.5:

            warnings.append(
                "audio_peak_close_to_zero"
            )


    except Exception:

        warnings.append(
            "loudness_measurement_partial"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "loudnorm":
            data,

        "silence_events":
            silence_events,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        TMP
        / "audio_qa.json",
        report
    )


    return report


if __name__ == "__main__":

    report = (
        run_audio()
    )


    print(
        "VI1400 AUDIO QA=",
        report[
            "status"
        ]
    )

    print(
        "LOUDNESS=",
        report[
            "loudnorm"
        ]
    )

    print(
        "SILENCE_EVENTS=",
        report[
            "silence_events"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )
