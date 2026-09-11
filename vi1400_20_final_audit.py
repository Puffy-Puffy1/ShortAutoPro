#!/usr/bin/env python3

from pathlib import Path

from vi1400_01_common import (
    TMP,
    ffprobe,
    load_json,
    save_json,
)


def get_duration(
    info,
):
    try:

        return float(
            (
                info.get(
                    "format"
                )
                or {}
            ).get(
                "duration"
            )
            or 0
        )

    except Exception:

        return 0.0


def main():
    postmaster = load_json(
        TMP
        / "postmaster.json"
    )


    gate = load_json(
        TMP
        / "release_gate.json"
    )


    blockers = []

    warnings = []


    if (
        gate.get(
            "ready"
        )

        and

        not postmaster.get(
            "rendered"
        )
    ):

        blockers.append(
            "postmaster_missing"
        )


    info = {}

    source_info = {}


    if postmaster.get(
        "rendered"
    ):

        path = Path(
            postmaster[
                "path"
            ]
        )


        if not path.exists():

            blockers.append(
                "master_file_missing"
            )


        else:

            info = ffprobe(
                path
            )


            streams = info.get(
                "streams",
                []
            )


            video_stream = next(
                (
                    stream

                    for stream in streams

                    if stream.get(
                        "codec_type"
                    )
                    ==
                    "video"
                ),
                {},
            )


            audio_stream = next(
                (
                    stream

                    for stream in streams

                    if stream.get(
                        "codec_type"
                    )
                    ==
                    "audio"
                ),
                {},
            )


            if (
                int(
                    video_stream.get(
                        "width"
                    )
                    or 0
                )
                != 1080

                or

                int(
                    video_stream.get(
                        "height"
                    )
                    or 0
                )
                != 1920
            ):

                blockers.append(
                    "master_resolution_wrong"
                )


            if not audio_stream:

                blockers.append(
                    "master_audio_missing"
                )


            source = Path(
                load_json(
                    TMP
                    / "artifacts.json"
                ).get(
                    "final_video",
                    ""
                )
            )


            if source.exists():

                source_info = ffprobe(
                    source
                )


                delta = abs(
                    get_duration(
                        info
                    )
                    -
                    get_duration(
                        source_info
                    )
                )


                if delta > 0.35:

                    blockers.append(
                        "master_duration_drift"
                    )


                elif delta > 0.12:

                    warnings.append(
                        "minor_master_duration_drift"
                    )


    status = (
        "VI1400_FINAL_RELEASE_CANDIDATE_CERTIFIED"

        if (
            gate.get(
                "ready"
            )

            and

            not blockers
        )

        else

        "VI1400_FINAL_SAFE_HOLD"
    )


    report = {
        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "master":
            postmaster,

        "probe":
            info,

        "source_probe":
            source_info,

        "publication_executed":
            False,

        "production_mutated":
            False,
    }


    save_json(
        TMP
        / "final_audit.json",
        report
    )


    print(
        "STATUS:",
        status
    )

    print(
        "BLOCKERS:",
        blockers
    )

    print(
        "WARNINGS:",
        warnings
    )

    print(
        "PUBLICATION_EXECUTED=False"
    )

    print(
        "PRODUCTION_MUTATED=False"
    )


    raise SystemExit(
        0

        if (
            status
            ==
            "VI1400_FINAL_RELEASE_CANDIDATE_CERTIFIED"
        )

        else 2
    )


if __name__ == "__main__":

    main()
