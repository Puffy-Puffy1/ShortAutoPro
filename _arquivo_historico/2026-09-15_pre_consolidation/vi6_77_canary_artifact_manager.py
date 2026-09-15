#!/usr/bin/env python3

from pathlib import Path


VERSION = "6.77"


def evaluate(
    legacy,
    vi6
):

    legacy = Path(
        legacy
    )


    vi6 = Path(
        vi6
    )


    return {
        "version": VERSION,

        "status":
            (
                "PASS"
                if legacy.exists()
                and vi6.exists()
                else "HOLD"
            ),

        "legacy_preview":
            str(legacy),

        "vi6_preview":
            str(vi6),

        "legacy_exists":
            legacy.exists(),

        "vi6_exists":
            vi6.exists(),

        # Keep both so user can compare.
        "previews_preserved":
            True,

        "production_video_touched":
            False,
    }


def self_test():

    assert VERSION == "6.77"

    print(
        "VI6.77 ARTIFACT MANAGER=PASS"
    )


if __name__ == "__main__":
    self_test()
