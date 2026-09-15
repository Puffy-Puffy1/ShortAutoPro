#!/usr/bin/env python3

import os

from vi1500_01_common import (
    save_json,
)


def run(
    video,
    run_dir,
):
    old = os.environ.get(
        "VI1400_INPUT_VIDEO"
    )


    os.environ[
        "VI1400_INPUT_VIDEO"
    ] = str(
        video
    )


    try:
        from vi1400_02_artifact_discovery import (
            discover,
        )

        from vi1400_09_temporal_qa import (
            run_temporal,
        )


        discover()

        result = (
            run_temporal()
        )


    except Exception as exc:
        result = {
            "status":
                "HOLD",

            "warnings":
                [],

            "blockers": [
                "temporal_guard_failed"
            ],

            "error":
                str(
                    exc
                ),
        }


    finally:
        if old is None:
            os.environ.pop(
                "VI1400_INPUT_VIDEO",
                None
            )

        else:
            os.environ[
                "VI1400_INPUT_VIDEO"
            ] = old


    save_json(
        run_dir
        / "temporal_qa.json",
        result
    )


    return result
