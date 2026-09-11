#!/usr/bin/env python3

VERSION = "8.62"


INTENT = {
    "FACE": [
        "portrait",
        "clear face",
        "documentary photograph",
    ],

    "DOCUMENT": [
        "original document",
        "archive",
        "close detail",
    ],

    "EVIDENCE": [
        "forensic evidence",
        "documentary",
        "close detail",
    ],

    "LOCATION": [
        "location",
        "exterior",
        "documentary photograph",
    ],

    "OBJECT": [
        "object detail",
        "documentary photograph",
    ],

    "GENERAL": [
        "documentary photograph",
    ],
}


def build(category):
    category = str(
        category or "GENERAL"
    ).upper()

    return list(
        INTENT.get(
            category,
            INTENT["GENERAL"]
        )
    )


def self_test():
    assert (
        "portrait"
        in build("FACE")
    )

    print(
        "VI8.62 SEARCH INTENT BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
