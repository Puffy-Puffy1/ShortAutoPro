#!/usr/bin/env python3

import functools
import inspect
import os
import re
from pathlib import Path

from vg4x_score import (
    note_selection,
)


_COMMITS = {}


def reset_commits():
    _COMMITS.clear()


def _bind(
    function,
    args,
    kwargs,
):

    try:
        return inspect.signature(
            function
        ).bind_partial(
            *args,
            **kwargs,
        ).arguments
    except Exception:
        return {}


def _scene_number(bound):

    for name in (
        "numero",
        "numero_cena",
        "scene_num",
        "scene_number",
        "scene_index",
        "indice",
        "idx",
        "cena",
    ):

        value = bound.get(name)

        if isinstance(value, int):
            return value

        if isinstance(value, str):

            match = re.search(
                r"\d+",
                value,
            )

            if match:
                return int(
                    match.group(0)
                )

    return None


def _candidate(bound):

    for name in (
        "candidato",
        "candidate",
        "item",
        "asset",
    ):

        if name in bound:
            return bound[name]

    return None


def _success_result(result):

    if isinstance(
        result,
        tuple,
    ) and result:

        return bool(
            result[0]
        )

    return bool(result)


def _destination(result):

    if (
        isinstance(result, tuple)
        and len(result) >= 2
    ):
        return result[1]

    return None


def _clean_siblings(destination):

    if not destination:
        return

    path = Path(
        str(destination)
    )

    if not path.exists():
        return

    match = re.match(
        r"(scene_\d+)",
        path.stem,
    )

    if not match:
        return

    stem = match.group(1)

    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
    }

    for sibling in path.parent.glob(
        f"{stem}.*"
    ):

        if sibling == path:
            continue

        if sibling.suffix.lower() not in allowed:
            continue

        try:
            sibling.unlink()

            print(
                "VG4X_SIBLING_REMOVED="
                f"{sibling.name}"
            )

        except Exception:
            pass


def install(namespace):

    if (
        os.getenv(
            "SAP_VG4X_COMMIT",
            "1",
        )
        ==
        "0"
    ):
        return {
            "installed": False,
            "reason": "DISABLED",
        }

    original = namespace.get(
        "baixar_candidato_5_2"
    )

    if not callable(original):
        return {
            "installed": False,
            "reason":
                "baixar_candidato_5_2_missing",
        }

    if getattr(
        original,
        "_vg4x_commit_wrapped",
        False,
    ):
        return {
            "installed": True,
            "reason": "ALREADY",
        }

    @functools.wraps(original)
    def wrapped(
        *args,
        **kwargs,
    ):

        bound = _bind(
            original,
            args,
            kwargs,
        )

        number = _scene_number(
            bound
        )

        candidate = _candidate(
            bound
        )

        if (
            number is not None
            and number in _COMMITS
        ):

            committed = _COMMITS[
                number
            ]

            print(
                "VG4X_SCENE_COMMIT=BLOCKED "
                f"scene={number:02d} "
                f"winner={committed}"
            )

            return (
                False,
                committed,
            )

        result = original(
            *args,
            **kwargs,
        )

        if not _success_result(
            result
        ):
            return result

        destination = _destination(
            result
        )

        if number is None and destination:

            match = re.search(
                r"scene_(\d+)",
                str(destination),
            )

            if match:
                number = int(
                    match.group(1)
                )

        if number is not None:

            _COMMITS[
                number
            ] = (
                str(destination)
                if destination
                else
                f"scene_{number:02d}"
            )

            print(
                "VG4X_SCENE_COMMIT=COMMITTED "
                f"scene={number:02d} "
                f"path={_COMMITS[number]}"
            )

        _clean_siblings(
            destination
        )

        if candidate is not None:
            note_selection(
                candidate
            )

        return result

    wrapped._vg4x_commit_wrapped = True

    namespace[
        "baixar_candidato_5_2"
    ] = wrapped

    return {
        "installed": True,
        "reason": "OK",
    }
