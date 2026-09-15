#!/usr/bin/env python3

from vi1510_01_common import (
    load_json,
    save_json,
)


def run(
    video,
    old_run_dir,
    run_dir,
):
    old = load_json(
        old_run_dir
        / "visual_qa.json",
        {}
    )


    try:

        from vi1500_11_visual_bridge import (
            run as bridge_run,
        )


        fresh = bridge_run(
            video,
            run_dir,
        )


        report = {
            **fresh,

            "source":
                "VI1400_REAUDIT",
        }


    except Exception as exc:

        if old:

            report = {
                **old,

                "source":
                    "VI1500_EXISTING_QA",

                "bridge_warning":
                    str(
                        exc
                    ),
            }

        else:

            report = {
                "status":
                    "HOLD",

                "average_strength":
                    0,

                "warnings":
                    [],

                "blockers": [
                    "visual_qa_unavailable"
                ],

                "error":
                    str(
                        exc
                    ),
            }


    save_json(
        run_dir
        / "visual_qa.json",
        report
    )


    return report
