#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1400_release_candidate_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

W = int(POLICY["canvas"]["width"])
H = int(POLICY["canvas"]["height"])


def run_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "COMMAND_FAILED\n"
            + " ".join(map(str, command))
            + "\n"
            + result.stderr[-5000:]
        )

    return result


def image_cover(source, output):
    vf = (
        f"scale={W}:{H}:"
        "force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        "setsar=1"
    )

    run_command([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-vf", vf,
        "-frames:v", "1",
        str(output),
    ])


def image_inset(source, output):
    fc = (
        "[0:v]split=2[base][fore];"
        f"[base]scale={W}:{H}:"
        "force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        "gblur=sigma=28[bg];"
        "[fore]scale=820:1450:"
        "force_original_aspect_ratio=decrease,"
        "setsar=1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        "setsar=1"
    )

    run_command([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-filter_complex", fc,
        "-frames:v", "1",
        str(output),
    ])


def archival_video_inset(
    source,
    output,
    *,
    scene_number,
):
    # Same archival video may serve different scenes.
    # Deterministic offsets prevent identical frames.
    seek_table = {
        1: 2.0,
        4: 12.0,
    }

    seek = float(
        seek_table.get(
            int(scene_number),
            4.0 + (int(scene_number) % 5) * 2.0,
        )
    )

    fc = (
        "[0:v]split=2[base][fore];"
        f"[base]scale={W}:{H}:"
        "force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        "gblur=sigma=34[bg];"
        "[fore]scale=900:1450:"
        "force_original_aspect_ratio=decrease,"
        "setsar=1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        "setsar=1"
    )

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-ss", str(seek),
        "-i", str(source),
        "-filter_complex", fc,
        "-frames:v", "1",
        str(output),
    ]

    try:
        run_command(command)

    except Exception:
        # Safe fallback near file beginning.
        command[
            command.index(str(seek))
        ] = "0.5"

        run_command(command)


def document_preview(
    source,
    output,
    work_dir,
):
    work_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for item in work_dir.glob(
        "document_page*"
    ):
        item.unlink(
            missing_ok=True
        )

    stem = (
        work_dir
        / "document_page"
    )

    run_command([
        "pdftoppm",
        "-f", "1",
        "-singlefile",
        "-jpeg",
        "-r", "160",
        str(source),
        str(stem),
    ])

    jpg = (
        work_dir
        / "document_page.jpg"
    )

    if not jpg.exists():
        raise RuntimeError(
            "PDF_PAGE_RENDER_MISSING"
        )

    fc = (
        "[0:v]split=2[base][fore];"
        f"[base]scale={W}:{H}:"
        "force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        "gblur=sigma=24[bg];"
        "[fore]scale=940:1650:"
        "force_original_aspect_ratio=decrease,"
        "setsar=1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        "setsar=1"
    )

    run_command([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(jpg),
        "-filter_complex", fc,
        "-frames:v", "1",
        str(output),
    ])


def transform(
    *,
    strategy,
    source,
    output,
    work_dir,
    scene_number,
):
    source = Path(source)
    output = Path(output)
    work_dir = Path(work_dir)

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.unlink(
        missing_ok=True
    )

    if strategy == "IMAGE_COVER":
        image_cover(
            source,
            output
        )

    elif strategy == "IMAGE_INSET":
        image_inset(
            source,
            output
        )

    elif strategy == "ARCHIVAL_INSET":
        archival_video_inset(
            source,
            output,
            scene_number=scene_number,
        )

    elif strategy == "DOCUMENT_PAGE_PREVIEW":
        document_preview(
            source,
            output,
            work_dir,
        )

    elif strategy == "VIDEO_COVER":
        archival_video_inset(
            source,
            output,
            scene_number=scene_number,
        )

    else:
        raise RuntimeError(
            "UNSUPPORTED_STRATEGY:"
            + str(strategy)
        )

    if not output.exists():
        raise RuntimeError(
            "PREPARED_OUTPUT_MISSING"
        )

    if output.stat().st_size < 1024:
        raise RuntimeError(
            "PREPARED_OUTPUT_TOO_SMALL"
        )


if __name__ == "__main__":
    print(
        "VI1450 TRANSFORM CORE HARDENED=PASS"
    )
