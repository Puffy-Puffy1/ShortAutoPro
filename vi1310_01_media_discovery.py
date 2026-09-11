#!/usr/bin/env python3

import json
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

SID = POLICY[
    "short"
][
    "sid"
]

OUT = (
    BASE
    / "temp/vi1310/"
    "discovery.json"
)


AUDIO_EXTS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
}

SUB_EXTS = {
    ".ass",
    ".srt",
}


def ignored(
    path
):
    value = str(
        path
    ).lower()

    return any(
        token in value

        for token in [
            "/backups/",
            "/backup_",
            "/videos/canary/vi1310/",
            "/temp/vi1310/",
        ]
    )


def files_matching(
    extensions
):
    output = []


    for path in BASE.rglob(
        "*"
    ):

        if (
            not path.is_file()
            or
            path.suffix.lower()
            not in extensions
            or
            ignored(
                path
            )
        ):
            continue


        output.append(
            path
        )


    return output


def audio_score(
    path
):
    name = path.name.lower()

    score = 0


    if SID.lower() in name:
        score += 100


    if path.stem.lower() == SID.lower():
        score += 80


    value = str(
        path
    ).lower()


    if "/audios/" in value:
        score += 30


    if "final" in name:
        score += 10


    if "narr" in name:
        score += 5


    try:
        score += min(
            int(
                path.stat().st_size
                /
                100000
            ),
            20
        )

    except Exception:
        pass


    return score


def subtitle_score(
    path
):
    name = path.name.lower()

    score = 0


    if SID.lower() in name:
        score += 100


    if path.stem.lower() == SID.lower():
        score += 80


    if path.suffix.lower() == ".ass":
        score += 25


    value = str(
        path
    ).lower()


    if (
        "/legendas/"
        in value
        or
        "subtitle"
        in value
        or
        "legenda"
        in value
    ):
        score += 20


    try:
        score += min(
            int(
                path.stat().st_size
                /
                2000
            ),
            15
        )

    except Exception:
        pass


    return score


def choose(
    values,
    scorer
):
    if not values:
        return None


    ranked = sorted(
        values,
        key=lambda p:
            (
                scorer(
                    p
                ),
                p.stat().st_mtime,
            ),
        reverse=True,
    )


    return ranked[
        0
    ]


def ffprobe_duration(
    path
):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(
            path
        ),
    ]


    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


    if result.returncode != 0:
        return None


    try:
        return float(
            result.stdout.strip()
        )

    except Exception:
        return None


def blueprint_segments():
    candidates = [
        (
            BASE
            / "temp/vi1000_launch/"
            "launch_blueprint.json"
        ),

        (
            BASE
            / "temp/vi1250/"
            "selection_plan.json"
        ),
    ]


    for path in candidates:

        if not path.exists():
            continue


        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            continue


        scenes = data.get(
            "scenes"
        )


        if (
            isinstance(
                scenes,
                list
            )
            and
            len(
                scenes
            )
            == 12
        ):

            segments = [
                str(
                    item.get(
                        "segment"
                    )
                    or ""
                )

                for item in scenes
            ]


            if any(
                segments
            ):
                return segments


    return [
        ""
        for _ in range(
            12
        )
    ]


def main():
    audios = files_matching(
        AUDIO_EXTS
    )

    subtitles = files_matching(
        SUB_EXTS
    )


    audio = choose(
        audios,
        audio_score
    )

    subtitle = choose(
        subtitles,
        subtitle_score
    )


    duration = (
        ffprobe_duration(
            audio
        )
        if audio
        else None
    )


    segments = blueprint_segments()


    checks = {
        "audio_found":
            audio is not None,

        "audio_duration_valid":
            (
                duration is not None
                and
                duration > 5
            ),

        "subtitle_found":
            subtitle is not None,

        "twelve_segments":
            len(
                segments
            )
            == 12,
    }


    failed = [
        key

        for key, value in (
            checks.items()
        )

        if value is not True
    ]


    output = {
        "version":
            "1310.00",

        "sid":
            SID,

        "audio":
            (
                str(
                    audio
                )
                if audio
                else None
            ),

        "audio_duration":
            duration,

        "subtitle":
            (
                str(
                    subtitle
                )
                if subtitle
                else None
            ),

        "subtitle_format":
            (
                subtitle.suffix.lower()
                if subtitle
                else None
            ),

        "segments":
            segments,

        "checks":
            checks,

        "failed":
            failed,
    }


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUT.write_text(
        json.dumps(
            output,
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
        " VI1310 MEDIA DISCOVERY"
    )

    print(
        "=============================================="
    )

    print(
        "SID:",
        SID
    )

    print(
        "AUDIO:",
        audio
    )

    print(
        "AUDIO DURATION:",
        duration
    )

    print(
        "SUBTITLE:",
        subtitle
    )

    print(
        "SUBTITLE FORMAT:",
        (
            subtitle.suffix.lower()
            if subtitle
            else None
        )
    )


    print()
    print(
        "===== CHECKS ====="
    )


    for key, value in (
        checks.items()
    ):

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


    if failed:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
