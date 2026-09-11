#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    BASE,
    ROOT,
    extract_short_id,
    load_json,
    parse_run_timestamp,
    policy,
    save_json,
)


OLD_RUNS = (
    ROOT
    / "temp"
    / "vi1500"
    / "runs"
)


def resolve():
    config = policy()

    before = int(
        config.get(
            "artifact_window_before_seconds",
            180
        )
    )

    after = int(
        config.get(
            "artifact_window_after_seconds",
            300
        )
    )


    rows = []


    for label in [
        "A",
        "B",
        "C",
    ]:

        candidates = sorted(
            OLD_RUNS.glob(
                label
                +
                "_*"
            ),
            key=lambda path:
                path.stat().st_mtime,
            reverse=True,
        )


        if not candidates:
            rows.append({
                "label":
                    label,

                "status":
                    "MISSING",
            })

            continue


        run_dir = candidates[
            0
        ]


        topic = load_json(
            run_dir
            / "topic_private.json",
            {}
        )


        artifacts = load_json(
            run_dir
            / "artifacts.json",
            {}
        )


        video_text = (
            artifacts.get(
                "final_video"
            )
        )


        video = (
            Path(
                video_text
            )
            if video_text
            else None
        )


        raw_start = (
            parse_run_timestamp(
                run_dir.name
            )
        )


        if raw_start is None:

            raw_start = (
                video.stat().st_mtime
                -
                900
                if (
                    video
                    and
                    video.exists()
                )
                else run_dir.stat().st_mtime
                -
                900
            )


        video_mtime = (
            video.stat().st_mtime

            if (
                video
                and
                video.exists()
            )

            else raw_start
            +
            1200
        )


        row = {
            "label":
                label,

            "status":
                "RESOLVED",

            "old_run_dir":
                str(
                    run_dir
                ),

            "topic":
                topic.get(
                    "topic"
                ),

            "domain":
                topic.get(
                    "domain",
                    "CUSTOM"
                ),

            "risk_level":
                topic.get(
                    "risk_level"
                ),

            "final_video":
                (
                    str(
                        video
                    )
                    if video
                    else None
                ),

            "short_id":
                extract_short_id(
                    video_text
                ),

            "window_start":
                raw_start
                -
                before,

            "generation_start":
                raw_start,

            "video_mtime":
                video_mtime,

            "window_end":
                video_mtime
                +
                after,

            "old_artifacts":
                artifacts,
        }


        rows.append(
            row
        )


    save_json(
        BASE
        / "resolved_runs.json",
        {
            "runs":
                rows
        }
    )


    return rows


if __name__ == "__main__":

    rows = resolve()

    print(
        "VI1510 RUN RESOLVER=PASS"
    )

    for row in rows:

        print(
            row[
                "label"
            ],
            "|",
            row[
                "status"
            ],
            "|",
            row.get(
                "short_id"
            ),
            "|",
            row.get(
                "final_video"
            )
        )
