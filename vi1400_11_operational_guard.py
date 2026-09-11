#!/usr/bin/env python3

import shutil

from pathlib import Path

from vi1400_01_common import (
    ROOT,
    TMP,
    command_exists,
    policy,
    save_json,
    sha256_file,
)


CORE = [
    "video.py",
    "gerar_short.sh",
    "roteiro.py",
    "v6.py",
    "vi6_95_scene_executor.py",
    "vi1000_1_semantic_core.py",
    "vi1000_1_query_gate.py",
    "vi1000_runtime.py",
    "vi1000_command_hook.py",
]


def run():
    config = policy()


    block_mb = int(
        config.get(
            "disk_free_block_mb",
            700
        )
    )


    warning_mb = int(
        config.get(
            "disk_free_warn_mb",
            1500
        )
    )


    usage = shutil.disk_usage(
        ROOT
    )


    free_mb = (
        usage.free
        //
        (
            1024
            *
            1024
        )
    )


    blockers = []

    warnings = []


    if (
        not command_exists(
            "ffmpeg"
        )

        or

        not command_exists(
            "ffprobe"
        )
    ):

        blockers.append(
            "ffmpeg_or_ffprobe_missing"
        )


    if free_mb < block_mb:

        blockers.append(
            "disk_free_below_block_threshold"
        )


    elif free_mb < warning_mb:

        warnings.append(
            "disk_free_below_warning_threshold"
        )


    hashes = {}


    for name in CORE:

        path = (
            ROOT
            / name
        )


        if path.exists():

            hashes[
                name
            ] = (
                sha256_file(
                    path
                )
            )


        else:

            warnings.append(
                "core_optional_missing:"
                + name
            )


    partial_files = [
        str(
            path
        )

        for path
        in ROOT.rglob(
            "*.part"
        )

        if (
            "vi1270_downloads"
            in str(
                path
            )
        )
    ]


    if partial_files:

        warnings.append(
            "partial_download_files_present"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "free_mb":
            free_mb,

        "core_hashes":
            hashes,

        "partial_files":
            partial_files,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        TMP
        / "operational_guard.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 OPERATIONAL GUARD=",
        report[
            "status"
        ]
    )

    print(
        "FREE_MB=",
        report[
            "free_mb"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )

    print(
        "BLOCKERS=",
        report[
            "blockers"
        ]
    )
