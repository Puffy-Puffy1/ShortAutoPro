#!/usr/bin/env python3

VERSION = "8.14"

def compare(
    current_score,
    best_score
):
    delta = (
        float(best_score)
        - float(current_score)
    )

    if delta >= 15:
        recommendation = (
            "STRONG_REPLACEMENT_CANDIDATE"
        )

    elif delta >= 7:
        recommendation = (
            "REPLACEMENT_CANDIDATE"
        )

    elif delta >= 2:
        recommendation = (
            "MINOR_IMPROVEMENT"
        )

    else:
        recommendation = (
            "KEEP_CURRENT"
        )

    return {
        "version": VERSION,
        "delta":
            round(delta, 2),
        "recommendation":
            recommendation,
    }

def self_test():
    result = compare(
        60,
        90
    )

    assert (
        result["recommendation"]
        == "STRONG_REPLACEMENT_CANDIDATE"
    )

    print(
        "VI8.14 CURRENT VS IDEAL=PASS"
    )

if __name__ == "__main__":
    self_test()
