#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import os
import re


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

SID_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_\d{4}$"
)


def valid(value):

    return bool(
        value
        and
        SID_RE.fullmatch(
            str(value).strip()
        )
    )


def parse_sid(value):

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d_%H%M",
        )

    except Exception:

        return datetime.min


def collect():

    evidence = {}


    def add(
        sid,
        source,
    ):

        if not valid(sid):
            return

        evidence.setdefault(
            sid,
            set(),
        ).add(
            source
        )


    # imagens/short_ID
    media_root = (
        ROOT
        / "imagens"
    )

    if media_root.is_dir():

        for path in media_root.glob(
            "short_*"
        ):

            if not path.is_dir():
                continue

            add(
                path.name[
                    len("short_"):
                ],
                "media",
            )


    # temp/ID
    temp_root = (
        ROOT
        / "temp"
    )

    if temp_root.is_dir():

        for path in temp_root.iterdir():

            if path.is_dir():

                add(
                    path.name,
                    "temp",
                )


    # audios/short_ID.mp3
    audio_root = (
        ROOT
        / "audios"
    )

    if audio_root.is_dir():

        for path in audio_root.glob(
            "short_*.mp3"
        ):

            add(
                path.stem[
                    len("short_"):
                ],
                "audio",
            )


    # roteiros
    roteiro_root = (
        ROOT
        / "roteiros"
    )

    if roteiro_root.is_dir():

        patterns = (
            "short_*.txt",
            "topic_*.txt",
            "scene_map_*.json",
        )

        for pattern in patterns:

            for path in roteiro_root.glob(
                pattern
            ):

                name = path.stem

                for prefix in (
                    "short_",
                    "topic_",
                    "scene_map_",
                ):

                    if name.startswith(
                        prefix
                    ):

                        add(
                            name[
                                len(prefix):
                            ],
                            "roteiro",
                        )


    # final videos
    video_root = (
        ROOT
        / "videos"
    )

    if video_root.is_dir():

        for path in video_root.glob(
            "short_v6_*.mp4"
        ):

            add(
                path.stem[
                    len("short_v6_"):
                ],
                "final",
            )


    return evidence


def resolve_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if valid(env):
        return env


    evidence = collect()

    if not evidence:
        return ""


    # Prefer IDs com pelo menos duas evidências,
    # depois o mais recente.
    ranked = sorted(
        evidence.items(),
        key=lambda item: (
            len(
                item[1]
            ),
            parse_sid(
                item[0]
            ),
        ),
        reverse=True,
    )


    strong = [
        item
        for item in ranked
        if len(
            item[1]
        ) >= 2
    ]


    if strong:

        strong.sort(
            key=lambda item:
                parse_sid(
                    item[0]
                ),
            reverse=True,
        )

        return strong[0][0]


    ranked.sort(
        key=lambda item:
            parse_sid(
                item[0]
            ),
        reverse=True,
    )

    return ranked[0][0]


if __name__ == "__main__":

    sid = resolve_short_id()

    if sid:
        print(sid)
    else:
        print("")
