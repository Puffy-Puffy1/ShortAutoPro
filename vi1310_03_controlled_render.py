#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1310_controlled_render_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

TIMELINE_PATH = (
    BASE
    / "temp/vi1310/"
    "timeline.json"
)

WORK = (
    BASE
    / "temp/vi1310"
)

CLIPS = (
    WORK
    / "clips"
)

LABELS = (
    WORK
    / "semantic_labels.ass"
)

OUTPUT_ROOT = (
    BASE
    / "videos/canary/vi1310"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1310_03_controlled_render_latest.json"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256_file(
    path
):
    sha = hashlib.sha256()


    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024
                *
                1024
            )


            if not chunk:
                break


            sha.update(
                chunk
            )


    return sha.hexdigest()


def run(
    command
):
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


def clean_work():
    CLIPS.mkdir(
        parents=True,
        exist_ok=True
    )


    for path in CLIPS.glob(
        "scene_*.mp4"
    ):

        path.unlink(
            missing_ok=True
        )


    for name in [
        "concat.txt",
        "silent_master.mp4",
        "main_subs.ass",
        "main_subs.srt",
    ]:

        (
            WORK
            /
            name
        ).unlink(
            missing_ok=True
        )


def render_scene(
    scene,
    path,
):
    duration = float(
        scene[
            "duration"
        ]
    )


    fps = int(
        POLICY[
            "output"
        ][
            "fps"
        ]
    )


    frames = max(
        1,
        int(
            round(
                duration
                *
                fps
            )
        )
    )


    fade = min(
        float(
            POLICY[
                "timing"
            ][
                "fade_duration"
            ]
        ),
        duration
        /
        6.0,
    )


    fade_out_start = max(
        0.0,
        duration
        -
        fade
    )


    maximum_zoom = float(
        POLICY[
            "motion"
        ][
            "maximum_zoom"
        ]
    )


    increment = (
        maximum_zoom
        -
        1.0
    ) / max(
        1,
        frames
    )


    if int(
        scene[
            "scene"
        ]
    ) % 2:

        x_expr = (
            "iw/2-(iw/zoom/2)"
        )

        y_expr = (
            "ih/2-(ih/zoom/2)"
        )

    else:

        x_expr = (
            "iw/2-(iw/zoom/2)"
        )

        y_expr = (
            "ih/2-(ih/zoom/2)"
        )


    vf = (
        "zoompan="
        "z='min(zoom+"
        + f"{increment:.8f}"
        + ","
        + f"{maximum_zoom:.5f}"
        + ")':"
        "x='"
        + x_expr
        + "':"
        "y='"
        + y_expr
        + "':"
        "d="
        + str(
            frames
        )
        + ":"
        "s=1080x1920:"
        "fps="
        + str(
            fps
        )
        + ","
        "fade=t=in:"
        "st=0:"
        "d="
        + f"{fade:.3f}"
        + ","
        "fade=t=out:"
        "st="
        + f"{fade_out_start:.3f}"
        + ":"
        "d="
        + f"{fade:.3f}"
        + ","
        "format=yuv420p"
    )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        scene[
            "prepared_path"
        ],
        "-vf",
        vf,
        "-frames:v",
        str(
            frames
        ),
        "-an",
        "-c:v",
        POLICY[
            "output"
        ][
            "video_codec"
        ],
        "-preset",
        POLICY[
            "output"
        ][
            "preset"
        ],
        "-crf",
        str(
            POLICY[
                "output"
            ][
                "crf"
            ]
        ),
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(
            fps
        ),
        "-movflags",
        "+faststart",
        str(
            path
        ),
    ]


    return run(
        command
    )


def concat_clips(
    paths,
    output
):
    concat_file = (
        WORK
        / "concat.txt"
    )


    lines = []


    for path in paths:

        escaped = str(
            path
        ).replace(
            "'",
            "'\\''"
        )


        lines.append(
            "file '"
            + escaped
            + "'"
        )


    concat_file.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8"
    )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(
            concat_file
        ),
        "-c",
        "copy",
        str(
            output
        ),
    ]


    return run(
        command
    )


def copy_subtitle(
    source
):
    source = Path(
        source
    )


    suffix = source.suffix.lower()


    target = (
        WORK
        /
        (
            "main_subs"
            +
            suffix
        )
    )


    shutil.copy2(
        source,
        target
    )


    return target


