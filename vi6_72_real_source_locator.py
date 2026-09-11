#!/usr/bin/env python3

import json
import re

from pathlib import Path


VERSION = "6.72"

BASE = Path.home() / "ShortAutoPro"


def _freeze():

    path = (
        BASE
        / "logs/producao/"
          "vi6_71_canary_freeze_latest.json"
    )


    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )["freeze"]


def locate():

    frozen = _freeze()

    scene = frozen.get(
        "scene"
    )


    blockers = []


    if not isinstance(scene, int):

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["scene_invalid"],
        }


    directories = sorted(
        [
            p
            for p in (
                BASE
                / "imagens"
            ).glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )


    candidates = []


    pattern = re.compile(
        rf"^scene_0*{scene}\."
        r"(jpg|jpeg|png|webp|mp4|mov|mkv)$",
        re.IGNORECASE
    )


    for directory in directories[:10]:

        for path in directory.iterdir():

            if (
                path.is_file()
                and pattern.match(
                    path.name
                )
            ):

                candidates.append(
                    path
                )


    candidates.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )


    source = (
        candidates[0]
        if candidates
        else None
    )


    if source is None:

        blockers.append(
            "source_media_not_found"
        )


    else:

        suffix = source.suffix.lower()


        if suffix not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:

            blockers.append(
                "candidate_source_not_still"
            )


    return {
        "version": VERSION,

        "status":
            (
                "FOUND"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "source":
            (
                str(source)
                if source
                else None
            ),

        "source_suffix":
            (
                source.suffix.lower()
                if source
                else None
            ),

        "candidate_count":
            len(candidates),

        "blockers":
            blockers,
    }


def self_test():

    assert (
        re.match(
            r"^scene_0*4\.",
            "scene_04.jpg"
        )
        is not None
    )

    print(
        "VI6.72 SOURCE LOCATOR=PASS"
    )


if __name__ == "__main__":

    self_test()

    print(
        json.dumps(
            locate(),
            ensure_ascii=False,
            indent=2
        )
    )
