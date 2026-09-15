#!/usr/bin/env python3

import os
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
}


def audit(short_id):

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{short_id}"
    )


    result = {
        "short_id":
            short_id,

        "directory":
            str(media_dir),

        "exists":
            media_dir.is_dir(),

        "scene_count":
            0,

        "duplicates":
            [],

        "missing":
            [],

        "zero_byte":
            [],

        "pass":
            False,
    }


    if not media_dir.is_dir():

        return result


    for number in range(
        1,
        13,
    ):

        stem = (
            f"scene_{number:02d}"
        )


        matches = [
            path
            for path
            in media_dir.glob(
                stem + ".*"
            )
            if path.suffix.casefold()
            in VALID_EXTENSIONS
        ]


        if len(matches) == 0:

            result[
                "missing"
            ].append(
                number
            )

            continue


        if len(matches) > 1:

            result[
                "duplicates"
            ].append(
                {
                    "scene":
                        number,

                    "files":
                        [
                            str(x)
                            for x
                            in matches
                        ],
                }
            )


        valid = [
            path
            for path
            in matches
            if path.stat().st_size
            >
            0
        ]


        for path in matches:

            if (
                path.stat().st_size
                <=
                0
            ):

                result[
                    "zero_byte"
                ].append(
                    str(path)
                )


        if len(matches) == 1 and valid:

            result[
                "scene_count"
            ] += 1


    result[
        "pass"
    ] = (
        result["scene_count"] == 12
        and
        not result["duplicates"]
        and
        not result["missing"]
        and
        not result["zero_byte"]
    )


    return result


if __name__ == "__main__":

    sid = os.getenv(
        "SHORT_ID",
        "",
    ).strip()

    result = audit(
        sid
    )


    print(
        f"SHORT_ID={sid}"
    )

    print(
        f"SCENE_COUNT={result['scene_count']}"
    )

    print(
        f"MISSING={result['missing']}"
    )

    print(
        f"DUPLICATES={result['duplicates']}"
    )

    print(
        f"ZERO_BYTE={result['zero_byte']}"
    )


    if result["pass"]:

        print(
            "SCENE_MEDIA_INTEGRITY=PASS"
        )

    else:

        print(
            "SCENE_MEDIA_INTEGRITY=FAIL"
        )

        raise SystemExit(1)
