#!/usr/bin/env python3

from pathlib import Path

from vi1500_01_common import (
    save_json,
)


def run(
    start_time,
    run_dir,
):
    warnings = []

    blockers = []


    try:
        from vi1400_07_subtitle_qa import (
            run as subtitle_run,
        )


        subtitles = subtitle_run()


        best = subtitles.get(
            "best"
        )


        if best:
            path = Path(
                best.get(
                    "path",
                    ""
                )
            )


            if (
                not path.exists()

                or

                path.stat().st_mtime
                <
                start_time
                - 2
            ):
                warnings.append(
                    "subtitle_candidate_not_fresh"
                )


        else:
            warnings.append(
                "fresh_subtitle_ass_not_discovered"
            )


        blockers.extend(
            subtitles.get(
                "blockers",
                []
            )
        )


    except Exception as exc:
        subtitles = {
            "status":
                "HOLD",

            "error":
                str(
                    exc
                ),
        }

        warnings.append(
            "subtitle_bridge_failed"
        )


    try:
        from vi1400_08_audio_qa import (
            run_audio,
        )


        audio = run_audio()


        blockers.extend(
            audio.get(
                "blockers",
                []
            )
        )


        warnings.extend(
            audio.get(
                "warnings",
                []
            )
        )


    except Exception as exc:
        audio = {
            "status":
                "HOLD",

            "error":
                str(
                    exc
                ),
        }

        blockers.append(
            "audio_bridge_failed"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "subtitle":
            subtitles,

        "audio":
            audio,

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }


    save_json(
        run_dir
        / "audio_subtitle_qa.json",
        report
    )


    return report
