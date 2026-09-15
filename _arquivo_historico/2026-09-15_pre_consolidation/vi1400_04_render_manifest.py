#!/usr/bin/env python3

import json

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1400_release_candidate_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

PREPARED = (
    BASE
    / "temp/vi1400/"
    "prepared_manifest.json"
)

OUT = (
    BASE
    / "temp/vi1400/"
    "render_manifest.json"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1400_04_render_manifest_latest.json"
)


def main():
    prepared = json.loads(
        PREPARED.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        prepared.get(
            "scenes"
        )
        or {}
    )

    labels = POLICY[
        "labels"
    ]

    output = {}

    failures = []

    for number in range(
        1,
        13
    ):
        key = str(number)

        scene = scenes[
            key
        ]

        label = scene.get(
            "overlay_label"
        )

        strategy = scene[
            "strategy"
        ]

        mode = str(
            scene.get(
                "semantic_mode"
            )
            or ""
        )

        generic = bool(
            scene.get(
                "generic"
            )
        )

        if generic:

            label = (
                labels[
                    "illustration"
                ]
            )

        elif (
            strategy
            ==
            "ARCHIVAL_INSET"
            and
            not label
        ):

            label = (
                labels[
                    "archive"
                ]
            )

        elif (
            strategy
            ==
            "DOCUMENT_PAGE_PREVIEW"
            and
            not label
        ):

            label = (
                labels[
                    "document"
                ]
            )

        elif (
            "CONTEXT"
            in mode
            and
            not label
        ):

            label = (
                labels[
                    "context"
                ]
            )

        if (
            generic
            and
            label
            !=
            labels[
                "illustration"
            ]
        ):

            failures.append({
                "scene":
                    number,

                "reason":
                    "illustration_label_missing",
            })

        output[
            key
        ] = {
            **scene,

            "overlay_label":
                label,

            "canary_duration":
                float(
                    POLICY[
                        "visual_canary"
                    ][
                        "seconds_per_scene"
                    ]
                ),
        }

    certified = (
        len(output) == 12
        and
        not failures
    )

    status = (
        "VI1400_RENDER_MANIFEST_CERTIFIED"
        if certified
        else
        "VI1400_RENDER_MANIFEST_HOLD"
    )

    OUT.write_text(
        json.dumps(
            {
                "version":
                    "1400.00",

                "status":
                    status,

                "scenes":
                    output,

                "render_scope":
                    "VISUAL_CANARY_ONLY",

                "production_allowed":
                    False,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    REPORT.write_text(
        json.dumps(
            {
                "gate":
                    {
                        "status":
                            status,

                        "scene_count":
                            len(output),

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
        " VI1400 RENDER MANIFEST"
    )
    print(
        "=============================================="
    )

    for key, scene in output.items():

        print(
            "SCENE",
            key,
            "|",
            scene[
                "strategy"
            ],
            "| label=",
            scene.get(
                "overlay_label"
            )
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
