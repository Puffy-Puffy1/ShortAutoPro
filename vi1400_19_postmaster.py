#!/usr/bin/env python3

from pathlib import Path

from vi1400_01_common import (
    OUT,
    TMP,
    load_json,
    policy,
    run,
    save_json,
    sha256_file,
)


def build_filter():
    config = policy()


    target = float(
        config.get(
            "audio_target_lufs",
            -14.0
        )
    )


    peak = float(
        config.get(
            "audio_true_peak",
            -1.5
        )
    )


    data = (
        load_json(
            TMP
            / "audio_qa.json"
        ).get(
            "loudnorm"
        )
        or {}
    )


    keys = [
        "input_i",
        "input_lra",
        "input_tp",
        "input_thresh",
        "target_offset",
    ]


    if all(
        data.get(
            key
        )
        not in {
            None,
            "",
        }

        for key
        in keys
    ):

        return (
            f"loudnorm="
            f"I={target}:"
            f"TP={peak}:"
            f"LRA=7:"
            f"measured_I={data['input_i']}:"
            f"measured_LRA={data['input_lra']}:"
            f"measured_TP={data['input_tp']}:"
            f"measured_thresh={data['input_thresh']}:"
            f"offset={data['target_offset']}:"
            f"linear=true:"
            f"print_format=summary"
        )


    return (
        f"loudnorm="
        f"I={target}:"
        f"TP={peak}:"
        f"LRA=7"
    )


def main():
    gate = load_json(
        TMP
        / "release_gate.json"
    )


    if not gate.get(
        "ready"
    ):

        save_json(
            TMP
            / "postmaster.json",
            {
                "status":
                    "SKIPPED_BY_RELEASE_GATE",

                "rendered":
                    False,
            }
        )


        print(
            "VI1400 POSTMASTER=SKIPPED_BY_RELEASE_GATE"
        )

        return


    source = Path(
        load_json(
            TMP
            / "artifacts.json"
        )[
            "final_video"
        ]
    )


    output = (
        OUT
        /
        (
            source.stem.replace(
                "_VI1330_CANARY",
                ""
            )
            +
            "_VI1400_FINAL_MASTER.mp4"
        )
    )


    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",

        "-i",
        str(
            source
        ),

        "-map",
        "0:v:0",

        "-map",
        "0:a:0",

        "-c:v",
        "copy",

        "-af",
        build_filter(),

        "-c:a",
        "aac",

        "-b:a",
        "160k",

        "-ar",
        "48000",

        "-movflags",
        "+faststart",

        str(
            output
        ),
    ]


    rc, stdout, stderr = run(
        cmd,
        timeout=240,
    )


    if rc != 0:

        save_json(
            TMP
            / "postmaster.json",
            {
                "status":
                    "HOLD",

                "rendered":
                    False,

                "error":
                    stderr[
                        -1200:
                    ],
            }
        )


        print(
            "VI1400 POSTMASTER=HOLD"
        )


        raise SystemExit(
            1
        )


    config = policy()


    data = {
        "status":
            "VI1400_POSTMASTER_COMPLETED",

        "rendered":
            True,

        "path":
            str(
                output
            ),

        "bytes":
            output.stat().st_size,

        "sha256":
            sha256_file(
                output
            ),

        "video_reencoded":
            False,

        "audio_mastered":
            True,

        "target_lufs":
            float(
                config.get(
                    "audio_target_lufs",
                    -14
                )
            ),

        "target_true_peak":
            float(
                config.get(
                    "audio_true_peak",
                    -1.5
                )
            ),

        "production_mutated":
            False,

        "publication_executed":
            False,
    }


    save_json(
        TMP
        / "postmaster.json",
        data
    )


    print(
        "VI1400 POSTMASTER=COMPLETED"
    )

    print(
        "FINAL=",
        output
    )

    print(
        "BYTES=",
        data[
            "bytes"
        ]
    )

    print(
        "VIDEO_REENCODED=False"
    )

    print(
        "AUDIO_MASTERED=True"
    )


if __name__ == "__main__":

    main()
