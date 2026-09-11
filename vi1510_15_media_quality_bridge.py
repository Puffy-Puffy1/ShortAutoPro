#!/usr/bin/env python3

from vi1510_01_common import (
    load_json,
    save_json,
)


def run(
    video,
    old_run_dir,
    run_dir,
):
    old_audio = load_json(
        old_run_dir
        / "audio_subtitle_qa.json",
        {}
    )


    old_temporal = load_json(
        old_run_dir
        / "temporal_qa.json",
        {}
    )


    audio = old_audio

    temporal = old_temporal


    if not audio:

        audio = {
            "status":
                "HOLD",

            "warnings":
                [],

            "blockers": [
                "audio_subtitle_qa_missing"
            ],
        }


    if not temporal:

        try:

            from vi1500_13_temporal_guard import (
                run as temporal_run,
            )


            temporal = temporal_run(
                video,
                run_dir,
            )


        except Exception as exc:

            temporal = {
                "status":
                    "HOLD",

                "warnings":
                    [],

                "blockers": [
                    "temporal_qa_missing"
                ],

                "error":
                    str(
                        exc
                    ),
            }


    report = {
        "audio_subtitle":
            audio,

        "temporal":
            temporal,

        "status":
            (
                "PASS"

                if (
                    audio.get(
                        "status"
                    )
                    == "PASS"

                    and

                    temporal.get(
                        "status"
                    )
                    == "PASS"
                )

                else "HOLD"
            ),

        "blockers":
            sorted(
                set(
                    (
                        audio.get(
                            "blockers"
                        )
                        or []
                    )
                    +
                    (
                        temporal.get(
                            "blockers"
                        )
                        or []
                    )
                )
            ),
    }


    save_json(
        run_dir
        / "media_quality.json",
        report
    )


    return report
