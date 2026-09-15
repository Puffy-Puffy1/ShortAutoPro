#!/usr/bin/env python3

VERSION = "8.63"


SHOT_TERMS = {
    "close_up": [
        "close up",
        "detail",
    ],

    "medium": [
        "medium shot",
        "waist up",
    ],

    "wide": [
        "wide shot",
        "environment",
    ],
}


def terms(shot):
    return list(
        SHOT_TERMS.get(
            str(
                shot or "medium"
            ).lower(),
            SHOT_TERMS["medium"]
        )
    )


def self_test():
    assert (
        "wide shot"
        in terms("wide")
    )

    print(
        "VI8.63 SHOT SEARCH LANGUAGE=PASS"
    )


if __name__ == "__main__":
    self_test()
