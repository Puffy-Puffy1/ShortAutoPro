#!/usr/bin/env python3

import json

from pathlib import Path

from vi1510_01_common import (
    ROOT,
    in_window,
    save_json,
)


TEXT_KEYS = {
    "narration",
    "segment",
    "script",
    "roteiro",
    "headline",
    "subtitle",
    "caption",
}


def walk_text(
    value,
):
    if isinstance(
        value,
        dict
    ):

        for key, item in value.items():

            if (
                str(
                    key
                ).lower()
                in TEXT_KEYS

                and

                isinstance(
                    item,
                    str
                )
            ):
                yield item


            yield from walk_text(
                item
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:
            yield from walk_text(
                item
            )


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


    files = []


    roots = [
        ROOT
        / "roteiros",

        ROOT
        / "manifests",

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
                not in {
                    ".json",
                    ".txt",
                }
            ):
                continue


            lower = str(
                path
            ).lower()


            if any(
                value in lower

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


            fresh = in_window(
                path,
                start,
                end,
            )


            narrative_name = any(
                key
                in path.name.lower()

                for key in [
                    "roteiro",
                    "script",
                    "narr",
                    "segment",
                    "story",
                    "scene",
                    "cena",
                ]
            )


            if (
                sid_match

                or

                (
                    fresh
                    and
                    (
                        narrative_name

                        or

                        base.name
                        ==
                        "roteiros"
                    )
                )
            ):
                files.append(
                    path
                )


    texts = []


    for path in files:

        try:

            if path.suffix.lower() == ".json":

                data = json.loads(
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )

                texts.extend(
                    walk_text(
                        data
                    )
                )


            elif (
                path.parent.name
                ==
                "roteiros"

                or

                any(
                    word
                    in path.name.lower()

                    for word in [
                        "roteiro",
                        "script",
                        "narr",
                    ]
                )
            ):

                texts.append(
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )


        except Exception:
            continue


    report = {
        "files": [
            str(
                path
            )

            for path in files
        ],

        "texts":
            texts,

        "text_count":
            len(
                texts
            ),
    }


    save_json(
        run_dir
        / "narrative_scope.json",
        report
    )


    return report
