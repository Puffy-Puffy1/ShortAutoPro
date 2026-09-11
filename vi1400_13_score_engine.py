#!/usr/bin/env python3

from vi1400_01_common import (
    TMP,
    load_json,
    policy,
    save_json,
)


def run():
    config = policy()


    visual_target = float(
        config.get(
            "visual_average_target",
            8.5
        )
    )


    release_min = float(
        config.get(
            "release_score_min",
            8.0
        )
    )


    visual = load_json(
        TMP
        / "visual_qa.json"
    )


    editorial = load_json(
        TMP
        / "editorial_qa.json"
    )


    subtitles = load_json(
        TMP
        / "subtitle_qa.json"
    )


    audio = load_json(
        TMP
        / "audio_qa.json"
    )


    temporal = load_json(
        TMP
        / "temporal_qa.json"
    )


    guard = load_json(
        TMP
        / "operational_guard.json"
    )


    components = [
        visual,
        editorial,
        subtitles,
        audio,
        temporal,
        guard,
    ]


    blockers = sum(
        [
            (
                item.get(
                    "blockers"
                )
                or []
            )

            for item
            in components
        ],
        []
    )


    warnings = sum(
        [
            (
                item.get(
                    "warnings"
                )
                or []
            )

            for item
            in components
        ],
        []
    )


    score = 10.0


    score -= max(
        0,
        visual_target
        -
        float(
            visual.get(
                "average_strength"
            )
            or 0
        ),
    ) * 0.55


    score -= min(
        1.4,
        len(
            warnings
        )
        * 0.08
    )


    score -= min(
        6.0,
        len(
            blockers
        )
        * 1.5
    )


    score = round(
        max(
            0,
            min(
                10,
                score
            )
        ),
        2
    )


    ready = (
        not blockers

        and

        score
        >=
        release_min
    )


    report = {
        "score":
            score,

        "ready_for_final_canary":
            ready,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "component_statuses": {
            "visual":
                visual.get(
                    "status"
                ),

            "editorial":
                editorial.get(
                    "status"
                ),

            "subtitle":
                subtitles.get(
                    "status"
                ),

            "audio":
                audio.get(
                    "status"
                ),

            "temporal":
                temporal.get(
                    "status"
                ),

            "guard":
                guard.get(
                    "status"
                ),
        },
    }


    save_json(
        TMP
        / "score.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 HUMAN-LIKE RELEASE SCORE=",
        report[
            "score"
        ],
        "/10"
    )

    print(
        "READY_FOR_FINAL_CANARY=",
        report[
            "ready_for_final_canary"
        ]
    )

    print(
        "BLOCKERS=",
        report[
            "blockers"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )
