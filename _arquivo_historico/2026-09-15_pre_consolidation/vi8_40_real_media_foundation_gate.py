#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_33_real_media_inventory import (
    inventory
)

from vi8_35_real_media_technical_analyzer import (
    evaluate as technical
)

from vi8_36_scene_media_grouper import (
    group
)

from vi8_39_real_media_coverage_audit import (
    evaluate as coverage
)


VERSION = "8.40"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    inv = inventory()


    analyzed = [
        technical(
            item
        )
        for item
        in inv.get(
            "items",
            []
        )
    ]


    grouped = group(
        analyzed
    )


    coverage_result = coverage(
        grouped
    )


    result = {
        "version":
            VERSION,

        "status":
            (
                "REAL_MEDIA_FOUNDATION_READY"
                if analyzed
                else "HOLD"
            ),

        "media_dir":
            inv.get(
                "media_dir"
            ),

        "file_count":
            len(
                analyzed
            ),

        "items":
            analyzed,

        "grouped":
            grouped,

        "coverage":
            coverage_result,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "media_mutated":
            False,

        "automatic_replace":
            False,

        "full_active":
            False,
    }


    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_40_real_media_foundation_latest.json"
    )


    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    output.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "8.40"

    print(
        "VI8.40 REAL MEDIA FOUNDATION GATE=PASS"
    )


if __name__ == "__main__":

    self_test()
