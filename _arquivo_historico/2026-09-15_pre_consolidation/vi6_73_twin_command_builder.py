#!/usr/bin/env python3

import json
import math
import re

from pathlib import Path


VERSION = "6.73"

BASE = Path.home() / "ShortAutoPro"


def _load(path, key):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )[key]


def _fps(vf):

    if not isinstance(vf, str):
        return None


    match = re.search(
        r"(?:^|[,:])fps="
        r"([0-9]+(?:\.[0-9]+)?)",
        vf
    )


    if not match:
        return None


    try:
        return float(
            match.group(1)
        )

    except Exception:
        return None


def _unsafe(vf):

    if not isinstance(vf, str):
        return True


    for token in (
        ";",
        "\n",
        "\r",
        "`",
        "$(",
    ):

        if token in vf:
            return True


    return False


def build():

    freeze = _load(
        (
            BASE
            / "logs/producao/"
              "vi6_71_canary_freeze_latest.json"
        ),
        "freeze"
    )


    source = _load(
        (
            BASE
            / "logs/producao/"
              "vi6_72_source_locator_latest.json"
        ),
        "source"
    )


    blockers = []


    if freeze.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "freeze_not_ready"
        )


    if source.get(
        "status"
    ) != "FOUND":

        blockers.append(
            "source_not_ready"
        )


    duration = freeze.get(
        "duration_seconds"
    )


    try:
        duration = float(
            duration
        )

    except Exception:
        duration = None


    if (
        duration is None
        or duration < .75
        or duration > 8.0
    ):

        blockers.append(
            "duration_outside_canary_bounds"
        )


    legacy_vf = freeze.get(
        "legacy_vf"
    )


    vi6_vf = freeze.get(
        "vi6_vf"
    )


    if _unsafe(legacy_vf):

        blockers.append(
            "legacy_filter_unsafe"
        )


    if _unsafe(vi6_vf):

        blockers.append(
            "vi6_filter_unsafe"
        )


    fps = (
        _fps(vi6_vf)
        or _fps(legacy_vf)
        or 30.0
    )


    frames = (
        max(
            1,
            int(
                math.ceil(
                    duration
                    * fps
                )
            )
        )
        if duration
        else None
    )


    source_path = source.get(
        "source"
    )


    output_dir = (
        BASE
        / "videos"
        / "canary"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    scene = freeze.get(
        "scene"
    )


    legacy_out = (
        output_dir
        / (
            f"scene_{scene:02d}"
            "_LEGACY_preview.mp4"
        )
    )


    vi6_out = (
        output_dir
        / (
            f"scene_{scene:02d}"
            "_VI6_preview.mp4"
        )
    )


    def command(vf, output):

        return [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            source_path,

            "-vf",
            vf,

            "-frames:v",
            str(frames),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-crf",
            "24",

            "-pix_fmt",
            "yuv420p",

            str(output),
        ]


    return {
        "version": VERSION,

        "status":
            (
                "READY"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "source":
            source_path,

        "duration_seconds":
            duration,

        "fps":
            fps,

        "frames":
            frames,

        "legacy_output":
            str(legacy_out),

        "vi6_output":
            str(vi6_out),

        "legacy_command":
            (
                command(
                    legacy_vf,
                    legacy_out
                )
                if not blockers
                else None
            ),

        "vi6_command":
            (
                command(
                    vi6_vf,
                    vi6_out
                )
                if not blockers
                else None
            ),

        "blockers":
            blockers,

        "video_py_modified":
            False,
    }


def self_test():

    assert _fps(
        "zoompan=d=90:s=1080x1920:fps=30"
    ) == 30.0


    assert _fps(
        "scale=1080:1920,fps=30"
    ) == 30.0


    print(
        "VI6.73 TWIN COMMAND BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
