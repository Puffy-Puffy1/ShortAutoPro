#!/usr/bin/env python3

from vi1500_01_common import (
    load_json,
    policy,
    save_json,
)


def run(
    run_dir,
):
    generator = load_json(
        run_dir
        / "generation.json"
    )

    artifacts = load_json(
        run_dir
        / "artifacts.json"
    )

    freshness = load_json(
        run_dir
        / "freshness_guard.json"
    )

    leak = load_json(
        run_dir
        / "semantic_leak_guard.json"
    )

    source = load_json(
        run_dir
        / "source_audit.json"
    )

    visual = load_json(
        run_dir
        / "visual_qa.json"
    )

    audio = load_json(
        run_dir
        / "audio_subtitle_qa.json"
    )

    temporal = load_json(
        run_dir
        / "temporal_qa.json"
    )

    resource = load_json(
        run_dir
        / "resource_guard.json"
    )


    blockers = []


    for component in [
        freshness,
        leak,
        source,
        visual,
        audio,
        temporal,
        resource,
    ]:
        blockers.extend(
            component.get(
                "blockers",
                []
            )
        )


    generated = bool(
        artifacts.get(
            "final_video"
        )
    )


    if not generated:
        blockers.append(
            "final_video_missing"
        )


    score = 0.0


    if generated:
        score += 1.5


    if freshness.get(
        "status"
    ) == "PASS":
        score += 1.0


    if leak.get(
        "status"
    ) == "PASS":
        score += 1.5


    if source.get(
        "status"
    ) == "PASS":
        score += 2.0


    visual_average = float(
        visual.get(
            "average_strength"
        )
        or 0
    )


    score += (
        min(
            10,
            visual_average
        )
        /
        10
    ) * 1.5


    if audio.get(
        "status"
    ) == "PASS":
        score += 1.0


    if temporal.get(
        "status"
    ) == "PASS":
        score += 1.0


    if resource.get(
        "status"
    ) == "PASS":
        score += 0.5


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

        "generated":
            generated,

        "visual_average":
            visual_average,

        "ready":
            ready,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }


    save_json(
        run_dir
        / "topic_score.json",
        report
    )


    return report
