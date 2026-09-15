#!/usr/bin/env python3

import json
import shutil
import subprocess
from pathlib import Path


from vi1330_06_scene_renderer import (
    render_scene,
)


BASE = Path.home() / "ShortAutoPro"

PLAN = json.loads(
    (
        BASE
        / "temp/vi1330/publication_visual_plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

DISCOVERY = json.loads(
    (
        BASE
        / "temp/vi1310/discovery.json"
    ).read_text(
        encoding="utf-8"
    )
)

WORK = (
    BASE
    / "temp/vi1330"
)

CLIPS = (
    WORK
    / "clips"
)

OUTPUT_ROOT = (
    BASE
    / "videos/canary/vi1330"
)

FINAL = (
    OUTPUT_ROOT
    / "2026-09-01_1433_VI1330_CANARY.mp4"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1330_07_publication_render_latest.json"
)


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


def concat(
    clips,
    destination,
):
    path = (
        WORK
        / "concat.txt"
    )


    path.write_text(
        "\n".join(
            (
                "file '"
                +
                str(
                    clip
                ).replace(
                    "'",
                    "'\\''"
                )
                +
                "'"
            )

            for clip in clips
        )
        + "\n",
        encoding="utf-8"
    )


    return run([
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
            path
        ),
        "-c",
        "copy",
        str(
            destination
        ),
    ])


def final_mux(
    silent,
):
    subtitle_source = Path(
        DISCOVERY[
            "subtitle"
        ]
    )


    subtitle_copy = (
        WORK
        /
        (
            "main_subtitle"
            +
            subtitle_source.suffix.lower()
        )
    )


    shutil.copy2(
        subtitle_source,
        subtitle_copy
    )


    vf = (
        "subtitles="
        "temp/vi1330/publication_overlays.ass,"
        "subtitles="
        "temp/vi1330/"
        + subtitle_copy.name
    )


    return run([
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
        DISCOVERY[
            "audio"
        ],
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-r",
        "30",
        "-shortest",
        "-movflags",
        "+faststart",
        str(
            FINAL
        ),
    ])


def main():
    CLIPS.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


    for path in CLIPS.glob(
        "*.mp4"
    ):

        path.unlink(
            missing_ok=True
        )


    FINAL.unlink(
        missing_ok=True
    )


    silent = (
        WORK
        / "silent_master.mp4"
    )


    silent.unlink(
        missing_ok=True
    )


    clips = []

    failures = []


    print()
    print(
        "=============================================="
    )
    print(
        " VI1330 PUBLICATION QUALITY RENDER"
    )
    print(
        "=============================================="
    )


    for scene in PLAN[
        "plans"
    ]:

        number = int(
            scene[
                "scene"
            ]
        )


        destination = (
            CLIPS
            /
            f"scene_{number:02d}.mp4"
        )


        print(
            "SCENE",
            number,
            "|",
            scene[
                "strategy"
            ]
        )


        result = render_scene(
            scene,
            destination
        )


        if result[
            "returncode"
        ] != 0:

            failures.append({
                "scene":
                    number,

                "stage":
                    "render",

                "stderr":
                    result[
                        "stderr"
                    ][-1600:],
            })

            break


        if not destination.exists():

            failures.append({
                "scene":
                    number,

                "stage":
                    "output_missing",
            })

            break


        clips.append(
            destination
        )


    if (
        not failures
        and
        len(
            clips
        )
        == 12
    ):

        result = concat(
            clips,
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
                    ][-1600:],
            })


    if (
        not failures
        and
        silent.exists()
    ):

        result = final_mux(
            silent
        )


        if result[
            "returncode"
        ] != 0:

            failures.append({
                "stage":
                    "final_mux",

                "stderr":
                    result[
                        "stderr"
                    ][-2000:],
            })


    success = (
        not failures
        and
        FINAL.exists()
        and
        FINAL.stat().st_size
        >
        3000000
    )


    output = {
        "version":
            "1330.00",

        "status":
            (
                "VI1330_RENDER_COMPLETED"

                if success

                else
                "VI1330_RENDER_HOLD"
            ),

        "scene_clips":
            len(
                clips
            ),

        "output":
            (
                str(
                    FINAL
                )
                if FINAL.exists()
                else None
            ),

        "bytes":
            (
                FINAL.stat().st_size
                if FINAL.exists()
                else 0
            ),

        "failures":
            failures,
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
        "SCENE CLIPS:",
        len(
            clips
        )
    )
    print(
        "FINAL:",
        FINAL
    )
    print(
        "FINAL BYTES:",
        output[
            "bytes"
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


    if not success:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
