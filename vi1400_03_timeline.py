#!/usr/bin/env python3

from pathlib import Path

from vi1400_01_common import (
    TMP,
    duration,
    load_json,
    save_json,
)


def build_timeline(
    artifacts=None,
):
    artifacts = (
        artifacts

        or

        load_json(
            TMP
            / "artifacts.json"
        )
    )


    final = Path(
        artifacts[
            "final_video"
        ]
    )


    final_duration = (
        duration(
            final
        )
    )


    clips = (
        artifacts.get(
            "scene_clips"
        )
        or {}
    )


    timeline = []

    current = 0.0


    if len(
        clips
    ) == 12:

        for number in range(
            1,
            13
        ):

            scene_duration = max(
                0.05,
                duration(
                    clips[
                        str(
                            number
                        )
                    ]
                ),
            )


            timeline.append({
                "scene":
                    number,

                "start":
                    round(
                        current,
                        3
                    ),

                "end":
                    round(
                        min(
                            final_duration,
                            current
                            + scene_duration
                        ),
                        3
                    ),

                "duration":
                    round(
                        scene_duration,
                        3
                    ),

                "source":
                    "scene_clip",
            })


            current += (
                scene_duration
            )


        if abs(
            current
            -
            final_duration
        ) > 0.75:

            scale = (
                final_duration
                /
                max(
                    current,
                    0.001
                )
            )


            current = 0.0


            for item in timeline:

                scene_duration = (
                    item[
                        "duration"
                    ]
                    *
                    scale
                )


                item[
                    "start"
                ] = round(
                    current,
                    3
                )


                item[
                    "end"
                ] = round(
                    current
                    +
                    scene_duration,
                    3
                )


                item[
                    "duration"
                ] = round(
                    scene_duration,
                    3
                )


                item[
                    "source"
                ] = (
                    "scene_clip_scaled"
                )


                current += (
                    scene_duration
                )


    else:

        scene_duration = (
            final_duration
            /
            12.0
        )


        timeline = [
            {
                "scene":
                    number,

                "start":
                    round(
                        (
                            number
                            - 1
                        )
                        *
                        scene_duration,
                        3
                    ),

                "end":
                    round(
                        (
                            number
                            *
                            scene_duration
                        )
                        if number < 12
                        else final_duration,
                        3
                    ),

                "duration":
                    round(
                        scene_duration,
                        3
                    ),

                "source":
                    "equal_fallback",
            }

            for number
            in range(
                1,
                13
            )
        ]


    save_json(
        TMP
        / "timeline.json",
        {
            "duration":
                final_duration,

            "timeline":
                timeline,

            "exact_scene_clips":
                len(
                    clips
                )
                == 12,
        }
    )


    return timeline


if __name__ == "__main__":

    timeline = (
        build_timeline()
    )


    print(
        "VI1400 TIMELINE=PASS"
    )

    print(
        "SCENES=",
        len(
            timeline
        )
    )

    print(
        "MODE=",
        timeline[
            0
        ][
            "source"
        ]
    )
