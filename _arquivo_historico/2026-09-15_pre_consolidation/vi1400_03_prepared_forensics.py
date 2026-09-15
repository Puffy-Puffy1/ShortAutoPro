#!/usr/bin/env python3

import hashlib
import json
import struct

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

MANIFEST = (
    BASE
    / "temp/vi1400/"
    "prepared_manifest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1400_03_prepared_forensics_latest.json"
)


def sha256_file(
    path,
):
    sha = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(
                chunk
            )

    return sha.hexdigest()


def png_info(
    path,
):
    with path.open(
        "rb"
    ) as handle:

        data = handle.read(
            24
        )

    if not data.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):

        return None

    if len(data) < 24:

        return None

    width = struct.unpack(
        ">I",
        data[16:20]
    )[0]

    height = struct.unpack(
        ">I",
        data[20:24]
    )[0]

    return {
        "width":
            width,

        "height":
            height,
    }


def main():
    manifest = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get(
            "status"
        )
        !=
        "VI1400_ASSET_TRANSFORMATION_CERTIFIED"
    ):

        raise SystemExit(
            "TRANSFORMATION_NOT_CERTIFIED"
        )

    scenes = (
        manifest.get(
            "scenes"
        )
        or {}
    )

    failures = []

    hashes = {}

    results = {}

    print()
    print(
        "=============================================="
    )
    print(
        " VI1400 PREPARED ASSET FORENSICS"
    )
    print(
        "=============================================="
    )

    for key in sorted(
        scenes,
        key=lambda x:
            int(x)
    ):
        item = scenes[
            key
        ]

        path = Path(
            item[
                "prepared_path"
            ]
        )

        scene_failures = []

        if not path.exists():

            scene_failures.append(
                "file_missing"
            )

            info = None
            digest = None

        else:

            digest = (
                sha256_file(
                    path
                )
            )

            info = png_info(
                path
            )

            if (
                digest
                !=
                item[
                    "prepared_sha256"
                ]
            ):

                scene_failures.append(
                    "sha_mismatch"
                )

            if info is None:

                scene_failures.append(
                    "not_png"
                )

            else:

                if (
                    info["width"]
                    != 1080
                    or
                    info["height"]
                    != 1920
                ):

                    scene_failures.append(
                        "wrong_dimensions"
                    )

        if digest:

            hashes.setdefault(
                digest,
                []
            ).append({
                "scene":
                    int(key),

                "source_group":
                    item.get(
                        "source_group"
                    ),
            })

        results[
            key
        ] = {
            "scene":
                int(key),

            "path":
                str(path),

            "sha256":
                digest,

            "dimensions":
                info,

            "failures":
                scene_failures,
        }

        if scene_failures:

            failures.append({
                "scene":
                    int(key),

                "failures":
                    scene_failures,
            })

        print(
            "SCENE",
            key,
            "|",
            (
                "PASS"
                if not scene_failures
                else "FAIL"
            ),
            "|",
            info
        )

    cross_source_duplicates = []

    for digest, entries in hashes.items():

        groups = {
            entry[
                "source_group"
            ]
            for entry in entries
        }

        if (
            len(entries) > 1
            and
            len(groups) > 1
        ):

            cross_source_duplicates.append({
                "sha256":
                    digest,

                "entries":
                    entries,
            })

    checks = {
        "twelve_prepared_assets":
            len(results) == 12,

        "all_png_1080x1920":
            not failures,

        "no_cross_source_duplicates":
            not cross_source_duplicates,
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
        "VI1400_PREPARED_FORENSICS_CERTIFIED"
        if certified
        else
        "VI1400_PREPARED_FORENSICS_HOLD"
    )

    report = {
        "version":
            "1400.00",

        "status":
            status,

        "assets":
            results,

        "cross_source_duplicates":
            cross_source_duplicates,

        "checks":
            checks,

        "failed_checks":
            failed_checks,
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
        "CROSS-SOURCE DUPLICATES:",
        cross_source_duplicates
    )

    print(
        "FAILED:",
        failed_checks
    )

    print(
        "STATUS:",
        status
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
