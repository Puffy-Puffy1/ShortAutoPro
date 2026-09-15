#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    ffprobe,
    save_json,
)


def magic_kind(
    path,
):
    try:

        with Path(
            path
        ).open(
            "rb"
        ) as handle:

            head = handle.read(
                16
            )

    except Exception:
        return "UNREADABLE"


    if head.startswith(
        b"\xff\xd8\xff"
    ):
        return "JPEG"


    if head.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return "PNG"


    if (
        len(
            head
        ) >= 12

        and

        head[
            :4
        ]
        ==
        b"RIFF"

        and

        head[
            8:12
        ]
        ==
        b"WEBP"
    ):
        return "WEBP"


    if head.startswith(
        b"%PDF-"
    ):
        return "PDF"


    if head.startswith(
        b"\x1aE\xdf\xa3"
    ):
        return "WEBM"


    if (
        len(
            head
        ) >= 12

        and

        head[
            4:8
        ]
        ==
        b"ftyp"
    ):
        return "MP4"


    if head.startswith(
        (
            b"II*\x00",
            b"MM\x00*",
        )
    ):
        return "TIFF"


    return "UNKNOWN"


def run(
    inventory,
    run_dir,
):
    rows = []

    blockers = []

    warnings = []


    for asset in inventory.get(
        "source_assets",
        []
    ):

        path = Path(
            asset[
                "path"
            ]
        )


        kind = magic_kind(
            path
        )


        valid = (
            kind
            not in {
                "UNREADABLE",
                "UNKNOWN",
            }
        )


        probe = {}


        if kind in {
            "JPEG",
            "PNG",
            "WEBP",
            "TIFF",
            "WEBM",
            "MP4",
        }:

            probe = ffprobe(
                path
            )


            if not probe:
                valid = False


        if path.stat().st_size < 1024:

            valid = False


        if not valid:

            blockers.append(
                (
                    "invalid_asset:"
                    +
                    path.name
                )
            )


        rows.append({
            "path":
                str(
                    path
                ),

            "magic_kind":
                kind,

            "bytes":
                path.stat().st_size,

            "valid":
                valid,

            "probe":
                probe,
        })


    if not rows:

        blockers.append(
            "no_source_assets_for_technical_audit"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "assets":
            rows,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "asset_technical_audit.json",
        report
    )


    return report
