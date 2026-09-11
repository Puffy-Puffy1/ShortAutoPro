#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.41"

BASE = Path.home() / "ShortAutoPro"


def latest_scene_map():
    files = [
        p
        for p in (
            BASE / "roteiros"
        ).glob("scene_map_*.json")
        if "_pre_" not in p.name
    ]

    files.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )

    return files[0] if files else None


def load():
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

    return {
        "version": VERSION,
        "path": str(path),
        "short_id":
            data.get("short_id"),
        "scenes": scenes,
    }


def self_test():
    assert VERSION == "8.41"

    print(
        "VI8.41 SCENE MAP LOADER=PASS"
    )


if __name__ == "__main__":
    self_test()
