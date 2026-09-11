#!/usr/bin/env python3

import re

from pathlib import Path

from vi1510_01_common import (
    ROOT,
    in_window,
    save_json,
    sha256_file,
)


MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".webm",
    ".mp4",
    ".pdf",
}


DERIVED_WORDS = {
    "render",
    "scene_clip",
    "concat",
    "rough",
    "final",
    "output",
    "canary",
}


def infer_scene(
    path,
):
    value = str(
        path
    )


    patterns = [
        r"(?:scene|cena)[_\- ]?0*(1[0-2]|[1-9])",
        r"(?:imagem|image|media)[_\- ]?0*(1[0-2]|[1-9])",
    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            value,
            re.I,
        )

        if match:
            return int(
                match.group(
                    1
                )
            )


    return None


def is_derived(
    path,
):
    text = str(
        path
    ).lower()


    if any(
        (
            "/"
            +
            word
        )
        in text

        or

        word
        in path.name.lower()

        for word
        in DERIVED_WORDS
    ):
        return True


    if (
        "/videos/"
        in text

        or

        "/vi1330/"
        in text

        or

        "/vi1400/"
        in text

        or

        "/vi1500/"
        in text

        or

        "/vi1510/"
        in text
    ):
        return True


    return False


def collect(
    run,
    run_dir,
):
    start = float(
        run[
            "window_start"
        ]
    )

    end = float(
        run[
            "window_end"
        ]
    )

    short_id = (
        run.get(
            "short_id"
        )
        or ""
    )


    candidates = {}


    roots = [
        ROOT
        / "imagens",

        ROOT
        / "temp",
    ]


    for base in roots:

        if not base.exists():
            continue


        for path in base.rglob(
            "*"
        ):

            if (
                not path.is_file()

                or

                path.suffix.lower()
                not in MEDIA_EXTENSIONS
            ):
                continue


            text = str(
                path
            ).lower()


            if any(
                value in text

                for value in [
                    "/vi1400/",
                    "/vi1500/",
                    "/vi1510/",
                ]
            ):
                continue


            sid_match = (
                bool(
                    short_id
                )

                and

                short_id
                in str(
                    path
                )
            )


            timed = in_window(
                path,
                start,
                end,
            )


            if not (
                sid_match
                or
                timed
            ):
                continue


            # For temp/, avoid unrelated intermediate
            # files unless clearly associated with media.
            if (
                base.name
                ==
                "temp"

                and

                not sid_match
            ):

                if not any(
                    word
                    in text

                    for word in [
                        "asset",
                        "media",
                        "download",
                        "source",
                        "scene",
                        "cena",
                        "image",
                        "imagem",
                    ]
                ):
                    continue


            try:
                digest = sha256_file(
                    path
                )

            except Exception:
                continue


            candidates[
                str(
                    path.resolve()
                )
            ] = {
                "path":
                    str(
                        path.resolve()
                    ),

                "basename":
                    path.name,

                "suffix":
                    path.suffix.lower(),

                "bytes":
                    path.stat().st_size,

                "mtime":
                    path.stat().st_mtime,

                "sha256":
                    digest,

                "scene":
                    infer_scene(
                        path
                    ),

                "short_id_match":
                    sid_match,

                "derived":
                    is_derived(
                        path
                    ),
            }


    rows = list(
        candidates.values()
    )


    source_rows = [
        row

        for row in rows

        if not row[
            "derived"
        ]
    ]


    report = {
        "all_media":
            rows,

        "source_assets":
            source_rows,

        "all_count":
            len(
                rows
            ),

        "source_asset_count":
            len(
                source_rows
            ),

        "unique_source_hashes":
            len({
                row[
                    "sha256"
                ]

                for row in source_rows
            }),
    }


    save_json(
        run_dir
        / "asset_inventory.json",
        report
    )


    return report
