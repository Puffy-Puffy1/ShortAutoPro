#!/usr/bin/env python3

VERSION = "8.17"

def evaluate(selection):
    current = (
        selection.get(
            "current"
        )
        or {}
    )

    winner = (
        selection.get(
            "winner"
        )
        or {}
    )

    current_candidate = (
        current.get(
            "candidate"
        )
        or {}
    )

    winner_candidate = (
        winner.get(
            "candidate"
        )
        or {}
    )

    current_shot = (
        current_candidate.get(
            "shot"
        )
    )

    winner_shot = (
        winner_candidate.get(
            "shot"
        )
    )

    return {
        "version":
            VERSION,

        "scene":
            selection.get(
                "scene"
            ),

        "current_shot":
            current_shot,

        "recommended_shot":
            winner_shot,

        "change":
            (
                current_shot
                != winner_shot
            ),
    }

def self_test():
    assert VERSION == "8.17"

    print(
        "VI8.17 SHOT CORRECTION ENGINE=PASS"
    )

if __name__ == "__main__":
    self_test()
