#!/usr/bin/env python3

from vi1400_01_common import (
    TMP,
    load_json,
    save_json,
)


def run():
    score = load_json(
        TMP
        / "score.json"
    )


    architecture = load_json(
        TMP
        / "architecture.json"
    )


    ready = (
        bool(
            score.get(
                "ready_for_final_canary"
            )
        )

        and

        architecture.get(
            "status"
        )
        ==
        "VI1400_ARCHITECTURE_CERTIFIED"
    )


    result = {
        "status":
            (
                "VI1400_RELEASE_GATE_CERTIFIED"

                if ready

                else

                "VI1400_RELEASE_GATE_HOLD"
            ),

        "ready":
            ready,

        "score":
            score.get(
                "score"
            ),

        "blockers":
            (
                score.get(
                    "blockers",
                    []
                )
                +
                architecture.get(
                    "blockers",
                    []
                )
            ),
    }


    save_json(
        TMP
        / "release_gate.json",
        result
    )


    return result


if __name__ == "__main__":

    result = run()


    print(
        "STATUS:",
        result[
            "status"
        ]
    )

    print(
        "READY=",
        result[
            "ready"
        ]
    )

    print(
        "SCORE=",
        result[
            "score"
        ]
    )

    print(
        "BLOCKERS=",
        result[
            "blockers"
        ]
    )


    raise SystemExit(
        0
        if result[
            "ready"
        ]
        else 2
    )
