#!/usr/bin/env python3

import json
import shutil
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1320_visual_director_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

PLAN = json.loads(
    (
        BASE
        / "temp/vi1320/visual_plan.json"
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
    / "temp/vi1320"
)

CLIPS = (
    WORK
    / "clips"
)

OVERLAYS = (
    WORK
    / "visual_overlays.ass"
)

OUTPUT_ROOT = (
    BASE
    / "videos/canary/vi1320"
)

FINAL = (
    OUTPUT_ROOT
    / "2026-09-01_1433_VI1320_CANARY.mp4"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1320_03_render_latest.json"
)


def run(command):
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


def video_duration(path):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(path),
    ])

    if result["returncode"] != 0:
        return 0.0

    try:
        return float(
            result["stdout"].strip()
        )
    except Exception:
        return 0.0


def image_filter(
    scene,
    frames
):
    strategy = scene[
        "strategy"
    ]

    # All prepared images are already 1080x1920.
    # We now use scene-specific framing/motion.

    if strategy == "HOTEL_SIGN_DETAIL":
        return (
            "crop=760:1500:160:80,"
            "scale=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00030,1.06)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "HOTEL_FACADE":
        return (
            "zoompan="
            "z='min(zoom+0.00016,1.035)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "GRAPH_DETAIL":
        return (
            "crop=1000:1180:40:430,"
            "scale=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00020,1.035)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "WORKER_DETAIL":
        return (
            "crop=820:1320:70:430,"
            "scale=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00024,1.045)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "WATER_TANK_DETAIL":
        return (
            "crop=900:1350:90:420,"
            "scale=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00020,1.04)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "DOCUMENT_DETAIL":
        return (
            "crop=920:1320:80:150,"
            "scale=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00020,1.045)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "CCTV_PUSH":
        return (
            "zoompan="
            "z='min(zoom+0.00030,1.055)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "ELEVATOR_PUSH":
        return (
            "zoompan="
            "z='min(zoom+0.00025,1.05)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            "format=yuv420p"
        )

    if strategy == "SLOW_PAN_LEFT":
        return (
            "scale=1140:2027,"
            "crop=1080:1920:"
            "x='60*(1-t/6)':"
            "y=53,"
            "fps=30,"
            "format=yuv420p"
        )

    return (
        "zoompan="
        "z='min(zoom+0.00018,1.04)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s=1080x1920:fps=30,"
        "format=yuv420p"
    )


def render_image_scene(
    scene,
    output
):
    duration = float(
        scene["duration"]
    )

    frames = max(
        1,
        round(
            duration
            *
            30
        )
    )

    vf = image_filter(
        scene,
        frames
    )

    return run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        scene[
            "visual_input"
        ],
        "-vf",
        vf,
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        str(output),
    ])


def render_archive_scene(
    scene,
    output
):
    source = Path(
        scene[
            "visual_input"
        ]
    )

    target_duration = float(
        scene["duration"]
    )

    source_duration = video_duration(
        source
    )

    if source_duration <= 0:
        return {
            "returncode":
                1,
            "stdout":
                "",
            "stderr":
                "archive_duration_invalid",
        }

    number = int(
        scene["scene"]
    )

    if number == 1:
        offset = 0.0
    else:
        offset = min(
            8.0,
            max(
                0.0,
                source_duration
                -
                target_duration
                -
                0.5
            )
        )

    return run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-stream_loop",
        "-1",
        "-ss",
        f"{offset:.3f}",
        "-i",
        str(source),
        "-t",
        f"{target_duration:.3f}",
        "-vf",
        (
            "scale=1000:1720:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:"
            "(oh-ih)/2:"
            "black,"
            "fps=30,"
            "format=yuv420p"
        ),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        str(output),
    ])


def concat_clips(
    clips,
    output
):
    concat = (
        WORK
        / "concat.txt"
    )

    concat.write_text(
        "\n".join(
            "file '"
            +
            str(path).replace(
                "'",
                "'\\''"
            )
            +
            "'"

            for path in clips
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
        str(concat),
        "-c",
        "copy",
        str(output),
    ])


def final_mux(
    silent
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
            "subtitle"
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
        "temp/vi1320/visual_overlays.ass,"
        "subtitles="
        "temp/vi1320/"
        + subtitle_copy.name
    )

    return run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(silent),
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
        str(FINAL),
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
        "scene_*.mp4"
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

    failures = []

    clips = []

    print()
    print(
        "=============================================="
    )
    print(
        " VI1320 VISUAL DIRECTOR 2.0 RENDER"
    )
    print(
        "=============================================="
    )

    for scene in PLAN["plans"]:
        number = int(
            scene["scene"]
        )

        output = (
            CLIPS
            /
            f"scene_{number:02d}.mp4"
        )

        print(
            "SCENE",
            number,
            "|",
            scene["strategy"]
        )

        if (
            scene[
                "source_mode"
            ]
            ==
            "AUTHENTIC_CASE_VIDEO"
        ):
            result = render_archive_scene(
                scene,
                output
            )
        else:
            result = render_image_scene(
                scene,
                output
            )

        if result["returncode"] != 0:
            failures.append({
                "scene":
                    number,
                "stage":
                    "scene_render",
                "stderr":
                    result[
                        "stderr"
                    ][-1400:],
            })
            break

        if not output.exists():
            failures.append({
                "scene":
                    number,
                "stage":
                    "output_missing",
            })
            break

        clips.append(
            output
        )

    if (
        not failures
        and
        len(clips)
        ==
        12
    ):
        result = concat_clips(
            clips,
            silent
        )

        if result["returncode"] != 0:
            failures.append({
                "stage":
                    "concat",
                "stderr":
                    result[
                        "stderr"
                    ][-1400:],
            })

    if (
        not failures
        and
        silent.exists()
    ):
        result = final_mux(
            silent
        )

        if result["returncode"] != 0:
            failures.append({
                "stage":
                    "mux",
                "stderr":
                    result[
                        "stderr"
                    ][-1800:],
            })

    success = (
        not failures
        and
        FINAL.exists()
        and
        FINAL.stat().st_size
        >
        1000000
    )

    report = {
        "version":
            "1320.00",

        "status":
            (
                "VI1320_RENDER_COMPLETED"
                if success
                else
                "VI1320_RENDER_HOLD"
            ),

        "output":
            (
                str(FINAL)
                if FINAL.exists()
                else None
            ),

        "bytes":
            (
                FINAL.stat().st_size
                if FINAL.exists()
                else 0
            ),

        "scene_clips":
            len(clips),

        "failures":
            failures,

        "production_mutation":
            False,
    }

    REPORT.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "SCENE CLIPS:",
        len(clips)
    )
    print(
        "OUTPUT:",
        FINAL
    )
    print(
        "FAILURES:",
        failures
    )
    print(
        "STATUS:",
        report["status"]
    )

    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
