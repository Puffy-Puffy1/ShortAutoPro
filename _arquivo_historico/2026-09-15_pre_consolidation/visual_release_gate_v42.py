#!/usr/bin/env python3

import hashlib
import os
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def check(sid):

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )

    problems = []
    files = []


    for number in range(1, 13):

        matches = []

        for suffix in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
        ):

            p = (
                media_dir
                /
                f"scene_{number:02d}{suffix}"
            )

            if p.is_file():
                matches.append(p)


        if len(matches) != 1:

            problems.append(
                f"scene_{number:02d}"
                f"_count={len(matches)}"
            )

            continue


        p = matches[0]

        if p.stat().st_size < 20_000:

            problems.append(
                f"scene_{number:02d}"
                "_too_small"
            )


        files.append(p)


    fingerprint = hashlib.sha256()

    for p in sorted(files):

        fingerprint.update(
            p.name.encode()
        )

        fingerprint.update(
            sha(p).encode()
        )


    print(
        "MEDIA_COUNT=",
        len(files),
    )

    print(
        "INPUT_FINGERPRINT=",
        fingerprint.hexdigest(),
    )


    if problems:

        for item in problems:
            print(
                "PROBLEM=",
                item
            )

        print(
            "VISUAL_RELEASE_GATE=FAIL"
        )

        return False


    print(
        "VISUAL_RELEASE_GATE=PASS"
    )

    return True


if __name__ == "__main__":

    sid = os.getenv(
        "SHORT_ID",
        "",
    )

    if not sid:
        raise SystemExit(
            "SHORT_ID ausente"
        )

    raise SystemExit(
        0
        if check(sid)
        else 1
    )
