#!/usr/bin/env python3

import argparse
import time

from pathlib import Path

from vi1500_01_common import (
    BASE,
    RUNS,
    load_json,
    save_json,
    safe_name,
    timestamp,
)

from vi1500_04_blind_controller import (
    build,
)

from vi1500_05_runtime_snapshot import (
    create_core_backup,
    filesystem_snapshot,
    verify_and_restore_core,
)

from vi1500_07_artifact_collector import (
    collect,
)

from vi1500_08_freshness_guard import (
    inspect as freshness_inspect,
)

from vi1500_09_semantic_leak_guard import (
    run as leak_run,
)

from vi1500_10_source_audit import (
    run as source_run,
)

from vi1500_11_visual_bridge import (
    run as visual_run,
)

from vi1500_12_audio_subtitle_bridge import (
    run as audio_run,
)

from vi1500_13_temporal_guard import (
    run as temporal_run,
)

from vi1500_14_resource_guard import (
    run as resource_run,
)

from vi1500_16_retry_controller import (
    run_with_retry,
)

from vi1500_17_topic_score import (
    run as score_run,
)

from vi1500_18_release_gate import (
    run as gate_run,
)

from vi1500_19_repro_manifest import (
    run as repro_run,
)


def process_topic(
    topic_record,
):
    label = topic_record[
        "label"
    ]

    topic = topic_record[
        "topic"
    ]


    run_id = (
        "VI1500_"
        +
        label
        +
        "_"
        +
        timestamp()
    )


    run_dir = (
        RUNS
        /
        (
            label
            +
            "_"
            +
            timestamp()
        )
    )


    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    save_json(
        run_dir
        / "topic_private.json",
        topic_record
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1500 TOPIC",
        label
    )

    print(
        "=============================================="
    )

    print(
        "DOMAIN:",
        topic_record[
            "domain"
        ]
    )

    print(
        "RISK:",
        topic_record[
            "risk_level"
        ]
    )

    print(
        "TOPIC:",
        topic
    )


    resource = resource_run(
        run_dir
    )


    if resource[
        "status"
    ] != "PASS":

        generation = {
            "status":
                "BLOCKED_BY_RESOURCE_GUARD",

            "returncode":
                0,
        }


        save_json(
            run_dir
            / "generation.json",
            generation
        )


        artifacts = {
            "final_video":
                None,

            "new_videos":
                [],

            "new_metadata":
                [],
        }


        save_json(
            run_dir
            / "artifacts.json",
            artifacts
        )


    else:
        before = filesystem_snapshot()

        start_time = time.time()


        generation = run_with_retry(
            topic,
            run_id,
            run_dir,
        )


        save_json(
            run_dir
            / "generation.json",
            generation
        )


        artifacts = collect(
            start_time,
            run_dir,
        )


    core = verify_and_restore_core()


    save_json(
        run_dir
        / "core_integrity.json",
        core
    )


    if core[
        "changed"
    ]:

        print(
            "CORE MUTATION DETECTED:",
            core[
                "changed"
            ]
        )

        print(
            "CORE RESTORED:",
            core[
                "restored"
            ]
        )


    freshness = freshness_inspect(
        topic,
        artifacts,
        run_dir,
    )


    leak = leak_run(
        topic,
        artifacts,
        run_dir,
    )


    start_for_source = (
        start_time

        if "start_time"
        in locals()

        else time.time()
    )


    source = source_run(
        start_for_source,
        run_dir,
    )


    video = artifacts.get(
        "final_video"
    )


    if video:
        visual = visual_run(
            video,
            run_dir,
        )


        audio = audio_run(
            start_for_source,
            run_dir,
        )


        temporal = temporal_run(
            video,
            run_dir,
        )


    else:
        visual = {
            "status":
                "HOLD",

            "average_strength":
                0,

            "warnings":
                [],

            "blockers": [
                "video_missing"
            ],
        }


        audio = {
            "status":
                "HOLD",

            "warnings":
                [],

            "blockers": [
                "video_missing"
            ],
        }


        temporal = {
            "status":
                "HOLD",

            "warnings":
                [],

            "blockers": [
                "video_missing"
            ],
        }


        save_json(
            run_dir
            / "visual_qa.json",
            visual
        )


        save_json(
            run_dir
            / "audio_subtitle_qa.json",
            audio
        )


        save_json(
            run_dir
            / "temporal_qa.json",
            temporal
        )


    score = score_run(
        run_dir
    )


    if core[
        "changed"
    ]:
        score[
            "ready"
        ] = False

        score[
            "blockers"
        ] = sorted(
            set(
                score.get(
                    "blockers",
                    []
                )
                +
                [
                    "core_mutation_detected_and_restored"
                ]
            )
        )


        save_json(
            run_dir
            / "topic_score.json",
            score
        )


    gate = gate_run(
        run_dir
    )


    repro_run(
        run_dir
    )


    print()
    print(
        "TOPIC",
        label,
        "SCORE=",
        score[
            "score"
        ]
    )

    print(
        "TOPIC",
        label,
        "RESULT=",
        gate[
            "status"
        ]
    )

    print(
        "BLOCKERS=",
        gate[
            "blockers"
        ]
    )

    print(
        "CORE_CHANGED=",
        core[
            "changed"
        ]
    )

    print(
        "FINAL_VIDEO=",
        artifacts.get(
            "final_video"
        )
    )


    return {
        "label":
            label,

        "run_dir":
            str(
                run_dir
            ),

        "result":
            gate[
                "status"
            ],

        "score":
            score[
                "score"
            ],
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--all",
        action="store_true"
    )

    parser.add_argument(
        "--label"
    )

    args = parser.parse_args()


    create_core_backup()

    queue = build()


    selected = queue


    if args.label:
        selected = [
            item

            for item in queue

            if item[
                "label"
            ]
            ==
            args.label
        ]


    results = []


    for item in selected:
        results.append(
            process_topic(
                item
            )
        )


    save_json(
        BASE
        / "topic_runner_results.json",
        {
            "results":
                results
        }
    )


    print()
    print(
        "VI1500 TOPIC RUNNER COMPLETED"
    )

    print(
        "TOPICS=",
        len(
            results
        )
    )


if __name__ == "__main__":
    main()
