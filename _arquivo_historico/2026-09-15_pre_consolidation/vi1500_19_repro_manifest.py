#!/usr/bin/env python3

from pathlib import Path

from vi1500_01_common import (
    load_json,
    save_json,
    sha256_file,
)


FILES = [
    "generation.json",
    "artifacts.json",
    "freshness_guard.json",
    "semantic_leak_guard.json",
    "source_audit.json",
    "visual_qa.json",
    "audio_subtitle_qa.json",
    "temporal_qa.json",
    "resource_guard.json",
    "topic_score.json",
    "release_gate.json",
]


def run(
    run_dir,
):
    artifacts = load_json(
        run_dir
        / "artifacts.json"
    )


    video = artifacts.get(
        "final_video"
    )


    hashes = {}


    for name in FILES:
        path = (
            run_dir
            / name
        )

        if path.exists():
            hashes[
                name
            ] = sha256_file(
                path
            )


    report = {
        "report_hashes":
            hashes,

        "video":
            video,

        "video_sha256":
            (
                sha256_file(
                    video
                )
                if (
                    video
                    and
                    Path(
                        video
                    ).exists()
                )
                else None
            ),

        "publication_executed":
            False,

        "production_core_mutated":
            False,
    }


    save_json(
        run_dir
        / "repro_manifest.json",
        report
    )


    return report
