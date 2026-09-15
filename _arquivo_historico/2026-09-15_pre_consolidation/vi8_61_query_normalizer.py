#!/usr/bin/env python3

import re

VERSION = "8.61"

REMOVE = {
    "image",
    "photo",
    "picture",
    "stock",
    "wallpaper",
    "4k",
    "hd",
}

def normalize(text):
    tokens = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    cleaned = []

    seen = set()

    for token in tokens:
        low = token.lower()

        if low in REMOVE:
            continue

        if low in seen:
            continue

        seen.add(low)
        cleaned.append(token)

    return " ".join(
        cleaned
    ).strip()


def self_test():
    result = normalize(
        "ransom note image photo ransom note"
    )

    assert "image" not in result.lower()
    assert "photo" not in result.lower()

    print(
        "VI8.61 QUERY NORMALIZER=PASS"
    )


if __name__ == "__main__":
    self_test()
