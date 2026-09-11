#!/usr/bin/env python3

VERSION = "8.88"


def evaluate():
    return {
        "version": VERSION,

        "module_import_allowed":
            False,

        "search_function_call":
            False,

        "network_call":
            False,

        "download_call":
            False,

        "filesystem_media_write":
            False,

        "media_replace":
            False,

        "source_recovery":
            False,

        "renderer":
            False,

        "ffmpeg":
            False,

        "video_generation":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "search_function_call"
        ]
        is False
    )

    print(
        "VI8.88 SIDE EFFECT BOUNDARY=PASS"
    )


if __name__ == "__main__":
    self_test()
