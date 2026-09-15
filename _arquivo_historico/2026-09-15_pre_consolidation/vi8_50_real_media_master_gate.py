#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_40_real_media_foundation_gate import (
    evaluate as foundation
)

from vi8_41_scene_map_loader import (
    load as load_scene_map
)

from vi8_48_real_scene_ranking_plan import (
    build as build_plan
)

from vi8_49_real_media_ranking_audit import (
    evaluate as audit
)

VERSION = "8.50"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    foundation_result = (
        foundation()
    )

    scene_map = (
        load_scene_map()
    )

    grouped = (
        foundation_result.get(
            "grouped"
        )
        or {}
    )

    plan = build_plan(
        scene_map.get(
            "scenes"
        )
        or [],
        grouped
    )

    audit_result = audit(
        plan
    )

    result = {
        "version":
            VERSION,

        "status":
            (
                "REAL_MEDIA_RANKING_READY"
                if not audit_result.get(
                    "blockers"
                )
                else "HOLD"
            ),

        "short_id":
            scene_map.get(
                "short_id"
            ),

        "media_dir":
            foundation_result.get(
                "media_dir"
            ),

        "scene_map":
            scene_map.get(
                "path"
            ),

        "foundation_status":
            foundation_result.get(
                "status"
            ),

        "plan":
            plan,

        "audit":
            audit_result,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_50_real_media_master_latest.json"
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
    assert VERSION == "8.50"

    print(
        "VI8.50 REAL MEDIA MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
