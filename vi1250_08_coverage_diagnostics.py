#!/usr/bin/env python3

import json

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
)

from vi1200_06_visual_precision import (
    scene_visual_intents,
)


BASE = Path.home() / "ShortAutoPro"

BLUEPRINT = (
    BASE
    / "temp/vi1000_launch/"
    "launch_blueprint.json"
)

PLAN = (
    BASE
    / "temp/vi1250/"
    "vi1250_selection_plan.json"
)

SEARCH = (
    BASE
    / "temp/vi1250/"
    "vi1250_search_report.json"
)

PIPELINE = (
    BASE
    / "logs/producao/"
    "vi1250_00_deep_real_source_expansion_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1250_08_coverage_diagnostics_latest.json"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():
    blueprint = read_json(
        BLUEPRINT
    )


    segments = [
        str(
            item.get(
                "segment"
            )
            or ""
        )

        for item in (
            blueprint.get(
                "scenes"
            )
            or []
        )
    ]


    entities = extract_entities(
        segments
    )

    scenes = classify_scenes(
        segments,
        entities
    )


    plan = (
        read_json(
            PLAN
        )
        if PLAN.exists()
        else {}
    )

    search = (
        read_json(
            SEARCH
        )
        if SEARCH.exists()
        else {}
    )

    pipeline = (
        read_json(
            PIPELINE
        ).get(
            "gate",
            {}
        )
        if PIPELINE.exists()
        else {}
    )


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )

    scene_reports = (
        search.get(
            "scene_reports"
        )
        or {}
    )

    hold_diagnostics = (
        pipeline.get(
            "hold_diagnostics"
        )
        or {}
    )


    blockers = []

    rows = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1250.1 COVERAGE DIAGNOSTICS"
    )

    print(
        "=============================================="
    )


    for scene in scenes:

        number = scene[
            "scene"
        ]


        final = selected.get(
            str(number),
            {}
        )


        info = scene_reports.get(
            str(number),
            {}
        )


        candidate = (
            final.get(
                "candidate"
            )
            or {}
        )


        evaluation = (
            final.get(
                "evaluation"
            )
            or {}
        )


        decision = final.get(
            "decision",
            "UNKNOWN"
        )


        intents = sorted(
            scene_visual_intents(
                scene
            )
        )


        candidate_intents = []


        if (
            evaluation.get(
                "mode"
            )
            == "DIRECT"
        ):

            candidate_intents = (
                evaluation.get(
                    "visual",
                    {}
                ).get(
                    "candidate_intents",
                    []
                )
            )


        demanded = (
            set(
                intents
            )
            &
            {
                "ELEVATOR",
                "HALLWAY",
                "ROOFTOP",
                "MEDICATION",
                "WATER_TANK",
                "SURVEILLANCE",
            }
        )


        if (
            decision
            == "SELECT_SAFE"

            and

            scene.get(
                "role"
            )
            == "HUMAN"

            and

            evaluation.get(
                "mode"
            )
            == "DIRECT"

            and

            "HUMAN"
            not in candidate_intents
        ):

            blockers.append(
                (
                    f"scene_{number}:"
                    "human_without_human_visual"
                )
            )


        if (
            decision
            == "SELECT_SAFE"

            and

            evaluation.get(
                "mode"
            )
            == "DIRECT"

            and

            demanded

            and

            not demanded.issubset(
                set(
                    candidate_intents
                )
            )
        ):

            blockers.append(
                (
                    f"scene_{number}:"
                    "visual_subtype_contradiction"
                )
            )


        row = {
            "scene":
                number,

            "segment":
                scene.get(
                    "segment"
                ),

            "role":
                scene.get(
                    "role"
                ),

            "factual":
                scene.get(
                    "factual"
                ),

            "identity_scope":
                scene.get(
                    "identity_scope"
                ),

            "location_scope":
                scene.get(
                    "location_scope"
                ),

            "scene_intents":
                intents,

            "decision":
                decision,

            "selected_title":
                candidate.get(
                    "title"
                ),

            "evaluation_mode":
                evaluation.get(
                    "mode"
                ),

            "candidate_intents":
                candidate_intents,

            "passing_candidates":
                info.get(
                    "passing_candidates"
                ),

            "raw_search_results":
                info.get(
                    "raw_search_results"
                ),

            "optimizer_hold":
                (
                    hold_diagnostics.get(
                        str(number)
                    )
                    or
                    hold_diagnostics.get(
                        number
                    )
                ),
        }


        rows.append(
            row
        )


        print()
        print(
            "SCENE",
            number
        )

        print(
            " role=",
            scene.get(
                "role"
            ),
            "| factual=",
            scene.get(
                "factual"
            )
        )

        print(
            " identity=",
            scene.get(
                "identity_scope"
            ),
            "| location=",
            scene.get(
                "location_scope"
            )
        )

        print(
            " intents=",
            intents
        )

        print(
            " segment=",
            str(
                scene.get(
                    "segment"
                )
            )[:180]
        )

        print(
            " decision=",
            decision
        )


        if candidate:

            print(
                " selected=",
                candidate.get(
                    "title"
                )
            )

            print(
                " mode=",
                evaluation.get(
                    "mode"
                ),
                "| candidate_intents=",
                candidate_intents
            )

        else:

            print(
                " passing=",
                info.get(
                    "passing_candidates"
                ),
                "| raw=",
                info.get(
                    "raw_search_results"
                )
            )


            optimizer_hold = (
                hold_diagnostics.get(
                    str(number)
                )
                or
                hold_diagnostics.get(
                    number
                )
            )


            if optimizer_hold:

                print(
                    " optimizer_reason=",
                    optimizer_hold.get(
                        "reason"
                    )
                )


    hold_scenes = [
        row[
            "scene"
        ]

        for row in rows

        if row[
            "decision"
        ]
        != "SELECT_SAFE"
    ]


    report = {
        "version":
            "1250.1",

        "status":
            (
                "VI1250_1_COVERAGE_DIAGNOSTICS_CERTIFIED"

                if not blockers

                else "HOLD"
            ),

        "selected_count":
            12
            -
            len(
                hold_scenes
            ),

        "hold_count":
            len(
                hold_scenes
            ),

        "hold_scenes":
            hold_scenes,

        "rows":
            rows,

        "blockers":
            blockers,
    }


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


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
        " DIAGNOSTIC SUMMARY"
    )

    print(
        "=============================================="
    )

    print(
        "SELECTED:",
        report[
            "selected_count"
        ]
    )

    print(
        "HOLD:",
        report[
            "hold_count"
        ]
    )

    print(
        "HOLD SCENES:",
        hold_scenes
    )

    print(
        "BLOCKERS:",
        blockers
    )

    print(
        "STATUS:",
        report[
            "status"
        ]
    )


    if blockers:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
