#!/usr/bin/env python3

from vi1500_01_common import (
    load_json,
    save_json,
)


def run(
    run_dir,
):
    score = load_json(
        run_dir
        / "topic_score.json"
    )


    ready = (
        score.get(
            "ready"
        )
        is True
    )


    report = {
        "status":
            (
                "RELEASE_CANDIDATE"
                if ready
                else "SAFE_HOLD"
            ),

        "ready":
            ready,

        "score":
            score.get(
                "score"
            ),

        "blockers":
            score.get(
                "blockers",
                []
            ),

        "publication_executed":
            False,
    }


    save_json(
        run_dir
        / "release_gate.json",
        report
    )


    return report
