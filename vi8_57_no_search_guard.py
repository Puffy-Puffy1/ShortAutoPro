#!/usr/bin/env python3

VERSION = "8.57"


def evaluate(
    search_item
):
    reasons = []

    if (
        search_item.get(
            "need"
        )
        == "NONE"
    ):
        reasons.append(
            "real_media_already_competitive"
        )

    if not search_item.get(
        "worthwhile"
    ):
        reasons.append(
            "gain_below_threshold"
        )

    return {
        "version": VERSION,
        "scene":
            search_item.get(
                "scene"
            ),
        "skip":
            bool(reasons),
        "reasons":
            reasons,
    }


def self_test():
    result = evaluate({
        "scene": 3,
        "need": "NONE",
        "worthwhile": False,
    })

    assert result["skip"] is True

    print(
        "VI8.57 NO SEARCH GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
