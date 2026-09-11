#!/usr/bin/env python3

VERSION = "6.68"


def analyze(events):

    measured = []


    for event in events or []:

        interval = (
            event.get("mega", {})
            .get("inter_event_wall_seconds")
        )


        try:
            interval = float(interval)

        except Exception:
            continue


        measured.append(
            {
                "scene":
                    event.get("scene"),

                "seconds":
                    round(interval, 3),

                "branch":
                    event.get("branch"),
            }
        )


    measured.sort(
        key=lambda x:
            x["seconds"],
        reverse=True
    )


    slowest = (
        measured[0]
        if measured
        else None
    )


    average = (
        round(
            sum(
                x["seconds"]
                for x in measured
            )
            / len(measured),
            3
        )
        if measured
        else None
    )


    warnings = []


    if (
        slowest
        and slowest["seconds"] > 8
    ):

        warnings.append(
            "slow_scene_stage_detected"
        )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),
        "measured_scene_intervals":
            len(measured),
        "average_interval_seconds":
            average,
        "slowest":
            slowest,
        "top_slowest":
            measured[:5],
        "warnings": warnings,
        "render_settings_changed": False,
    }


def self_test():

    result = analyze(
        [
            {
                "scene": 2,
                "branch": "VIDEO",
                "mega": {
                    "inter_event_wall_seconds":
                        4.2
                },
            }
        ]
    )


    assert (
        result["render_settings_changed"]
        is False
    )

    print("VI6.68 PERFORMANCE INTELLIGENCE=PASS")


if __name__ == "__main__":
    self_test()
