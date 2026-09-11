#!/usr/bin/env python3

import os
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"


PROTECTED_SUFFIXES = {
    ".ass",
    ".srt",
    ".vtt",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".json",
    ".txt",
    ".onnx",
}


FINAL_NAMES = (
    "short_v6_{sid}.mp4",
    "short_v5_{sid}.mp4",
    "short_v4_{sid}.mp4",
    "short_v3_{sid}.mp4",
)


def _inside_project(path):

    try:
        resolved = path.resolve()
        root = ROOT.resolve()

        return (
            resolved == root
            or root in resolved.parents
        )

    except Exception:
        return False


def _remove_file(path):

    path = Path(path)

    if not _inside_project(path):
        raise RuntimeError(
            f"unsafe path: {path}"
        )

    if not path.is_file():
        return False

    if path.suffix.casefold() in PROTECTED_SUFFIXES:
        return False

    path.unlink()

    return True


def clean(short_id):

    sid = str(
        short_id or ""
    ).strip()

    if not sid:
        raise RuntimeError(
            "SHORT_ID vazio"
        )

    if (
        "/" in sid
        or "\\" in sid
        or ".." in sid
    ):
        raise RuntimeError(
            "SHORT_ID inseguro"
        )


    removed = []


    videos = (
        ROOT
        / "videos"
    )


    for template in FINAL_NAMES:

        path = (
            videos
            /
            template.format(
                sid=sid
            )
        )

        if _remove_file(path):

            removed.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    temp_dir = (
        ROOT
        / "temp"
        / sid
    )


    if temp_dir.is_dir():

        for path in list(
            temp_dir.iterdir()
        ):

            if not path.is_file():
                continue

            if path.suffix.casefold() != ".mp4":
                continue


            name = path.name


            disposable = (
                name == "video_sem_audio.mp4"
                or name.startswith(
                    "v63_cena_"
                )
                or name.startswith(
                    "cena_"
                )
                or name.startswith(
                    "clip_"
                )
            )


            if not disposable:
                continue


            path.unlink()

            removed.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    return removed


if __name__ == "__main__":

    sid = os.getenv(
        "SHORT_ID",
        "",
    )

    removed = clean(
        sid
    )

    print(
        "FRESH_RENDER_GUARD=PASS"
    )

    print(
        f"REMOVED_COUNT={len(removed)}"
    )

    for item in removed:

        print(
            f"REMOVED={item}"
        )
