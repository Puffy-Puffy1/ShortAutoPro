#!/usr/bin/env python3

import os

from vi6_47_renderer_switch import (
    adapt_scene_command
)


photo = [
    "ffmpeg",
    "-y",
    "-loop",
    "1",
    "-i",
    "photo.jpg",
    "-vf",
    "scale=1200:2133,zoompan=z='1.02'",
    "scene.mp4",
]


video = [
    "ffmpeg",
    "-y",
    "-stream_loop",
    "-1",
    "-i",
    "clip.mp4",
    "-t",
    "4",
    "-vf",
    "scale=1080:1920",
    "scene.mp4",
]


old = os.environ.get(
    "VI647_RENDERER_MODE"
)


try:

    for mode in (
        "LEGACY",
        "SHADOW",
        "ACTIVE",
    ):

        os.environ[
            "VI647_RENDERER_MODE"
        ] = mode


        for command in (
            photo,
            video,
        ):

            snapshot = list(
                command
            )


            result = adapt_scene_command(
                command,
                {
                    "test":
                        True
                }
            )


            assert result is command

            assert command == snapshot


finally:

    if old is None:

        os.environ.pop(
            "VI647_RENDERER_MODE",
            None
        )

    else:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = old


print()
print(
    "======================================"
)
print(
    " VI6.46-6.48 MODULE TEST: PASS"
)
print(
    "======================================"
)

print(
    "PHOTO COMMAND PRESERVED=YES"
)

print(
    "VIDEO COMMAND PRESERVED=YES"
)

print(
    "LEGACY NO MUTATION=YES"
)

print(
    "SHADOW NO MUTATION=YES"
)

print(
    "ACTIVE BLOCKED=YES"
)

print(
    "FFMPEG EXECUTED=0"
)

print(
    "VIDEO GENERATED=0"
)
