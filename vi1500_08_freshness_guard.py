#!/usr/bin/env python3

from pathlib import Path

from vi1500_01_common import (
    policy,
    save_json,
)


def inspect(
    topic,
    artifacts,
    run_dir,
):
    config = policy()

    forbidden = [
        str(
            value
        ).lower()

        for value in config.get(
            "old_benchmark_forbidden",
            []
        )
    ]


    corpus = [
        topic.lower()
    ]


    paths = (
        artifacts.get(
            "new_metadata",
            []
        )
        +
        [
            str(
                run_dir
                / "generator_stdout.txt"
            ),

            str(
                run_dir
                / "generator_stderr.txt"
            ),
        ]
    )


    if artifacts.get(
        "final_video"
    ):
        corpus.append(
            artifacts[
                "final_video"
            ].lower()
        )


    for path_text in paths:
        path = Path(
            path_text
        )


        if (
            not path.exists()
            or
            path.suffix.lower()
            not in {
                ".json",
                ".txt",
                ".ass",
                ".srt",
            }
        ):
            continue


        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            corpus.append(
                text.lower()
            )

        except Exception:
            pass


    joined = "\n".join(
        corpus
    )


    contamination = [
        value

        for value in forbidden

        if value in joined
    ]


    # The benchmark name inside topic itself is ignored
    # only if user intentionally supplied it.
    contamination = [
        value

        for value in contamination

        if value not in topic.lower()
    ]


    report = {
        "status":
            (
                "PASS"
                if not contamination
                else "HOLD"
            ),

        "fresh_topic":
            True,

        "old_benchmark_contamination":
            contamination,

        "blockers": [
            (
                "old_benchmark_leak:"
                + value
            )

            for value
            in contamination
        ],
    }


    save_json(
        run_dir
        / "freshness_guard.json",
        report
    )


    return report
