#!/usr/bin/env python3

import hashlib
import json
import struct
import urllib.parse

from pathlib import Path


from vi1000_1_query_gate import (
    license_allowed,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

ROOT = (
    BASE
    / "temp/vi1270_downloads"
)

ASSET_ROOT = (
    ROOT
    / "assets"
)

MANIFEST = (
    ROOT
    / "download_manifest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1280_00_asset_forensics_latest.json"
)


ALLOWED_HOSTS = {
    "upload.wikimedia.org",
    "commons.wikimedia.org",
    "archive.org",
}


MAGIC_JPEG = bytes.fromhex(
    "FFD8FF"
)

MAGIC_JPEG_SOI = bytes.fromhex(
    "FFD8"
)

MAGIC_PNG = bytes.fromhex(
    "89504E470D0A1A0A"
)

MAGIC_WEBM = bytes.fromhex(
    "1A45DFA3"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256_file(
    path
):
    sha = hashlib.sha256()


    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024
                * 1024
            )


            if not chunk:
                break


            sha.update(
                chunk
            )


    return sha.hexdigest()


def magic_kind(
    path
):
    with path.open(
        "rb"
    ) as handle:

        head = handle.read(
            64
        )


    if head.startswith(
        MAGIC_JPEG
    ):
        return "JPEG"


    if head.startswith(
        MAGIC_PNG
    ):
        return "PNG"


    if (
        len(head) >= 12
        and
        head[:4] == b"RIFF"
        and
        head[8:12] == b"WEBP"
    ):
        return "WEBP"


    if head.startswith(
        b"%PDF-"
    ):
        return "PDF"


    if head.startswith(
        MAGIC_WEBM
    ):
        return "WEBM"


    if (
        len(head) >= 12
        and
        head[4:8] == b"ftyp"
    ):
        return "MP4"


    return "UNKNOWN"


def expected_kind(
    content_type
):
    mapping = {
        "image/jpeg":
            "JPEG",

        "image/png":
            "PNG",

        "image/webp":
            "WEBP",

        "video/webm":
            "WEBM",

        "video/mp4":
            "MP4",

        "application/pdf":
            "PDF",
    }


    return mapping.get(
        str(
            content_type
            or ""
        )
        .split(
            ";",
            1
        )[0]
        .strip()
        .lower()
    )


def jpeg_dimensions(
    path
):
    sof = {
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
    }


    with path.open(
        "rb"
    ) as handle:

        if handle.read(
            2
        ) != MAGIC_JPEG_SOI:

            return None


        while True:

            byte = handle.read(
                1
            )


            if not byte:
                return None


            if byte != b"\xff":
                continue


            while byte == b"\xff":

                marker_raw = handle.read(
                    1
                )


                if not marker_raw:
                    return None


                if marker_raw != b"\xff":
                    break


            marker = marker_raw[0]


            if marker in {
                0xD8,
                0xD9,
            }:
                continue


            if marker == 0xDA:
                return None


            length_raw = handle.read(
                2
            )


            if len(
                length_raw
            ) != 2:
                return None


            length = struct.unpack(
                ">H",
                length_raw
            )[0]


            if length < 2:
                return None


            if marker in sof:

                data = handle.read(
                    5
                )


                if len(
                    data
                ) != 5:
                    return None


                height = struct.unpack(
                    ">H",
                    data[
                        1:3
                    ]
                )[0]

                width = struct.unpack(
                    ">H",
                    data[
                        3:5
                    ]
                )[0]


                if (
                    width <= 0
                    or
                    height <= 0
                ):
                    return None


                return {
                    "width":
                        width,

                    "height":
                        height,
                }


            handle.seek(
                length - 2,
                1
            )


def png_dimensions(
    path
):
    with path.open(
        "rb"
    ) as handle:

        head = handle.read(
            24
        )


    if (
        len(
            head
        )
        < 24
        or
        not head.startswith(
            MAGIC_PNG
        )
        or
        head[
            12:16
        ] != b"IHDR"
    ):
        return None


    width = struct.unpack(
        ">I",
        head[
            16:20
        ]
    )[0]

    height = struct.unpack(
        ">I",
        head[
            20:24
        ]
    )[0]


    if (
        width <= 0
        or
        height <= 0
    ):
        return None


    return {
        "width":
            width,

        "height":
            height,
    }


def webp_dimensions(
    path
):
    with path.open(
        "rb"
    ) as handle:

        head = handle.read(
            32
        )


    if (
        len(
            head
        )
        < 16
        or
        head[
            :4
        ] != b"RIFF"
        or
        head[
            8:12
        ] != b"WEBP"
    ):
        return None


    chunk = head[
        12:16
    ]


    if (
        chunk == b"VP8X"
        and
        len(
            head
        )
        >= 30
    ):

        width = (
            1
            +
            int.from_bytes(
                head[
                    24:27
                ],
                "little"
            )
        )

        height = (
            1
            +
            int.from_bytes(
                head[
                    27:30
                ],
                "little"
            )
        )


        return {
            "width":
                width,

            "height":
                height,
        }


    return None


def dimensions(
    path,
    kind
):
    if kind == "JPEG":

        return jpeg_dimensions(
            path
        )


    if kind == "PNG":

        return png_dimensions(
            path
        )


    if kind == "WEBP":

        return webp_dimensions(
            path
        )


    return None


def pdf_integrity(
    path
):
    try:

        size = path.stat().st_size


        if size < 128:

            return False


        with path.open(
            "rb"
        ) as handle:

            header = handle.read(
                8
            )


            seek_back = min(
                size,
                8192
            )


            handle.seek(
                -seek_back,
                2
            )


            tail = handle.read()


        return (
            header.startswith(
                b"%PDF-"
            )
            and
            b"%%EOF"
            in tail
        )


    except Exception:

        return False


def host_allowed(
    url
):
    if not url:
        return False


    hostname = str(
        urllib.parse.urlparse(
            url
        ).hostname
        or ""
    ).lower()


    if hostname in ALLOWED_HOSTS:

        return True


    if hostname.endswith(
        ".archive.org"
    ):

        return True


    return False


def path_inside_asset_root(
    path
):
    try:

        path.resolve().relative_to(
            ASSET_ROOT.resolve()
        )

        return True


    except Exception:

        return False


def asset_record_matches_scene(
    scene_asset,
    source_assets
):
    if not isinstance(
        scene_asset,
        dict
    ):
        return False


    group = scene_asset.get(
        "source_group"
    )


    if not group:
        return False


    canonical = source_assets.get(
        group
    )


    if not canonical:
        return False


    return (
        scene_asset.get(
            "sha256"
        )
        ==
        canonical.get(
            "sha256"
        )

        and

        scene_asset.get(
            "path"
        )
        ==
        canonical.get(
            "path"
        )
    )


def main():
    if not MANIFEST.exists():

        raise SystemExit(
            "VI1280.1: MANIFEST MISSING"
        )


    manifest = read_json(
        MANIFEST
    )


    source_assets = (
        manifest.get(
            "source_assets"
        )
        or {}
    )


    scene_map = (
        manifest.get(
            "scene_map"
        )
        or {}
    )


    failures = []

    asset_reports = []

    hashes = {}


    print()
    print(
        "=============================================="
    )

    print(
        " VI1280.1 CONTROLLED ASSET FORENSICS"
    )

    print(
        "=============================================="
    )


    for group, asset in sorted(
        source_assets.items()
    ):

        path_text = asset.get(
            "path"
        )


        if not path_text:

            failures.append({
                "source_group":
                    group,

                "reason": [
                    "path_missing"
                ],
            })

            continue


        path = Path(
            path_text
        )


        asset_failures = []


        if not path_inside_asset_root(
            path
        ):

            asset_failures.append(
                "asset_path_outside_controlled_root"
            )


        if not path.exists():

            asset_failures.append(
                "file_missing"
            )


            failures.append({
                "source_group":
                    group,

                "reason":
                    asset_failures,
            })

            continue


        if not path.is_file():

            asset_failures.append(
                "not_regular_file"
            )


        actual_size = (
            path.stat().st_size
        )


        expected_size = int(
            asset.get(
                "bytes",
                -1
            )
        )


        actual_sha = sha256_file(
            path
        )


        expected_sha = str(
            asset.get(
                "sha256"
            )
            or ""
        )


        kind = magic_kind(
            path
        )


        expected = expected_kind(
            asset.get(
                "content_type"
            )
        )


        dims = dimensions(
            path,
            kind
        )


        if actual_size != expected_size:

            asset_failures.append(
                "size_mismatch"
            )


        if (
            not expected_sha
            or
            actual_sha != expected_sha
        ):

            asset_failures.append(
                "sha256_mismatch"
            )


        if expected is None:

            asset_failures.append(
                "manifest_mime_unknown"
            )


        elif kind != expected:

            asset_failures.append(
                "magic_mime_mismatch"
            )


        if kind == "UNKNOWN":

            asset_failures.append(
                "unknown_binary_signature"
            )


        if (
            kind
            in {
                "JPEG",
                "PNG",
            }
            and
            dims is None
        ):

            asset_failures.append(
                "image_dimensions_unreadable"
            )


        if (
            kind == "PDF"
            and
            not pdf_integrity(
                path
            )
        ):

            asset_failures.append(
                "pdf_structure_check_failed"
            )


        if not license_allowed(
            asset.get(
                "license"
            )
        ):

            asset_failures.append(
                "license_failed"
            )


        transfer_url = (
            asset.get(
                "download_url"
            )
            or
            asset.get(
                "final_url"
            )
            or
            asset.get(
                "original_url"
            )
        )


        if not host_allowed(
            transfer_url
        ):

            asset_failures.append(
                "download_host_not_allowed"
            )


        hashes.setdefault(
            actual_sha,
            []
        ).append(
            group
        )


        row = {
            "source_group":
                group,

            "title":
                asset.get(
                    "title"
                ),

            "path":
                str(
                    path.resolve()
                ),

            "bytes":
                actual_size,

            "sha256":
                actual_sha,

            "content_type":
                asset.get(
                    "content_type"
                ),

            "expected_kind":
                expected,

            "magic_kind":
                kind,

            "dimensions":
                dims,

            "failures":
                sorted(
                    set(
                        asset_failures
                    )
                ),
        }


        asset_reports.append(
            row
        )


        if asset_failures:

            failures.append({
                "source_group":
                    group,

                "reason":
                    sorted(
                        set(
                            asset_failures
                        )
                    ),
            })


        dimension_text = "-"


        if dims:

            dimension_text = (
                str(
                    dims[
                        "width"
                    ]
                )
                + "x"
                + str(
                    dims[
                        "height"
                    ]
                )
            )


        print(
            group,
            "| expected=",
            expected,
            "| magic=",
            kind,
            "|",
            actual_size,
            "bytes",
            "|",
            dimension_text,
            "|",
            (
                "PASS"
                if not asset_failures
                else "FAIL"
            )
        )


    unexpected_duplicates = []


    for digest, groups in (
        hashes.items()
    ):

        if len(
            groups
        ) > 1:

            unexpected_duplicates.append({
                "sha256":
                    digest,

                "source_groups":
                    sorted(
                        groups
                    ),
            })


    part_files = sorted(
        str(
            path
        )

        for path
        in ASSET_ROOT.glob(
            "*.part"
        )
    )


    expected_scene_keys = {
        str(
            number
        )

        for number
        in range(
            1,
            13
        )
    }


    actual_scene_keys = set(
        scene_map.keys()
    )


    scene_reference_failures = []


    for scene_number in sorted(
        expected_scene_keys
    ):

        mapped = scene_map.get(
            scene_number
        )


        if not asset_record_matches_scene(
            mapped,
            source_assets
        ):

            scene_reference_failures.append(
                int(
                    scene_number
                )
            )


    mapped_scene_count = len(
        scene_map
    )


    unique_asset_count = len(
        source_assets
    )


    manifest_status_ok = (
        manifest.get(
            "status"
        )
        ==
        "VI1270_CONTROLLED_DOWNLOAD_CERTIFIED"
    )


    checks = {
        "vi1270_manifest_certified":
            manifest_status_ok,

        "exact_scene_keys_1_to_12":
            actual_scene_keys
            ==
            expected_scene_keys,

        "all_12_scenes_mapped":
            mapped_scene_count
            == 12,

        "scene_asset_references_valid":
            not scene_reference_failures,

        "minimum_8_unique_assets":
            unique_asset_count
            >= 8,

        "all_assets_forensically_valid":
            not failures,

        "no_cross_group_binary_duplicates":
            not unexpected_duplicates,

        "no_partial_files":
            not part_files,

        "ffmpeg_not_executed":
            True,

        "renderer_not_executed":
            True,

        "video_not_generated":
            True,

        "production_not_mutated":
            True,
    }


    failed_checks = [
        key

        for key, value
        in checks.items()

        if value is not True
    ]


    certified = (
        not failed_checks
    )


    status = (
        "VI1280_1_ASSET_FORENSICS_CERTIFIED"

        if certified

        else
        "VI1280_1_ASSET_FORENSICS_HOLD"
    )


    report = {
        "version":
            "1280.1",

        "status":
            status,

        "mapped_scenes":
            mapped_scene_count,

        "unique_assets":
            unique_asset_count,

        "assets":
            asset_reports,

        "scene_reference_failures":
            scene_reference_failures,

        "unexpected_duplicates":
            unexpected_duplicates,

        "partial_files":
            part_files,

        "forensic_failures":
            failures,

        "checks":
            checks,

        "failed_checks":
            failed_checks,

        "ffmpeg_executed":
            False,

        "renderer_activated":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "===== FORENSIC SUMMARY ====="
    )

    print(
        "MAPPED SCENES:",
        mapped_scene_count
    )

    print(
        "UNIQUE ASSETS:",
        unique_asset_count
    )

    print(
        "SCENE REFERENCE FAILURES:",
        scene_reference_failures
    )

    print(
        "FORENSIC FAILURES:",
        failures
    )

    print(
        "UNEXPECTED DUPLICATES:",
        unexpected_duplicates
    )

    print(
        "PART FILES:",
        part_files
    )


    print()
    print(
        "===== CHECKS ====="
    )


    for key, value in (
        checks.items()
    ):

        print(
            key,
            "=",
            (
                "PASS"
                if value
                else "FAIL"
            )
        )


    print(
        "FAILED:",
        failed_checks
    )


    print()
    print(
        "FFMPEG EXECUTED: False"
    )

    print(
        "VIDEO GENERATED: False"
    )

    print(
        "RENDERER ACTIVATED: False"
    )

    print(
        "PRODUCTION MUTATED: False"
    )


    print()
    print(
        "STATUS:",
        status
    )


    if not certified:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
