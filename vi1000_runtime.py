#!/usr/bin/env python3

import hashlib
import json
import os
import re
from pathlib import Path


VERSION = "1000.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

DEFAULT_MANIFEST = (
    BASE
    / "temp/vi1000_launch"
    / "active_manifest.json"
)

_CACHE = {
    "path": None,
    "mtime": None,
    "data": None,
}


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def enabled():
    return (
        os.getenv(
            "VI1000_MODE",
            "OFF"
        ).upper()
        == "ON"
    )


def manifest_path():
    value = os.getenv(
        "VI1000_MANIFEST"
    )

    if value:
        return Path(value)

    return DEFAULT_MANIFEST


def scene_number(value):
    if isinstance(
        value,
        int
    ):
        return value

    match = re.search(
        r"(\d+)",
        str(value or "")
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def load_manifest():
    path = manifest_path()

    if not path.exists():
        return {}

    mtime = (
        path.stat().st_mtime
    )

    if (
        _CACHE["path"]
        == str(path)
        and
        _CACHE["mtime"]
        == mtime
        and
        _CACHE["data"]
        is not None
    ):
        return _CACHE[
            "data"
        ]

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    _CACHE["path"] = str(
        path
    )

    _CACHE["mtime"] = mtime

    _CACHE["data"] = data

    return data


def scenes():
    return (
        load_manifest()
        .get(
            "scenes",
            {}
        )
    )


def describe_scene(scene):
    number = scene_number(
        scene
    )

    if number is None:
        return {}

    return (
        scenes().get(
            str(number),
            {}
        )
    )


def validate_entry(
    scene,
    entry
):
    result = {
        "scene":
            scene,

        "valid":
            True,

        "errors":
            [],
    }

    if not entry.get(
        "override_active"
    ):
        result[
            "active"
        ] = False

        return result

    result[
        "active"
    ] = True

    candidate = entry.get(
        "canary_path"
    )

    expected = entry.get(
        "expected_sha256"
    )

    if not candidate:
        result[
            "errors"
        ].append(
            "canary_path_missing"
        )

        result[
            "valid"
        ] = False

        return result

    path = Path(
        candidate
    )

    if not path.exists():
        result[
            "errors"
        ].append(
            "canary_file_missing"
        )

        result[
            "valid"
        ] = False

        return result

    actual = sha256(
        path
    )

    result[
        "actual_sha256"
    ] = actual

    if (
        expected
        and actual
        != expected
    ):
        result[
            "errors"
        ].append(
            "sha256_mismatch"
        )

        result[
            "valid"
        ] = False

    result[
        "path"
    ] = str(path)

    return result


def validate_manifest():
    data = load_manifest()

    scene_map = (
        data.get(
            "scenes",
            {}
        )
    )

    results = {}

    for key, entry in (
        scene_map.items()
    ):
        try:
            scene = int(key)

        except Exception:
            continue

        results[
            scene
        ] = validate_entry(
            scene,
            entry
        )

    invalid = {
        scene:
            result

        for scene, result
        in results.items()

        if not result[
            "valid"
        ]
    }

    active = sorted(
        scene
        for scene, result
        in results.items()
        if result.get(
            "active"
        )
    )

    return {
        "valid":
            not invalid,

        "active_scenes":
            active,

        "invalid":
            invalid,

        "results":
            results,
    }


def resolve_scene_media(
    scene,
    original_path
):
    if not enabled():
        return str(
            original_path
        )

    number = scene_number(
        scene
    )

    if number is None:
        return str(
            original_path
        )

    entry = describe_scene(
        number
    )

    if not entry.get(
        "override_active"
    ):
        return str(
            original_path
        )

    validation = (
        validate_entry(
            number,
            entry
        )
    )

    if not validation[
        "valid"
    ]:
        return str(
            original_path
        )

    return validation[
        "path"
    ]


if __name__ == "__main__":
    print(
        json.dumps(
            validate_manifest(),
            ensure_ascii=False,
            indent=2
        )
    )
