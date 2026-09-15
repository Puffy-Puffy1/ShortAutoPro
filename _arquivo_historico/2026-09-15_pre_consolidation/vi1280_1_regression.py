#!/usr/bin/env python3

import tempfile

from pathlib import Path


from vi1280_00_asset_forensics import (
    MAGIC_JPEG,
    MAGIC_PNG,
    MAGIC_WEBM,
    magic_kind,
)


def temporary_file(
    payload
):
    handle = tempfile.NamedTemporaryFile(
        delete=False
    )

    handle.write(
        payload
    )

    handle.close()

    return Path(
        handle.name
    )


def main():
    tests = [
        (
            "JPEG_MAGIC",
            MAGIC_JPEG
            + bytes(
                64
            ),
            "JPEG",
        ),

        (
            "PNG_MAGIC",
            MAGIC_PNG
            + bytes(
                64
            ),
            "PNG",
        ),

        (
            "WEBM_MAGIC",
            MAGIC_WEBM
            + bytes(
                64
            ),
            "WEBM",
        ),

        (
            "PDF_MAGIC",
            b"%PDF-1.7\n"
            + bytes(
                64
            ),
            "PDF",
        ),

        (
            "WEBP_MAGIC",
            b"RIFF"
            + bytes.fromhex(
                "10000000"
            )
            + b"WEBP"
            + b"VP8X"
            + bytes(
                32
            ),
            "WEBP",
        ),

        (
            "MP4_MAGIC",
            bytes.fromhex(
                "00000018"
            )
            + b"ftyp"
            + b"isom"
            + bytes(
                32
            ),
            "MP4",
        ),
    ]


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1280.1 MAGIC SIGNATURE REGRESSION"
    )

    print(
        "=============================================="
    )


    paths = []


    try:

        for (
            name,
            payload,
            expected,
        ) in tests:

            path = temporary_file(
                payload
            )

            paths.append(
                path
            )


            actual = magic_kind(
                path
            )


            passed = (
                actual
                ==
                expected
            )


            print(
                name,
                "=",
                (
                    "PASS"
                    if passed
                    else "FAIL"
                ),
                "| expected=",
                expected,
                "| actual=",
                actual
            )


            if not passed:

                failed.append(
                    name
                )


    finally:

        for path in paths:

            path.unlink(
                missing_ok=True
            )


    print(
        "FAILED:",
        failed
    )


    if failed:

        raise SystemExit(
            1
        )


    print(
        "VI1280_1_MAGIC_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
