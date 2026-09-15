#!/usr/bin/env python3

from pathlib import Path

from vi1500_01_common import (
    ROOT,
    newest,
    save_json,
)


VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mov",
    ".mkv",
}


def collect(
    start_time,
    run_dir,
):
    videos = []

    metadata = []


    roots = [
        ROOT / "videos",
        ROOT / "temp",
        ROOT / "manifests",
        ROOT / "credits",
        ROOT / "logs",
    ]


    for base in roots:
        if not base.exists():
            continue


        for path in base.rglob(
            "*"
        ):
            if not path.is_file():
                continue


            try:
                mtime = (
                    path.stat().st_mtime
                )

            except Exception:
                continue


            if mtime < (
                start_time
                - 2
            ):
                continue


            suffix = (
                path.suffix.lower()
            )


            if suffix in VIDEO_EXTENSIONS:
                videos.append(
                    path
                )


            elif suffix in {
                ".json",
                ".txt",
                ".ass",
                ".srt",
            }:
                metadata.append(
                    path
                )


    filtered_videos = [
        path

        for path in videos

        if (
            "vi1400"
            not in str(
                path
            ).lower()

            and

            "vi1500"
            not in str(
                path
            ).lower()
        )
    ]


    final_video = newest(
        filtered_videos
        or
        videos
    )


    result = {
        "final_video":
            (
                str(
                    final_video
                )
                if final_video
                else None
            ),

        "new_videos": [
            str(
                path
            )

            for path
            in sorted(
                videos,
                key=lambda p:
                    p.stat().st_mtime
            )
        ],

        "new_metadata": [
            str(
                path
            )

            for path
            in metadata[
                :300
            ]
        ],

        "video_count":
            len(
                videos
            ),
    }


    save_json(
        run_dir
        / "artifacts.json",
        result
    )


    return result
