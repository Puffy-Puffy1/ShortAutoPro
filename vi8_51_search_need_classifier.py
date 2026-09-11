#!/usr/bin/env python3

VERSION = "8.51"


def evaluate(scene_result):
    gap = (
        scene_result.get("gap")
        or {}
    )

    status = gap.get(
        "status"
    )

    real_count = int(
        scene_result.get(
            "real_candidate_count",
            0
        )
        or 0
    )

    if status == "NO_REAL_MEDIA":
        need = "CRITICAL"

    elif status == "STRONG_REAL_MEDIA_GAP":
        need = "HIGH"

    elif status == "REAL_MEDIA_GAP":
        need = "MEDIUM"

    elif status == "MINOR_REAL_MEDIA_GAP":
        need = "LOW"

    elif status == "REAL_MEDIA_COMPETITIVE":
        need = "NONE"

    else:
        need = (
            "LOW"
            if real_count
            else "CRITICAL"
        )

    return {
        "version": VERSION,
        "scene":
            scene_result.get(
                "scene"
            ),
        "need": need,
        "gap_status": status,
        "real_count": real_count,
    }


def self_test():
    result = evaluate({
        "scene": 5,
        "real_candidate_count": 1,
        "gap": {
            "status":
                "STRONG_REAL_MEDIA_GAP"
        }
    })

    assert result["need"] == "HIGH"

    print(
        "VI8.51 SEARCH NEED CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
