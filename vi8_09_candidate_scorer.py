#!/usr/bin/env python3

from vi8_02_crop_fitness import (
    evaluate as crop_fitness
)

from vi8_03_subject_shot_compatibility import (
    score as shot_score
)

from vi8_04_narrative_relevance import (
    evaluate as relevance
)

from vi8_05_documentary_value import (
    score as documentary_score
)

from vi8_06_identity_safety import (
    evaluate as identity_safety
)

from vi8_07_media_quality_score import (
    evaluate as media_quality
)

from vi8_08_duplication_penalty import (
    penalty as duplication_penalty
)

VERSION = "8.09"

def evaluate(
    scene,
    candidate,
    previous_candidates=None
):
    category = (
        candidate.get("category")
        or scene.get(
            "cinematic_category"
        )
        or "GENERAL"
    )

    shot = (
        candidate.get("shot")
        or scene.get(
            "shot_type"
        )
        or "medium"
    )

    crop = crop_fitness(
        candidate.get("width"),
        candidate.get("height")
    )

    shot_fit = shot_score(
        category,
        shot
    )

    rel = relevance(
        scene,
        candidate
    )

    documentary = documentary_score(
        category
    )

    identity = identity_safety(
        category,
        candidate
    )

    quality = media_quality(
        candidate
    )

    duplicate = duplication_penalty(
        candidate,
        previous_candidates
        or []
    )

    blockers = []

    blockers.extend(
        identity.get("blockers")
        or []
    )

    base = (
        rel["score"] * .32
        + shot_fit * .20
        + crop["score"] * .14
        + documentary * .14
        + quality["score"] * .12
        + float(
            candidate.get(
                "source_score",
                0
            )
            or 0
        ) * .08
    )

    final = (
        base
        - duplicate["penalty"]
    )

    final = max(
        0.0,
        min(100.0, final)
    )

    return {
        "version": VERSION,
        "score":
            round(final, 2),
        "category":
            category,
        "shot":
            shot,
        "components": {
            "relevance":
                rel["score"],
            "shot":
                shot_fit,
            "crop":
                crop["score"],
            "documentary":
                documentary,
            "quality":
                quality["score"],
            "source":
                float(
                    candidate.get(
                        "source_score",
                        0
                    )
                    or 0
                ),
            "duplicate_penalty":
                duplicate[
                    "penalty"
                ],
        },
        "blockers":
            blockers,
        "warnings":
            identity.get(
                "warnings"
            )
            or [],
        "eligible":
            not blockers,
    }

def self_test():
    scene = {
        "segment":
            "a ransom note was discovered",
        "query":
            "ransom note",
        "shot_type":
            "close_up",
        "cinematic_category":
            "DOCUMENT",
    }

    candidate = {
        "path":
            "note.jpg",
        "category":
            "DOCUMENT",
        "shot":
            "close_up",
        "width":
            1200,
        "height":
            1600,
        "query":
            "ransom note handwritten paper",
        "source_score":
            90,
        "metadata": {},
    }

    result = evaluate(
        scene,
        candidate
    )

    assert result[
        "score"
    ] >= 70

    print(
        "VI8.09 CANDIDATE SCORER=PASS"
    )

if __name__ == "__main__":
    self_test()
