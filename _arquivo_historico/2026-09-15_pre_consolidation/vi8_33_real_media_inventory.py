#!/usr/bin/env python3

from pathlib import Path

from vi8_31_real_media_file import (
    build
)

from vi8_32_scene_number_extractor import (
    extract
)

VERSION = "8.33"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def latest_media_dir():

    root = (
        BASE
        / "imagens"
    )

    dirs = [
        path
        for path in root.glob(
            "short_*"
        )
        if path.is_dir()
    ]

    dirs.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return (
        dirs[0]
        if dirs
        else None
    )


def inventory(
    media_dir=None
):

    folder = (
        Path(media_dir)
        if media_dir
        else latest_media_dir()
    )

    if (
        folder is None
        or not folder.exists()
    ):

        raise RuntimeError(
            "media_directory_missing"
        )

    items = []

    for path in sorted(
        folder.iterdir()
    ):

        if not path.is_file():
            continue

        item = build(
            path
        )

        if (
            item[
                "media_type"
            ]
            == "UNKNOWN"
        ):
            continue

        item[
            "scene_guess"
        ] = extract(
            path.name
        )

        items.append(
            item
        )

    return {
        "version":
            VERSION,

        "media_dir":
            str(folder),

        "count":
            len(items),

        "items":
            items,
    }


def self_test():

    assert VERSION == "8.33"

    print(
        "VI8.33 REAL MEDIA INVENTORY=PASS"
    )


if __name__ == "__main__":
    self_test()
