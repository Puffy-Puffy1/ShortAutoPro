#!/usr/bin/env python3

from vi1510_01_common import (
    save_json,
)


def run(
    score,
    run_dir,
):
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

        "production_mutated":
            False,
    }


    save_json(
        run_dir
        / "release_gate_v2.json",
        report
    )


    return report
