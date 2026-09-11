#!/usr/bin/env python3

VERSION = "6.63"


TRUE_VALUES = {
    True,
    1,
    "1",
    "true",
    "yes",
    "pass",
    "verified",
    "confirmed",
}


FALSE_VALUES = {
    False,
    0,
    "0",
    "false",
    "no",
    "fail",
    "rejected",
    "invalid",
}


def normalize(value):

    if isinstance(value, str):
        value = value.strip().lower()


    if value in TRUE_VALUES:

        return "TRUE"


    if value in FALSE_VALUES:

        return "FALSE"


    # Critical policy:
    # missing/unclear data NEVER becomes TRUE.
    return "UNKNOWN"


def evaluate(value):

    state = normalize(value)


    return {
        "version": VERSION,
        "state": state,
        "safe_for_active":
            state == "TRUE",
        "unknown_promoted_to_true":
            False,
    }


def self_test():

    assert normalize(True) == "TRUE"
    assert normalize(False) == "FALSE"
    assert normalize(None) == "UNKNOWN"
    assert normalize("maybe") == "UNKNOWN"

    assert (
        evaluate(None)["safe_for_active"]
        is False
    )


    print("VI6.63 TRUTH HARDENER=PASS")


if __name__ == "__main__":
    self_test()
