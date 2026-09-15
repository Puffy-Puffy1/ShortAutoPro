#!/usr/bin/env python3

import hashlib
import json
import os
import re
from pathlib import Path


_DEFAULT_MANIFEST = (
    Path.home()
    / "ShortAutoPro"
    / "temp/vi700_canary/portfolio_manifest.json"
)

_CACHE = {
    "path": None,
    "mtime": None,
    "data": None,
}


def _sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def _scene_number(value):
    if isinstance(value, int):
        return value

    match = re.search(
        r"(\d+)",
        str(value or "")
    )

    if not match:
        return None

    return int(match.group(1))


def canary_enabled():
    return (
        os.environ.get(
            "VI700_PORTFOLIO_CANARY",
            "OFF"
        ).upper()
        == "ON"
    )


def _manifest_path():
    override = os.environ.get(
        "VI700_PORTFOLIO_MANIFEST"
    )

    if override:
        return Path(override)

    return _DEFAULT_MANIFEST


def load_manifest():
    path = _manifest_path()

    if not path.exists():
        return {}

    mtime = path.stat().st_mtime

    if (
        _CACHE["path"] == str(path)
        and _CACHE["mtime"] == mtime
        and _CACHE["data"] is not None
    ):
        return _CACHE["data"]

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    _CACHE["path"] = str(path)
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data

    return data


def resolve_scene_media(
    scene,
    original_path
):
    if not canary_enabled():
        return str(original_path)

    number = _scene_number(scene)

    if number is None:
        return str(original_path)

    manifest = load_manifest()

    scenes = (
        manifest.get("scenes")
        or {}
    )

    entry = (
        scenes.get(str(number))
        or {}
    )

    if not entry.get(
        "override_active"
    ):
        return str(original_path)

    candidate = entry.get(
        "canary_path"
    )

    expected = entry.get(
        "expected_sha256"
    )

    if not candidate:
        return str(original_path)

    path = Path(candidate)

    if not path.exists():
        return str(original_path)

    if expected:
        try:
            actual = _sha256(path)

        except Exception:
            return str(original_path)

        if actual != expected:
            return str(original_path)

    return str(path)


def describe_scene(scene):
    number = _scene_number(scene)

    if number is None:
        return {}

    return (
        load_manifest()
        .get("scenes", {})
        .get(str(number), {})
    )
