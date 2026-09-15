#!/usr/bin/env python3

from vi8_37_real_candidate_converter import (
    convert
)

from vi8_44_real_shot_estimator import (
    estimate
)

VERSION = "8.45"


def enrich(
    item,
    scene,
    category
):
    candidate = convert(
        item,
        scene,
        category
    )

    candidate["shot"] = estimate(
        item,
        category,
        scene
    )

    metadata = (
        candidate.get(
            "metadata"
        )
        or {}
    )

    metadata[
        "scene_guess"
    ] = item.get(
        "scene_guess"
    )

    metadata[
        "size_bytes"
    ] = item.get(
        "size_bytes"
    )

    metadata[
        "crop_fitness"
    ] = item.get(
        "crop_fitness"
    )

    candidate[
        "metadata"
    ] = metadata

    return candidate


def self_test():
    result = enrich(
        {
            "path": "a.jpg",
            "name": "a.jpg",
            "media_type": "STILL",
            "width": 1200,
            "height": 1600,
            "orientation": "PORTRAIT",
            "technical_score": 90,
            "scene_guess": 4,
            "size_bytes": 1000000,
        },
        {
            "query": "document",
            "shot_type":
                "close_up",
        },
        "DOCUMENT"
    )

    assert (
        result["shot"]
        == "close_up"
    )

    print(
        "VI8.45 REAL CANDIDATE ENRICHER=PASS"
    )


if __name__ == "__main__":
    self_test()
