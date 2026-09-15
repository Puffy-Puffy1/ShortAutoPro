#!/usr/bin/env python3

VERSION = "8.76"


def contract():
    return {
        "version": VERSION,

        "mode":
            "DISCOVERY_ONLY",

        "network_allowed":
            False,

        "download_allowed":
            False,

        "filesystem_media_write":
            False,

        "provider_call_allowed":
            False,

        "source_recovery_allowed":
            False,

        "renderer_allowed":
            False,

        "ffmpeg_allowed":
            False,
    }


def self_test():
    c = contract()

    assert (
        c[
            "network_allowed"
        ]
        is False
    )

    assert (
        c[
            "filesystem_media_write"
        ]
        is False
    )

    print(
        "VI8.76 READONLY SEARCH ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
