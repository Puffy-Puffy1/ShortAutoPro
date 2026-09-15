#!/usr/bin/env python3

from vi1510_01_common import (
    policy,
    save_json,
)


def status_pass(
    value,
):
    return (
        value.get(
            "status"
        )
        ==
        "PASS"
    )


def run(
    provenance,
    relevance,
    leak,
    stale,
    technical,
    visual,
    media_quality,
    run_dir,
):
    blockers = []


    for component in [
        provenance,
        relevance,
        leak,
        stale,
        technical,
    ]:

        blockers.extend(
            component.get(
                "blockers",
                []
            )
        )


    visual_blockers = (
        visual.get(
            "blockers"
        )
        or []
    )


    blockers.extend(
        visual_blockers
    )


    blockers.extend(
        media_quality.get(
            "blockers",
            []
        )
    )


    score = 0.0


    if provenance.get(
        "status"
    ) == "PASS":
        score += 2.5


    if relevance.get(
        "status"
    ) == "PASS":
        score += 1.5


    if leak.get(
        "status"
    ) == "PASS":
        score += 1.5


    if stale.get(
        "status"
    ) == "PASS":
        score += 0.5


    if technical.get(
        "status"
    ) == "PASS":
        score += 0.5


    visual_average = float(
        visual.get(
            "average_strength"
        )
        or 0
    )


    score += (
        min(
            10.0,
            visual_average
        )
        /
        10.0
        *
        2.0
    )


    if media_quality.get(
        "status"
    ) == "PASS":
        score += 1.5


    score = round(
        min(
            10,
            score
        ),
        2
    )


    minimum = float(
        policy().get(
            "release_score_min",
            8.0
        )
    )


    ready = (
        score >= minimum

        and

        not blockers
    )


    report = {
        "score":
            score,

        "minimum":
            minimum,

        "ready":
            ready,

        "visual_average":
            visual_average,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "components": {
            "provenance":
                provenance.get(
                    "status"
                ),

            "relevance":
                relevance.get(
                    "status"
                ),

            "leak":
                leak.get(
                    "status"
                ),

            "stale":
                stale.get(
                    "status"
                ),

            "technical":
                technical.get(
                    "status"
                ),

            "visual":
                visual.get(
                    "status"
                ),

            "media_quality":
                media_quality.get(
                    "status"
                ),
        },
    }


    save_json(
        run_dir
        / "score_v2.json",
        report
    )


    return report
