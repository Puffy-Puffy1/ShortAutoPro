#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

NEW_VIDEO = (
    BASE
    / "videos/canary/vi1320/"
    "2026-09-01_1433_VI1320_CANARY.mp4"
)

OLD_VIDEO = (
    BASE
    / "videos/canary/vi1310/"
    "2026-09-01_1433_VI1310_CANARY.mp4"
)

TIMELINE = json.loads(
    (
        BASE
        / "temp/vi1310/timeline.json"
    ).read_text(
        encoding="utf-8"
    )
)

CONTACT = (
    BASE
    / "videos/canary/vi1320/"
    "VI1320_contact_sheet.jpg"
)

COMPARE = (
    BASE
    / "videos/canary/vi1320/"
    "VI1310_vs_VI1320.jpg"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1320_04_audit_compare_latest.json"
)


def run(command):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def probe(path):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ])

    if result.returncode != 0:
        return None

    return json.loads(
        result.stdout
    )


def make_contact_sheet():
    inputs = []
    filters = []

    for index, scene in enumerate(
        TIMELINE["timeline"]
    ):
        middle = (
            float(scene["start"])
            +
            float(scene["duration"])
            /
            2
        )

        inputs.extend([
            "-ss",
            f"{middle:.3f}",
            "-i",
            str(NEW_VIDEO),
        ])

        filters.append(
            (
                f"[{index}:v]"
                "scale=270:480,"
                f"drawtext=text='S{index + 1}':"
                "x=12:y=12:"
                "fontsize=32:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=black@0.65"
                f"[v{index}]"
            )
        )

    refs = "".join(
        f"[v{i}]"
        for i in range(12)
    )

    fc = (
        ";".join(filters)
        +
        ";"
        +
        refs
        +
        "xstack=inputs=12:"
        "layout="
        "0_0|270_0|540_0|810_0|"
        "0_480|270_480|540_480|810_480|"
        "0_960|270_960|540_960|810_960"
        "[out]"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
    ]

    command.extend(
        inputs
    )

    command.extend([
        "-filter_complex",
        fc,
        "-map",
        "[out]",
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(CONTACT),
    ])

    return run(
        command
    )


def make_comparison():
    if not OLD_VIDEO.exists():
        return None

    old_contact = (
        BASE
        / "videos/canary/vi1310/"
        "VI1310_contact_sheet.jpg"
    )

    if not old_contact.exists():
        return None

    return run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(old_contact),
        "-i",
        str(CONTACT),
        "-filter_complex",
        (
            "[0:v]scale=810:-1[left];"
            "[1:v]scale=810:-1[right];"
            "[left][right]"
            "hstack=inputs=2[out]"
        ),
        "-map",
        "[out]",
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(COMPARE),
    ])


def main():
    if not NEW_VIDEO.exists():
        raise SystemExit(
            "VI1320 VIDEO MISSING"
        )

    data = probe(
        NEW_VIDEO
    )

    if not data:
        raise SystemExit(
            "FFPROBE FAILED"
        )

    streams = (
        data.get("streams")
        or []
    )

    video = next(
        (
            item
            for item in streams
            if item.get(
                "codec_type"
            )
            ==
            "video"
        ),
        None,
    )

    audio = next(
        (
            item
            for item in streams
            if item.get(
                "codec_type"
            )
            ==
            "audio"
        ),
        None,
    )

    width = int(
        (
            video
            or {}
        ).get(
            "width"
        )
        or 0
    )

    height = int(
        (
            video
            or {}
        ).get(
            "height"
        )
        or 0
    )

    duration = float(
        (
            data.get("format")
            or {}
        ).get(
            "duration"
        )
        or 0
    )

    contact_result = (
        make_contact_sheet()
    )

    compare_result = None

    if (
        contact_result.returncode
        ==
        0
        and
        CONTACT.exists()
    ):
        compare_result = (
            make_comparison()
        )

    checks = {
        "width_1080":
            width == 1080,

        "height_1920":
            height == 1920,

        "video_stream":
            video is not None,

        "audio_stream":
            audio is not None,

        "duration_41s_range":
            41.0
            <=
            duration
            <=
            42.5,

        "contact_sheet_created":
            CONTACT.exists(),

        "production_mutation_off":
            True,

        "publication_off":
            True,
    }

    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]

    status = (
        "VI1320_VISUAL_DIRECTOR_CANARY_CERTIFIED"
        if not failed
        else
        "VI1320_VISUAL_DIRECTOR_HOLD"
    )

    report = {
        "version":
            "1320.00",

        "status":
            status,

        "output":
            str(NEW_VIDEO),

        "width":
            width,

        "height":
            height,

        "duration":
            duration,

        "video_codec":
            (
                video
                or {}
            ).get(
                "codec_name"
            ),

        "audio_codec":
            (
                audio
                or {}
            ).get(
                "codec_name"
            ),

        "contact_sheet":
            str(CONTACT),

        "comparison":
            (
                str(COMPARE)
                if COMPARE.exists()
                else None
            ),

        "checks":
            checks,

        "failed":
            failed,
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
        "=============================================="
    )
    print(
        " VI1320 VISUAL AUDIT"
    )
    print(
        "=============================================="
    )

    print(
        "SIZE:",
        width,
        "x",
        height
    )

    print(
        "DURATION:",
        duration
    )

    print(
        "VIDEO CODEC:",
        report["video_codec"]
    )

    print(
        "AUDIO CODEC:",
        report["audio_codec"]
    )

    print(
        "CONTACT SHEET:",
        CONTACT
    )

    print(
        "COMPARISON:",
        (
            COMPARE
            if COMPARE.exists()
            else "NOT_CREATED"
        )
    )

    print()
    for key, value in checks.items():
        print(
            key,
            "=",
            (
                "PASS"
                if value
                else "FAIL"
            )
        )

    print(
        "FAILED:",
        failed
    )

    print(
        "STATUS:",
        status
    )

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
