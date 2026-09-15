#!/usr/bin/env python3

from vi8_53_minimum_gain_policy import (
    threshold
)

VERSION = "8.54"


def evaluate(
    need,
    virtual_advantage
):
    gap = float(
        virtual_advantage
        or 0
    )

    minimum = threshold(
        need
    )

    worthwhile = (
        need == "CRITICAL"
        or gap >= minimum
    )

    if need == "NONE":
        worthwhile = False

    return {
        "version": VERSION,
        "need": need,
        "gap": round(
            gap,
            2
        ),
        "minimum_gain":
            minimum,
        "worthwhile":
            worthwhile,
    }


def self_test():
    result = evaluate(
        "HIGH",
        15
    )

    assert result[
        "worthwhile"
    ] is True

    print(
        "VI8.54 SEARCH VALUE ESTIMATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
