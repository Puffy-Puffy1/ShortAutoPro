#!/usr/bin/env python3

import os
import shutil

from pathlib import Path

from vi1500_01_common import (
    ROOT,
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

        from vi1400_03_timeline import (
            build_timeline,
        )

        from vi1400_04_frame_metrics import (
            analyze,
        )

        from vi1400_06_visual_qa import (
            run as visual_run,
        )


        discover()

        build_timeline()

        metrics = analyze()

        visual = visual_run()


        result = {
            "status":
                visual.get(
                    "status",
                    "HOLD"
                ),

            "average_strength":
                visual.get(
                    "average_strength"
                ),

            "warnings":
                visual.get(
                    "warnings",
                    []
                ),

            "blockers":
                visual.get(
                    "blockers",
                    []
                ),

            "scenes":
                metrics,
        }


    except Exception as exc:
        result = {
            "status":
                "HOLD",

            "average_strength":
                0,

            "warnings":
                [],

            "blockers": [
                (
                    "vi1400_visual_bridge_failed:"
                    +
                    type(
                        exc
                    ).__name__
                )
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
        / "visual_qa.json",
        result
    )


    return result
