#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

MANIFEST = (
    BASE
    / "temp/vi1400/"
    "render_manifest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1450_04_portfolio_audit_latest.json"
)


def main():
    data = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        data.get(
            "scenes"
        )
        or {}
    )

    failures = []

    groups = []

    labels = []

    strategies = []

    for number in range(
        1,
        13
    ):
        scene = scenes.get(
            str(number)
        )

        if not scene:
            failures.append({
                "scene":
                    number,
                "reason":
                    "scene_missing",
            })
            continue

        group = scene.get(
            "source_group"
        )

        label = scene.get(
            "overlay_label"
        )

        strategy = scene.get(
            "strategy"
        )

        groups.append(
            group
        )

        labels.append(
            label
        )

        strategies.append(
            strategy
        )

        if (
            scene.get(
                "generic"
            )
            and
            label
            !=
            "IMAGEM ILUSTRATIVA"
        ):
            failures.append({
                "scene":
                    number,
                "reason":
                    "generic_without_disclosure",
            })

        if (
            "CONTEXT"
            in str(
                scene.get(
                    "semantic_mode"
                )
                or ""
            )
            and
            not label
        ):
            failures.append({
                "scene":
                    number,
                "reason":
                    "context_without_disclosure",
            })

        if (
            strategy
            ==
            "DOCUMENT_PAGE_PREVIEW"
            and
            scene.get(
                "content_type"
            )
            !=
            "application/pdf"
        ):
            failures.append({
                "scene":
                    number,
                "reason":
                    "document_strategy_without_pdf",
            })

    max_run = 0
    current_run = 0
    previous = None

    for group in groups:

        if group == previous:
            current_run += 1

        else:
            current_run = 1
            previous = group

        max_run = max(
            max_run,
            current_run
        )

    unique = len(
        {
            group
            for group in groups
            if group
        }
    )

    checks = {
        "twelve_scenes":
            len(scenes) == 12,

        "minimum_8_unique_sources":
            unique >= 8,

        "max_2_consecutive_same_source":
            max_run <= 2,

        "all_disclosures_valid":
            not failures,

        "scene12_document_preview":
            scenes.get(
                "12",
                {}
            ).get(
                "strategy"
            )
            ==
            "DOCUMENT_PAGE_PREVIEW",

        "scene1_archival_inset":
            scenes.get(
                "1",
                {}
            ).get(
                "strategy"
            )
            ==
            "ARCHIVAL_INSET",

        "scene4_archival_inset":
            scenes.get(
                "4",
                {}
            ).get(
                "strategy"
            )
            ==
            "ARCHIVAL_INSET",
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
        "VI1450_PORTFOLIO_AUDIT_CERTIFIED"
        if certified
        else
        "VI1450_PORTFOLIO_AUDIT_HOLD"
    )

    report = {
        "version":
            "1450.00",

        "status":
            status,

        "unique_sources":
            unique,

        "max_consecutive_same_source":
            max_run,

        "strategies":
            strategies,

        "labels":
            labels,

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
        "=============================================="
    )
    print(
        " VI1450 PORTFOLIO AUDIT"
    )
    print(
        "=============================================="
    )

    print(
        "UNIQUE SOURCES:",
        unique
    )

    print(
        "MAX SOURCE RUN:",
        max_run
    )

    for key, value in (
        checks.items()
    ):
        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
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
