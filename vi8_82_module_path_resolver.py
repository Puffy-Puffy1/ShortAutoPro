#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.82"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def resolve(relative_path):
    if not relative_path:
        return {
            "status": "HOLD",
            "reason":
                "module_path_missing",
            "path": None,
        }

    candidate = (
        BASE
        / relative_path
    ).resolve()

    base = BASE.resolve()

    try:
        candidate.relative_to(
            base
        )
    except Exception:
        return {
            "status": "HOLD",
            "reason":
                "path_escape_detected",
            "path": None,
        }

    if not candidate.exists():
        return {
            "status": "HOLD",
            "reason":
                "module_not_found",
            "path": str(
                candidate
            ),
        }

    if candidate.suffix not in {
        ".py",
        ".sh",
    }:
        return {
            "status": "HOLD",
            "reason":
                "unsupported_module_type",
            "path": str(
                candidate
            ),
        }

    return {
        "status": "PASS",
        "reason": None,
        "path": str(
            candidate
        ),
    }


def self_test():
    result = resolve(
        "video.py"
    )

    assert result[
        "status"
    ] == "PASS"

    print(
        "VI8.82 MODULE PATH RESOLVER=PASS"
    )


if __name__ == "__main__":
    self_test()
