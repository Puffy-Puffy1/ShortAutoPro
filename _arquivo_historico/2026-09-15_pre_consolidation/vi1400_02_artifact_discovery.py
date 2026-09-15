#!/usr/bin/env python3

import os
import re

from pathlib import Path

from vi1400_01_common import (
    ROOT,
    TMP,
    newest,
    save_json,
)


def discover():
    override = (
        os.environ.get(
            "VI1400_INPUT_VIDEO",
            ""
        )
        .strip()
    )


    final = (
        Path(
            override
        ).expanduser()

        if override

        else None
    )


    if (
        final
        and
        not final.is_absolute()
    ):
        final = (
            ROOT
            / final
        )


    if (
        not final
        or
        not final.exists()
    ):

        candidates = list(
            (
                ROOT
                / "videos"
                / "canary"
                / "vi1330"
            ).glob(
                "*VI1330_CANARY*.mp4"
            )
        )


        if not candidates:

            candidates = [
                path

                for path in (
                    ROOT
                    / "videos"
                    / "canary"
                ).rglob(
                    "*.mp4"
                )

                if (
                    "VI1400_FINAL_MASTER"
                    not in path.name
                )
            ]


        final = newest(
            candidates
        )


    if not final:

        raise RuntimeError(
            "INPUT_CANARY_NOT_FOUND"
        )


    scene_clips = []


    search_roots = [
        ROOT
        / "temp"
        / "vi1330",

        ROOT
        / "videos"
        / "canary"
        / "vi1330",

        final.parent,
    ]


    for base in search_roots:

        if not base.exists():
            continue


        for path in base.rglob(
            "*.mp4"
        ):

            if (
                path.resolve()
                ==
                final.resolve()
            ):
                continue


            match = re.search(
                r"(?:scene|cena)[_\- ]?0*([1-9]|1[0-2])",
                path.name,
                re.I,
            )


            if match:

                scene_clips.append((
                    int(
                        match.group(
                            1
                        )
                    ),
                    path,
                ))


    dedup = {}


    for number, path in scene_clips:

        dedup.setdefault(
            number,
            path
        )


    selection_override = (
        os.environ.get(
            "VI1400_SELECTION_PLAN",
            ""
        )
        .strip()
    )


    selection = (
        Path(
            selection_override
        ).expanduser()

        if selection_override

        else
        ROOT
        / "temp"
        / "vi1260_1"
        / "selection_plan.json"
    )


    if (
        selection_override
        and
        not selection.is_absolute()
    ):
        selection = (
            ROOT
            / selection
        )


    download_manifest = (
        ROOT
        / "temp"
        / "vi1270_downloads"
        / "download_manifest.json"
    )


    overlay = (
        ROOT
        / "temp"
        / "vi1330"
        / "publication_overlays.ass"
    )


    ass_files = []


    for base in [
        ROOT
        / "temp"
        / "vi1330",

        ROOT
        / "temp",

        ROOT
        / "roteiros",
    ]:

        if base.exists():

            ass_files.extend(
                base.rglob(
                    "*.ass"
                )
            )


    ass_files = sorted(
        set(
            ass_files
        ),
        key=lambda path:
            path.stat().st_mtime,
        reverse=True,
    )


    data = {
        "final_video":
            str(
                final
            ),

        "scene_clips": {
            str(
                key
            ):
                str(
                    value
                )

            for key, value
            in sorted(
                dedup.items()
            )
        },

        "selection_plan":
            (
                str(
                    selection
                )
                if selection.exists()
                else None
            ),

        "download_manifest":
            (
                str(
                    download_manifest
                )
                if download_manifest.exists()
                else None
            ),

        "publication_overlays":
            (
                str(
                    overlay
                )
                if overlay.exists()
                else None
            ),

        "ass_candidates": [
            str(
                path
            )

            for path
            in ass_files[:20]
        ],

        "input_override_used":
            bool(
                override
            ),
    }


    save_json(
        TMP
        / "artifacts.json",
        data
    )


    return data


if __name__ == "__main__":

    data = discover()


    print(
        "VI1400 ARTIFACT DISCOVERY=PASS"
    )

    print(
        "FINAL=",
        data[
            "final_video"
        ]
    )

    print(
        "SCENE_CLIPS=",
        len(
            data[
                "scene_clips"
            ]
        )
    )

    print(
        "OVERRIDE=",
        data[
            "input_override_used"
        ]
    )
