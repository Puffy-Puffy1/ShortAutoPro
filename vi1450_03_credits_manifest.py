#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

SELECTION = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

DOWNLOAD = (
    BASE
    / "temp/vi1270_downloads/"
    "download_manifest.json"
)

JSON_OUT = (
    BASE
    / "temp/vi1450/"
    "credits_manifest.json"
)

TEXT_OUT = (
    BASE
    / "temp/vi1450/"
    "credits.txt"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1450_03_credits_manifest_latest.json"
)


def read_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():
    selection = read_json(
        SELECTION
    )

    download = read_json(
        DOWNLOAD
    )

    selected = (
        selection.get(
            "selected"
        )
        or {}
    )

    scene_map = (
        download.get(
            "scene_map"
        )
        or {}
    )

    credits = {}

    failures = []

    for number in range(
        1,
        13
    ):
        key = str(number)

        item = (
            selected.get(
                key
            )
            or {}
        )

        candidate = (
            item.get(
                "candidate"
            )
            or {}
        )

        asset = (
            scene_map.get(
                key
            )
            or {}
        )

        group = str(
            candidate.get(
                "source_group"
            )
            or
            asset.get(
                "source_group"
            )
            or ""
        )

        if not group:
            failures.append({
                "scene":
                    number,
                "reason":
                    "source_group_missing",
            })
            continue

        entry = credits.setdefault(
            group,
            {
                "source_group":
                    group,

                "title":
                    candidate.get(
                        "title"
                    )
                    or
                    asset.get(
                        "title"
                    ),

                "license":
                    candidate.get(
                        "license"
                    )
                    or
                    asset.get(
                        "license"
                    ),

                "provider":
                    candidate.get(
                        "provider"
                    )
                    or
                    asset.get(
                        "provider"
                    ),

                "original_url":
                    asset.get(
                        "original_url"
                    ),

                "scenes":
                    [],
            }
        )

        entry[
            "scenes"
        ].append(
            number
        )

    rows = sorted(
        credits.values(),
        key=lambda item:
            min(
                item[
                    "scenes"
                ]
            )
    )

    for row in rows:

        if not row.get(
            "title"
        ):
            failures.append({
                "source_group":
                    row[
                        "source_group"
                    ],
                "reason":
                    "title_missing",
            })

        if not row.get(
            "license"
        ):
            failures.append({
                "source_group":
                    row[
                        "source_group"
                    ],
                "reason":
                    "license_missing",
            })

    certified = (
        len(rows) >= 8
        and
        not failures
    )

    status = (
        "VI1450_CREDITS_MANIFEST_CERTIFIED"
        if certified
        else
        "VI1450_CREDITS_MANIFEST_HOLD"
    )

    JSON_OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    JSON_OUT.write_text(
        json.dumps(
            {
                "version":
                    "1450.00",

                "status":
                    status,

                "unique_sources":
                    len(rows),

                "credits":
                    rows,

                "failures":
                    failures,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    lines = []

    for index, row in enumerate(
        rows,
        start=1
    ):
        lines.append(
            (
                f"{index}. "
                f"{row['title']} "
                f"| {row['license']} "
                f"| scenes={row['scenes']} "
                f"| {row.get('original_url') or ''}"
            )
        )

    TEXT_OUT.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8"
    )

    REPORT.write_text(
        json.dumps(
            {
                "gate":
                    {
                        "status":
                            status,

                        "unique_sources":
                            len(rows),

                        "failures":
                            failures,
                    }
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "=============================================="
    )
    print(
        " VI1450 CREDITS MANIFEST"
    )
    print(
        "=============================================="
    )

    print(
        "UNIQUE SOURCES:",
        len(rows)
    )

    print(
        "FAILURES:",
        failures
    )

    print(
        "STATUS:",
        status
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
