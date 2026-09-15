#!/usr/bin/env python3

from pathlib import Path

from vi1400_01_common import (
    TMP,
    load_json,
    save_json,
    sha256_file,
)


def run():
    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    video = Path(
        artifacts[
            "final_video"
        ]
    )


    report = {
        "version":
            "1400.00",

        "source_video":
            str(
                video
            ),

        "source_sha256":
            sha256_file(
                video
            ),

        "score":
            load_json(
                TMP
                / "score.json"
            ),

        "visual_qa":
            load_json(
                TMP
                / "visual_qa.json"
            ),

        "editorial_qa":
            load_json(
                TMP
                / "editorial_qa.json"
            ),

        "subtitle_qa":
            load_json(
                TMP
                / "subtitle_qa.json"
            ),

        "audio_qa":
            load_json(
                TMP
                / "audio_qa.json"
            ),

        "temporal_qa":
            load_json(
                TMP
                / "temporal_qa.json"
            ),

        "rescue_plan":
            load_json(
                TMP
                / "rescue_plan.json"
            ),

        "operational_guard":
            load_json(
                TMP
                / "operational_guard.json"
            ),

        "publication_pack":
            load_json(
                TMP
                / "publication_pack.json"
            ),

        "production_mutated":
            False,

        "publication_executed":
            False,
    }


    save_json(
        TMP
        / "release_manifest.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 RELEASE MANIFEST=PASS"
    )

    print(
        "SOURCE_SHA256=",
        report[
            "source_sha256"
        ]
    )
