#!/usr/bin/env python3

from pathlib import Path

from visual_runtime_v42 import (
    note_success,
)


MEDIA_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
}


def wrap_downloader(fn):

    if getattr(
        fn,
        "_vse42_download_guard",
        False,
    ):
        return fn


    def wrapped(*args, **kwargs):

        result = fn(
            *args,
            **kwargs
        )


        ok = False
        destination = None


        if isinstance(
            result,
            tuple,
        ):

            if result:
                ok = bool(result[0])

            if len(result) >= 2:
                destination = result[1]

        else:

            ok = bool(result)


        if (
            ok
            and
            destination
        ):

            dest = Path(
                destination
            )


            if dest.exists():

                for sibling in dest.parent.glob(
                    dest.stem + ".*"
                ):

                    if sibling == dest:
                        continue

                    if (
                        sibling.suffix.casefold()
                        not in MEDIA_SUFFIXES
                    ):
                        continue

                    try:

                        sibling.unlink()

                        print(
                            "VSE42_STALE_SIBLING_REMOVED="
                            + str(sibling)
                        )

                    except Exception:
                        pass


            candidate = (
                args[0]
                if args
                else kwargs.get(
                    "candidato"
                )
            )

            try:
                note_success(
                    candidate,
                    destination,
                )
            except Exception:
                pass


        return result


    wrapped._vse42_download_guard = True

    wrapped.__name__ = getattr(
        fn,
        "__name__",
        "wrapped_downloader",
    )

    return wrapped
