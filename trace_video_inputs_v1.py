#!/usr/bin/env python3

import builtins
import os
import runpy
from pathlib import Path


ROOT = str(
    Path.home()
    / "ShortAutoPro"
)


SID = os.environ.get(
    "SHORT_ID",
    "",
)


original_open = (
    builtins.open
)


seen = set()


def traced_open(
    file,
    *args,
    **kwargs,
):

    try:

        path = os.fspath(
            file
        )

        lower = path.lower()

        if (
            SID
            and
            SID in path
            and
            any(
                lower.endswith(ext)
                for ext in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".mp4",
                ]
            )
        ):

            absolute = os.path.abspath(
                path
            )

            if absolute not in seen:

                seen.add(
                    absolute
                )

                print(
                    "RENDER_INPUT_OPEN="
                    +
                    absolute,
                    flush=True,
                )

    except Exception:
        pass


    return original_open(
        file,
        *args,
        **kwargs,
    )


builtins.open = traced_open


try:

    runpy.run_path(
        "video.py",
        run_name="__main__",
    )

finally:

    builtins.open = (
        original_open
    )


print(
    "RENDER_INPUT_OPEN_COUNT=",
    len(seen),
)
