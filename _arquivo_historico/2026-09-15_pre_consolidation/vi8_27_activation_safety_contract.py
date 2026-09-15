#!/usr/bin/env python3

VERSION = "8.27"


def evaluate():
    return {
        "version":
            VERSION,

        "mode":
            "SHADOW_ONLY",

        "automatic_download":
            False,

        "automatic_media_replace":
            False,

        "filesystem_media_mutation":
            False,

        "renderer_activation":
            False,

        "ffmpeg_allowed":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "ffmpeg_allowed"
        ]
        is False
    )

    assert (
        result[
            "automatic_media_replace"
        ]
        is False
    )

    print(
        "VI8.27 ACTIVATION SAFETY CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
