#!/usr/bin/env python3

VERSION = "8.47"


def evaluate(
    ranking
):
    gap = ranking.get(
        "virtual_advantage"
    )

    real_count = int(
        ranking.get(
            "real_candidate_count",
            0
        )
        or 0
    )

    if real_count == 0:
        status = (
            "NO_REAL_MEDIA"
        )

    elif gap is None:
        status = (
            "REAL_ONLY_OR_UNKNOWN"
        )

    elif gap >= 15:
        status = (
            "STRONG_REAL_MEDIA_GAP"
        )

    elif gap >= 7:
        status = (
            "REAL_MEDIA_GAP"
        )

    elif gap >= 2:
        status = (
            "MINOR_REAL_MEDIA_GAP"
        )

    else:
        status = (
            "REAL_MEDIA_COMPETITIVE"
        )

    return {
        "version":
            VERSION,

        "real_candidate_count":
            real_count,

        "virtual_advantage":
            gap,

        "status":
            status,
    }


def self_test():
    result = evaluate({
        "real_candidate_count": 2,
        "virtual_advantage": 18
    })

    assert (
        result["status"]
        == "STRONG_REAL_MEDIA_GAP"
    )

    print(
        "VI8.47 REAL MEDIA GAP=PASS"
    )


if __name__ == "__main__":
    self_test()
