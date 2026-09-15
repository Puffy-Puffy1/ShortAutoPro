#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.31"

IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

VIDEO_EXTS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
}


def media_type(path):

    suffix = Path(
        path
    ).suffix.lower()

    if suffix in IMAGE_EXTS:
        return "STILL"

    if suffix in VIDEO_EXTS:
        return "VIDEO"

    return "UNKNOWN"


def build(path):

    p = Path(path)

    return {
        "version":
            VERSION,

        "path":
            str(p),

        "name":
            p.name,

        "suffix":
            p.suffix.lower(),

        "media_type":
            media_type(p),

        "exists":
            p.exists(),

        "size_bytes":
            (
                p.stat().st_size
                if p.exists()
                else 0
            ),
    }


def self_test():

    assert (
        media_type(
            "scene_01.jpg"
        )
        == "STILL"
    )

    assert (
        media_type(
            "scene_02.mp4"
        )
        == "VIDEO"
    )

    print(
        "VI8.31 REAL MEDIA FILE MODEL=PASS"
    )


if __name__ == "__main__":
    self_test()
