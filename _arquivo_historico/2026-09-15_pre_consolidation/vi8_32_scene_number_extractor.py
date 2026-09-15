#!/usr/bin/env python3

import re

VERSION = "8.32"


PATTERNS = (
    r"(?:scene|cena)[_-]?0*(\d+)",
    r"^0*(\d+)[_.-]",
)


def extract(name):

    text = str(
        name or ""
    ).lower()

    for pattern in PATTERNS:

        match = re.search(
            pattern,
            text
        )

        if match:

            number = int(
                match.group(1)
            )

            if 1 <= number <= 12:
                return number

    return None


def self_test():

    assert (
        extract(
            "scene_05.jpg"
        )
        == 5
    )

    assert (
        extract(
            "cena07.png"
        )
        == 7
    )

    print(
        "VI8.32 SCENE NUMBER EXTRACTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
