#!/usr/bin/env python3

VERSION = "8.07"

def resolution_score(
    width,
    height
):
    try:
        pixels = (
            int(width)
            * int(height)
        )
    except Exception:
        return 50.0

    if pixels >= 2_000_000:
        return 100.0

    if pixels >= 1_000_000:
        return 90.0

    if pixels >= 500_000:
        return 75.0

    if pixels >= 250_000:
        return 60.0

    return 40.0

def evaluate(candidate):
    result = resolution_score(
        candidate.get("width"),
        candidate.get("height")
    )

    return {
        "version": VERSION,
        "score": result,
    }

def self_test():
    assert (
        resolution_score(
            1920,
            1080
        )
        == 100
    )

    print(
        "VI8.07 MEDIA QUALITY SCORE=PASS"
    )

if __name__ == "__main__":
    self_test()
