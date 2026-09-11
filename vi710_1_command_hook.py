#!/usr/bin/env python3

import hashlib
import importlib
import json
import os
from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

DEFAULT_TRACE = (
    BASE
    / "temp"
    / "vi710_1_canary"
    / "command_trace.jsonl"
)


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


def trace(payload):

    path = Path(
        os.getenv(
            "VI710_1_TRACE",
            str(DEFAULT_TRACE)
        )
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                payload,
                ensure_ascii=False
            )
            + "\n"
        )


def enabled():

    return (
        os.getenv(
            "VI700_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
        and
        os.getenv(
            "VI700_PORTFOLIO_CANARY",
            "OFF"
        ).upper()
        == "ON"
    )


def manifest():

    runtime = importlib.import_module(
        "vi700_runtime_override"
    )

    return runtime.load_manifest()


def active_entries():

    data = manifest()

    scenes = (
        data.get(
            "scenes"
        )
        or {}
    )

    result = {}

    for key, entry in (
        scenes.items()
    ):

        if not entry.get(
            "override_active"
        ):
            continue

        try:

            scene = int(key)

        except Exception:

            continue

        original = entry.get(
            "original_path"
        )

        candidate = entry.get(
            "canary_path"
        )

        expected = entry.get(
            "expected_sha256"
        )

        if not original:
            continue

        if not candidate:
            continue

        candidate_path = Path(
            candidate
        )

        if not candidate_path.exists():

            result[scene] = {
                "valid":
                    False,

                "reason":
                    "candidate_missing",

                "original":
                    original,

                "candidate":
                    candidate,
            }

            continue

        actual = sha256(
            candidate_path
        )

        if (
            expected
            and actual != expected
        ):

            result[scene] = {
                "valid":
                    False,

                "reason":
                    "candidate_hash_mismatch",

                "original":
                    original,

                "candidate":
                    candidate,

                "expected":
                    expected,

                "actual":
                    actual,
            }

            continue

        original_path = Path(
            original
        )

        try:

            relative = str(
                original_path.relative_to(
                    BASE
                )
            )

        except Exception:

            relative = os.path.relpath(
                str(original_path),
                str(BASE)
            )

        result[scene] = {
            "valid":
                True,

            "original":
                str(original_path),

            "relative":
                relative,

            "basename":
                original_path.name,

            "candidate":
                str(candidate_path),

            "sha256":
                actual,

            "mode":
                entry.get(
                    "mode"
                ),
        }

    return result


def validate_all():

    entries = active_entries()

    expected = {
        3,
        8,
        9,
        10,
        11,
    }

    actual = {
        scene
        for scene, entry
        in entries.items()
        if entry.get(
            "valid"
        )
    }

    invalid = {
        scene:
            entry
        for scene, entry
        in entries.items()
        if not entry.get(
            "valid"
        )
    }

    return {
        "expected":
            sorted(expected),

        "valid":
            sorted(actual),

        "invalid":
            invalid,

        "all_valid":
            actual == expected
            and not invalid,
    }


def replace_string(
    value,
    previous=None
):

    if not isinstance(
        value,
        (str, Path)
    ):
        return value, []

    original_value = str(
        value
    )

    new_value = original_value

    matches = []

    entries = active_entries()

    for scene, entry in (
        entries.items()
    ):

        if not entry.get(
            "valid"
        ):
            continue

        original = entry[
            "original"
        ]

        relative = entry[
            "relative"
        ]

        basename = entry[
            "basename"
        ]

        candidate = entry[
            "candidate"
        ]

        replaced = False

        # Absolute path.
        if original in new_value:

            new_value = new_value.replace(
                original,
                candidate
            )

            replaced = True

        # Relative project path.
        elif (
            relative
            and relative
            in new_value
        ):

            new_value = new_value.replace(
                relative,
                candidate
            )

            replaced = True

        # Bare basename is accepted ONLY
        # when it is clearly an FFmpeg input.
        elif (
            new_value == basename
            and previous == "-i"
        ):

            new_value = candidate

            replaced = True

        if replaced:

            matches.append({
                "scene":
                    scene,

                "original":
                    original,

                "candidate":
                    candidate,

                "mode":
                    entry.get(
                        "mode"
                    ),
            })

    if isinstance(
        value,
        Path
    ):

        return Path(
            new_value
        ), matches

    return new_value, matches


def rewrite_command(command):

    if isinstance(
        command,
        str
    ):

        rewritten, matches = (
            replace_string(
                command
            )
        )

        return rewritten, matches

    if isinstance(
        command,
        tuple
    ):

        source = list(
            command
        )

        tuple_mode = True

    elif isinstance(
        command,
        list
    ):

        source = list(
            command
        )

        tuple_mode = False

    else:

        return command, []

    output = []

    all_matches = []

    previous = None

    for token in source:

        rewritten, matches = (
            replace_string(
                token,
                previous=previous
            )
        )

        output.append(
            rewritten
        )

        all_matches.extend(
            matches
        )

        previous = str(
            token
        )

    # De-duplicate scene matches.
    unique = {}

    for item in all_matches:

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

        return tuple(
            output
        ), matches

    return output, matches


def command_preview(command):

    if isinstance(
        command,
        (list, tuple)
    ):

        return [
            str(x)[:300]
            for x in command[:40]
        ]

    return str(
        command
    )[:1200]


def self_test():

    validation = validate_all()

    fake = [
        "ffmpeg",
        "-loop",
        "1",
        "-i",
        str(
            BASE
            / "imagens"
            / "short_2026-09-01_1433"
            / "scene_03.jpg"
        ),
        "-f",
        "null",
        "-"
    ]

    rewritten, matches = (
        rewrite_command(
            fake
        )
    )

    return {
        "validation":
            validation,

        "synthetic_before":
            fake,

        "synthetic_after":
            rewritten,

        "synthetic_matches":
            matches,

        "synthetic_pass":
            any(
                item[
                    "scene"
                ] == 3
                for item in matches
            ),
    }


def activate():

    module = importlib.import_module(
        "vi6_95_scene_executor"
    )

    if getattr(
        module,
        "_vi710_1_command_hook",
        False
    ):

        return {
            "patched":
                True,

            "reason":
                "already_patched",
        }

    original_execute = getattr(
        module,
        "execute"
    )

    def patched_execute(
        command,
        **run_kwargs
    ):

        use_canary = enabled()

        rewritten = command

        matches = []

        if use_canary:

            rewritten, matches = (
                rewrite_command(
                    command
                )
            )

        event = {
            "enabled":
                use_canary,

            "matched_scenes":
                [
                    item[
                        "scene"
                    ]
                    for item in matches
                ],

            "changed":
                bool(
                    matches
                ),

            "replacements":
                matches,

            "command_before":
                command_preview(
                    command
                ),

            "command_after":
                command_preview(
                    rewritten
                ),
        }

        try:

            result = original_execute(
                rewritten,
                **run_kwargs
            )

            event[
                "status"
            ] = "SUCCESS"

            trace(
                event
            )

            return result

        except BaseException as exc:

            event[
                "status"
            ] = "ERROR"

            event[
                "error"
            ] = (
                type(exc).__name__
                + ": "
                + str(exc)[:500]
            )

            trace(
                event
            )

            raise

    setattr(
        module,
        "_vi710_1_original_execute",
        original_execute
    )

    setattr(
        module,
        "execute",
        patched_execute
    )

    setattr(
        module,
        "_vi710_1_command_hook",
        True
    )

    return {
        "patched":
            True,

        "validation":
            validate_all(),
    }
