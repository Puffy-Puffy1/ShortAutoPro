#!/usr/bin/env python3

import hashlib
import json

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

MANIFEST = (
    BASE
    / "temp/vi1300/"
    "prepared_manifest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1300_01_preparation_audit_latest.json"
)


def sha256_file(path):
    sha = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(chunk)

    return sha.hexdigest()


def main():
    if not MANIFEST.exists():
        raise SystemExit(
            "VI1300 MANIFEST MISSING"
        )

    data = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    records = (
        data.get(
            "prepared"
        )
        or []
    )

    failures = []

    seen_scenes = set()

    print()
    print(
        "=============================================="
    )
    print(
        " VI1300 PREPARATION AUDIT"
    )
    print(
        "=============================================="
    )

    for item in records:

        scene = int(
            item[
                "scene"
            ]
        )

        path = Path(
            item[
                "prepared_path"
            ]
        )

        reasons = []

        if scene in seen_scenes:
            reasons.append(
                "duplicate_scene"
            )

        seen_scenes.add(
            scene
        )

        try:
            path.resolve().relative_to(
                (
                    BASE
                    / "temp/vi1300_prepared"
                ).resolve()
            )

        except Exception:
            reasons.append(
                "path_outside_prepared_root"
            )

        if not path.exists():

            reasons.append(
                "file_missing"
            )

        else:

            actual_sha = sha256_file(
                path
            )

            if (
                actual_sha
                !=
                item.get(
                    "prepared_sha256"
                )
            ):
                reasons.append(
                    "sha256_mismatch"
                )

            if (
                path.stat().st_size
                !=
                int(
                    item.get(
                        "prepared_bytes",
                        -1
                    )
                )
            ):
                reasons.append(
                    "size_mismatch"
                )

        if (
            int(
                item.get(
                    "prepared_width",
                    0
                )
            )
            != 1080
            or
            int(
                item.get(
                    "prepared_height",
                    0
                )
            )
            != 1920
        ):

            reasons.append(
                "dimension_manifest_mismatch"
            )

        if reasons:

            failures.append({
                "scene":
                    scene,

                "reasons":
                    reasons,
            })

        print(
            "SCENE",
            scene,
            "|",
            (
                "PASS"
                if not reasons
                else "FAIL"
            ),
            "|",
            path.name
        )

    checks = {
        "upstream_vi1300_certified":
            data.get(
                "status"
            )
            ==
            "VI1300_ASSET_PREPARATION_CANARY_CERTIFIED",

        "exact_12_records":
            len(
                records
            )
            == 12,

        "exact_scene_set":
            seen_scenes
            ==
            set(
                range(
                    1,
                    13
                )
            ),

        "all_prepared_files_integral":
            not failures,

        "renderer_still_off":
            True,

        "final_video_still_off":
            True,

        "production_still_off":
            True,
    }

    failed_checks = [
        key

        for key, value
        in checks.items()

        if value is not True
    ]

    certified = (
        not failures
        and
        not failed_checks
    )

    status = (
        "VI1300_PREPARATION_AUDIT_CERTIFIED"

        if certified

        else
        "VI1300_PREPARATION_AUDIT_HOLD"
    )

    report = {
        "version":
            "1300.01",

        "status":
            status,

        "failures":
            failures,

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
        "FAILURES:",
        failures
    )

    for key, value in checks.items():

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
        "STATUS:",
        status
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