def burn_and_mux(
    silent,
    audio,
    subtitle,
    output
):
    subtitle = copy_subtitle(
        subtitle
    )


    filters = []


    if LABELS.exists():
        filters.append(
            "subtitles="
            "temp/vi1310/"
            "semantic_labels.ass"
        )


    filters.append(
        "subtitles="
        "temp/vi1310/"
        + subtitle.name
    )


    vf = ",".join(
        filters
    )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(
            silent
        ),
        "-i",
        str(
            audio
        ),
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        POLICY[
            "output"
        ][
            "video_codec"
        ],
        "-preset",
        POLICY[
            "output"
        ][
            "preset"
        ],
        "-crf",
        str(
            POLICY[
                "output"
            ][
                "crf"
            ]
        ),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        POLICY[
            "output"
        ][
            "audio_codec"
        ],
        "-b:a",
        POLICY[
            "output"
        ][
            "audio_bitrate"
        ],
        "-r",
        str(
            POLICY[
                "output"
        ][
            "fps"
        ]
        ),
        "-shortest",
        "-movflags",
        "+faststart",
        str(
            output
        ),
    ]


    return run(
        command
    )


def main():
    timeline = read_json(
        TIMELINE_PATH
    )


    clean_work()


    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


    sid = timeline[
        "sid"
    ]


    final = (
        OUTPUT_ROOT
        /
        (
            sid
            +
            "_VI1310_CANARY.mp4"
        )
    )


    silent = (
        WORK
        /
        "silent_master.mp4"
    )


    final.unlink(
        missing_ok=True
    )


    clip_paths = []

    failures = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1310 FIRST FULL CONTROLLED RENDER CANARY"
    )

    print(
        "=============================================="
    )


    for scene in (
        timeline[
            "timeline"
        ]
    ):

        number = int(
            scene[
                "scene"
            ]
        )


        clip = (
            CLIPS
            /
            f"scene_{number:02d}.mp4"
        )


        print(
            "SCENE",
            number,
            "|",
            f"{scene['duration']:.2f}s",
            "|",
            Path(
                scene[
                    "prepared_path"
                ]
            ).name
        )


        result = render_scene(
            scene,
            clip
        )


        if result[
            "returncode"
        ] != 0:

            failures.append({
                "scene":
                    number,

                "stage":
                    "scene_render",

                "stderr":
                    result[
                        "stderr"
                    ][-1200:],
            })

            break


        if not clip.exists():

            failures.append({
                "scene":
                    number,

                "stage":
                    "scene_output_missing",
            })

            break


        clip_paths.append(
            clip
        )


    if (
        not failures
        and
        len(
            clip_paths
        )
        == 12
    ):

        result = concat_clips(
            clip_paths,
            silent
        )


        if result[
            "returncode"
        ] != 0:

            failures.append({
                "stage":
                    "concat",

                "stderr":
                    result[
                        "stderr"
                    ][-1200:],
            })


    if (
        not failures
        and
        silent.exists()
    ):

        result = burn_and_mux(
            silent,
            timeline[
                "audio"
            ],
            timeline[
                "subtitle"
            ],
            final,
        )


        if result[
            "returncode"
        ] != 0:

            failures.append({
                "stage":
                    "final_mux_subtitle",

                "stderr":
                    result[
                        "stderr"
                    ][-1600:],
            })


    certified = (
        not failures
        and
        final.exists()
        and
        final.stat().st_size
        >
        100000
    )


    output = {
        "version":
            "1310.00",

        "status":
            (
                "VI1310_RENDER_COMPLETED"

                if certified

                else
                "VI1310_RENDER_HOLD"
            ),

        "sid":
            sid,

        "output":
            (
                str(
                    final
                )
                if final.exists()
                else None
            ),

        "output_bytes":
            (
                final.stat().st_size
                if final.exists()
                else 0
            ),

        "output_sha256":
            (
                sha256_file(
                    final
                )
                if final.exists()
                else None
            ),

        "scene_clips":
            [
                str(
                    path
                )

                for path in clip_paths
            ],

        "failures":
            failures,

        "network":
            False,

        "downloads":
            False,

        "video_py_renderer":
            False,

        "production_mutation":
            False,

        "publication":
            False,
    }


    REPORT.write_text(
        json.dumps(
            {
                "gate":
                    output
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "===== VI1310 RENDER SUMMARY ====="
    )

    print(
        "SCENE CLIPS:",
        len(
            clip_paths
        )
    )

    print(
        "FINAL:",
        final
    )

    print(
        "FINAL BYTES:",
        output[
            "output_bytes"
        ]
    )

    print(
        "FAILURES:",
        failures
    )

    print(
        "STATUS:",
        output[
            "status"
        ]
    )


    if not certified:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
