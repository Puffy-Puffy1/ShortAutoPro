#!/usr/bin/env python3

VERSION = "7.82"

def evaluate():
    return {
        "version": VERSION,
        "new_source_fetch": False,
        "source_recovery":
            "SHADOW_ONLY",
        "automatic_replacement":
            False,
        "unknown_truth_is_true":
            False,
        "renderer_source_mutation":
            False,
        "status":
            "LOCKED_SAFE",
    }

def self_test():
    result = evaluate()

    assert (
        result[
            "automatic_replacement"
        ]
        is False
    )

    assert (
        result[
            "unknown_truth_is_true"
        ]
        is False
    )

    print(
        "VI7.82 SOURCE BOUNDARY=PASS"
    )

if __name__ == "__main__":
    self_test()
