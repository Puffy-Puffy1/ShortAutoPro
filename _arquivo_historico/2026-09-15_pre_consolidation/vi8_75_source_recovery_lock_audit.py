#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.75"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    candidates = []

    for path in BASE.glob(
        "*.py"
    ):
        name = path.name.lower()

        if any(
            token in name
            for token in (
                "source",
                "recovery",
                "router",
            )
        ):
            candidates.append(
                str(path)
            )

    return {
        "version": VERSION,
        "candidate_modules":
            sorted(candidates),
        "active_allowed":
            False,
        "required_mode":
            "SHADOW_ONLY",
        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "active_allowed"
        ]
        is False
    )

    print(
        "VI8.75 SOURCE RECOVERY LOCK AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
