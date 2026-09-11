#!/usr/bin/env python3

import struct

from pathlib import Path

VERSION = "8.34"


def png_dimensions(path):

    with open(
        path,
        "rb"
    ) as f:

        header = f.read(
            24
        )

    if (
        len(header) >= 24
        and header[:8]
        == b"\x89PNG\r\n\x1a\n"
    ):

        width, height = (
            struct.unpack(
                ">II",
                header[16:24]
            )
        )

        return width, height

    return None


def jpeg_dimensions(path):

    with open(
        path,
        "rb"
    ) as f:

        data = f.read(
            2
        )

        if data != b"\xff\xd8":
            return None

        while True:

            byte = f.read(
                1
            )

            if not byte:
                break

            if byte != b"\xff":
                continue

            while byte == b"\xff":
                byte = f.read(
                    1
                )

            marker = byte[0]

            length_raw = f.read(
                2
            )

            if len(
                length_raw
            ) != 2:
                break

            length = struct.unpack(
                ">H",
                length_raw
            )[0]

            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:

                payload = f.read(
                    5
                )

                if len(
                    payload
                ) != 5:
                    return None

                height, width = (
                    struct.unpack(
                        ">HH",
                        payload[1:5]
                    )
                )

                return width, height

            f.seek(
                max(
                    0,
                    length - 2
                ),
                1
            )

    return None


def webp_dimensions(path):

    try:

        from PIL import Image

        with Image.open(
            path
        ) as img:

            return img.size

    except Exception:

        return None


def dimensions(path):

    p = Path(path)

    suffix = (
        p.suffix.lower()
    )

    try:

        if suffix == ".png":
            return png_dimensions(
                p
            )

        if suffix in {
            ".jpg",
            ".jpeg",
        }:

            return jpeg_dimensions(
                p
            )

        if suffix == ".webp":
            return webp_dimensions(
                p
            )

    except Exception:

        return None

    return None


def self_test():

    assert dimensions(
        "/definitely/not/here.jpg"
    ) is None

    print(
        "VI8.34 IMAGE DIMENSION READER=PASS"
    )


if __name__ == "__main__":
    self_test()
