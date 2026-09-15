#!/usr/bin/env python3

import json
import os
from pathlib import Path

import vi1000_runtime as runtime


VERSION = "1000.00"


def active_entries():
    data = (
        runtime.load_manifest()
    )

    result = {}

    for key, entry in (
        data.get(
            "scenes",
            {}
        ).items()
    ):
        try:
            scene = int(key)

        except Exception:
            continue

        if not entry.get(
            "override_active"
        ):
            continue

        validation = (
            runtime.validate_entry(
                scene,
                entry
            )
        )

        result[
            scene
        ] = {
            "entry":
                entry,

            "validation":
                validation,
        }

    return result


def replace_token(
    value,
    previous=None
):
    if not isinstance(
        value,
        (str, Path)
    ):
        return value, []

    raw = str(
        value
    )

    rewritten = raw

    matches = []

    for scene, payload in (
        active_entries().items()
    ):
        validation = payload[
            "validation"
        ]

        if not validation[
            "valid"
        ]:
            continue

        entry = payload[
            "entry"
        ]

        original = str(
            entry.get(
                "original_path"
            )
            or ""
        )

        candidate = validation[
            "path"
        ]

        if not original:
            continue

        original_path = Path(
            original
        )

        basename = (
            original_path.name
        )

        try:
            relative = str(
                original_path.relative_to(
                    runtime.BASE
                )
            )

        except Exception:
            relative = os.path.relpath(
                original,
                runtime.BASE
            )

        changed = False

        if original in rewritten:
            rewritten = (
                rewritten.replace(
                    original,
                    candidate
                )
            )

            changed = True

        elif (
            relative
            and relative
            in rewritten
        ):
            rewritten = (
                rewritten.replace(
                    relative,
                    candidate
                )
            )

            changed = True

        elif (
            previous == "-i"
            and rewritten
            == basename
        ):
            rewritten = candidate

            changed = True

        if changed:
            matches.append({
                "scene":
                    scene,

                "original":
                    original,

                "candidate":
                    candidate,
            })

    if isinstance(
        value,
        Path
    ):
        return (
            Path(rewritten),
            matches
        )

    return (
        rewritten,
        matches
    )


def rewrite_command(
    command
):
    if isinstance(
        command,
        str
    ):
        return replace_token(
            command
        )

    if not isinstance(
        command,
        (
            list,
            tuple,
        )
    ):
        return (
            command,
            []
        )

    tuple_mode = isinstance(
        command,
        tuple
    )

    output = []

    matches = []

    previous = None

    for token in command:
        rewritten, current = (
            replace_token(
                token,
                previous=previous
            )
        )

        output.append(
            rewritten
        )

        matches.extend(
            current
        )

        previous = str(
            token
        )

    unique = {}

    for item in matches:
        unique[
            item["scene"]
        ] = item

    matches = [
        unique[key]
        for key in sorted(
            unique
        )
    ]

    if tuple_mode:
        output = tuple(
            output
        )

    return (
        output,
        matches
    )


def synthetic_test():
    manifest = (
        runtime.load_manifest()
    )

    results = []

    for key, entry in (
        manifest.get(
            "scenes",
            {}
        ).items()
    ):
        try:
            scene = int(key)

        except Exception:
            continue

        if not entry.get(
            "override_active"
        ):
            continue

        original = entry.get(
            "original_path"
        )

        if not original:
            continue

        command = [
            "ffmpeg",
            "-i",
            original,
            "-f",
            "null",
            "-"
        ]

        rewritten, matches = (
            rewrite_command(
                command
            )
        )

        results.append({
            "scene":
                scene,

            "matches":
                [
                    item[
                        "scene"
                    ]
                    for item in matches
                ],

            "rewritten":
                rewritten,
        })

    return results


if __name__ == "__main__":
    print(
        json.dumps(
            synthetic_test(),
            ensure_ascii=False,
            indent=2
        )
    )
