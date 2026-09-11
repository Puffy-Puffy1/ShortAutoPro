#!/usr/bin/env python3

VERSION = "8.02"

TARGET_RATIO = 1080 / 1920

def evaluate(width, height):
    try:
        width = float(width)
        height = float(height)

    except Exception:
        return {
            "version": VERSION,
            "score": 50.0,
            "status": "UNKNOWN",
        }

    if width <= 0 or height <= 0:
        return {
            "version": VERSION,
            "score": 0.0,
            "status": "INVALID",
        }

    ratio = width / height

    distance = abs(
        ratio - TARGET_RATIO
    )

    if ratio <= 0.7:
        score = 100 - distance * 30

    elif ratio <= 1.0:
        score = 90 - distance * 35

    elif ratio <= 1.5:
        score = 75 - distance * 35

    else:
        score = 55 - distance * 20

    score = max(
        0.0,
        min(100.0, score)
    )

    return {
        "version": VERSION,
        "ratio": round(ratio, 3),
        "score": round(score, 2),
        "status": (
            "PASS"
            if score >= 70
            else "CAUTION"
        ),
    }

def self_test():
    portrait = evaluate(
        1080,
        1920
    )

    assert portrait["score"] >= 95

    print(
        "VI8.02 CROP FITNESS=PASS"
    )

if __name__ == "__main__":
    self_test()
