#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_18_media_selection_plan import (
    build
)

from vi8_19_selection_audit import (
    evaluate as audit
)

VERSION = "8.20"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

def latest_scene_map():
    files = [
        path
        for path in (
            BASE
            / "roteiros"
        ).glob(
            "scene_map_*.json"
        )
        if "_pre_" not in path.name
    ]

    files.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return (
        files[0]
        if files
        else None
    )

def evaluate():
    path = latest_scene_map()

    if not path:
        raise RuntimeError(
            "scene_map_missing"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        data.get("scenes")
        or []
    )

    if len(scenes) != 12:
        raise RuntimeError(
            "scene_count_not_12"
        )

    plan = build(
        scenes
    )

    audit_result = audit(
        plan
    )

    return {
        "version":
            VERSION,

        "status":
            audit_result[
                "status"
            ],

        "short_id":
            data.get(
                "short_id"
            ),

        "scene_map":
            str(path),

        "plan":
            plan,

        "audit":
            audit_result,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "renderer_activation":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

def self_test():
    assert VERSION == "8.20"

    print(
        "VI8.20 MEDIA SELECTION SHADOW GATE=PASS"
    )

if __name__ == "__main__":
    self_test()
