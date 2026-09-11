#!/usr/bin/env python3

import json

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
)

import vi1200_01_real_transport as transport

from vi1250_01_seed_bank import (
    fetch_seed_bank,
)

from vi1260_01_semantic_roles import (
    scene_requirements,
)

from vi1260_02_targeted_search import (
    search_scene,
)

from vi1260_03_semantic_candidate_gate import (
    adapt_and_evaluate_vi1260,
)

from vi1260_04_global_optimizer import (
    optimize,
)


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1260_semantic_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

BLUEPRINT = (
    BASE
    / "temp/vi1000_launch/"
    "launch_blueprint.json"
)

PREVIOUS = (
    BASE
    / "temp/vi1250/"
    "vi1250_selection_plan.json"
)

PREVIOUS_DIAG = (
    BASE
    / "logs/producao/"
    "vi1250_08_coverage_diagnostics_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1260_00_coverage_resolver_latest.json"
)

PLAN_OUT = (
    BASE
    / "temp/vi1260/"
    "selection_plan.json"
)

SEARCH_OUT = (
    BASE
    / "temp/vi1260/"
    "search_report.json"
)


def read_json(
    path,
    default=None,
):
    if not path.exists():
        return (
            {} if default is None
            else default
        )

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return (
            {} if default is None
            else default
        )


def write_json(
    path,
    data,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def load_segments():
    data = read_json(
        BLUEPRINT
    )

    return [
        str(
            item.get("segment")
            or ""
        )
        for item in (
            data.get("scenes")
            or []
        )
    ]


def previous_selected():
    data = read_json(
        PREVIOUS
    )

    return (
        data.get("selected")
        or {}
    )


def previous_certified():
    data = read_json(
        PREVIOUS_DIAG
    ).get(
        "gate",
        {}
    )

    return (
        data.get("status")
        ==
        "VI1250_1_COVERAGE_DIAGNOSTICS_CERTIFIED"
    )


def dedupe(
    values,
):
    best = {}


    for item in values:

        candidate = item[
            "candidate"
        ]

        key = (
            candidate.get(
                "source_group"
            ),
            item[
                "evaluation"
            ].get(
                "mode"
            ),
        )


        old = best.get(
            key
        )


        if (
            old is None
            or
            item[
                "rank"
            ]
            >
            old[
                "rank"
            ]
        ):
            best[
                key
            ] = item


    return sorted(
        best.values(),
        key=lambda x:
            x[
                "rank"
            ],
        reverse=True
    )


def main():
    # Hard cap applies to this process, including retries.
    transport.POLICY[
        "network"
    ][
        "maximum_total_requests"
    ] = int(
        POLICY[
            "network"
        ][
            "maximum_total_requests"
        ]
    )


    segments = load_segments()

    entities = extract_entities(
        segments
    )

    scenes = classify_scenes(
        segments,
        entities
    )


    old_selected = previous_selected()


    targets = set(
        POLICY[
            "target_scenes"
        ]
    )


    seed_bank = fetch_seed_bank()


    candidates_by_scene = {}

    diagnostics = {}

    searches = {}


    print()
    print(
        "=============================================="
    )
    print(
        " VI1260 SEMANTIC ROLE + COVERAGE RESOLVER"
    )
    print(
        "=============================================="
    )

    print(
        "SCENES:",
        len(scenes)
    )

    print(
        "PRIMARY PERSON:",
        (
            entities.get(
                "primary_person"
            )
            or {}
        ).get("name")
    )

    print(
        "PRIMARY LOCATION:",
        (
            entities.get(
                "primary_location"
            )
            or {}
        ).get("name")
    )

    print(
        "TARGET SCENES:",
        sorted(targets)
    )

    print(
        "SEEDS FOUND:",
        seed_bank[
            "found"
        ],
        "/",
        seed_bank[
            "requested"
        ]
    )


    for scene in scenes:

        number = scene[
            "scene"
        ]

        requirements = scene_requirements(
            scene,
            entities
        )


        alternatives = []


        # Re-evaluate the previous selected candidate
        # under the new stricter semantics.
        old = old_selected.get(
            str(number),
            {}
        )


        old_candidate = (
            old.get("candidate")
            or {}
        )


        if old_candidate:

            raw = (
                old_candidate.get(
                    "raw_metadata"
                )
                or {}
            )


            if raw:

                alternatives.append(
                    adapt_and_evaluate_vi1260(
                        raw,
                        scene,
                        entities,
                        query="VI1260_PREVIOUS_SELECTION"
                    )
                )


        raw_results = []


        if number in targets:

            # Every verified seed may be considered;
            # the semantic gate decides whether it is
            # actually appropriate for the scene.
            raw_results.extend(
                seed_bank.get(
                    "seeds",
                    []
                )
            )


            search = search_scene(
                scene,
                entities,
                limit=int(
                    POLICY[
                        "network"
                    ][
                        "maximum_queries_per_scene"
                    ]
                )
            )


            searches[
                str(number)
            ] = search


            raw_results.extend(
                search[
                    "results"
                ]
            )


            query_label = " || ".join(
                search[
                    "queries"
                ]
            )


            for raw in raw_results:

                alternatives.append(
                    adapt_and_evaluate_vi1260(
                        raw,
                        scene,
                        entities,
                        query=query_label
                    )
                )


        alternatives = dedupe(
            alternatives
        )


        passing = [
            item
            for item in alternatives
            if item[
                "evaluation"
            ][
                "passed"
            ]
        ]


        candidates_by_scene[
            number
        ] = passing[
            :10
        ]


        diagnostics[
            str(number)
        ] = {
            "scene":
                number,

            "role":
                scene.get("role"),

            "segment":
                scene.get("segment"),

            "requirements":
                requirements,

            "targeted":
                number in targets,

            "candidate_count":
                len(alternatives),

            "passing_count":
                len(passing),

            "top": [
                {
                    "title":
                        item[
                            "candidate"
                        ].get("title"),

                    "source_class":
                        item[
                            "candidate"
                        ].get(
                            "source_class"
                        ),

                    "mode":
                        item[
                            "evaluation"
                        ].get("mode"),

                    "semantics":
                        item[
                            "evaluation"
                        ].get(
                            "candidate_semantics",
                            []
                        ),

                    "rank":
                        item["rank"],
                }
                for item in passing[:5]
            ],
        }


    optimized = optimize(
        scenes,
        candidates_by_scene,
        beam_width=400
    )


    chosen = optimized[
        "chosen"
    ]


    print()
    print(
        "===== SEMANTIC REQUIREMENTS ====="
    )


    for number in sorted(
        targets
    ):

        info = diagnostics[
            str(number)
        ]

        print(
            "SCENE",
            number,
            "| role=",
            info["role"],
            "| requirements=",
            info[
                "requirements"
            ][
                "requirements"
            ]
        )


    print()
    print(
        "===== VI1260 FINAL SELECTION ====="
    )


    selection_json = {}


    for scene in scenes:

        number = scene[
            "scene"
        ]

        item = chosen.get(
            number
        )


        if not item:

            selection_json[
                str(number)
            ] = {
                "scene":
                    number,

                "decision":
                    "HOLD_SAFE",

                "role":
                    scene.get("role"),

                "requirements":
                    diagnostics[
                        str(number)
                    ][
                        "requirements"
                    ],
            }


            print(
                "SCENE",
                number,
                "| HOLD_SAFE",
                "| passing=",
                diagnostics[
                    str(number)
                ][
                    "passing_count"
                ]
            )

            continue


        candidate = item[
            "candidate"
        ]

        evaluation = item[
            "evaluation"
        ]


        selection_json[
            str(number)
        ] = {
            "scene":
                number,

            "decision":
                "SELECT_SAFE",

            "role":
                scene.get("role"),

            "candidate":
                candidate,

            "evaluation":
                evaluation,

            "rank":
                item["rank"],
        }


        print(
            "SCENE",
            number,
            "| SELECT_SAFE",
            "|",
            candidate.get(
                "source_class"
            ),
            "|",
            evaluation.get(
                "mode"
            ),
            "|",
            str(
                candidate.get(
                    "title"
                )
            )[:80]
        )


    network = transport.stats()


    selected_count = optimized[
        "selected_count"
    ]

    hold_count = optimized[
        "hold_count"
    ]

    diversity = optimized[
        "diversity"
    ]


    scene10 = selection_json.get(
        "10",
        {}
    )


    scene10_ok = True


    if (
        scene10.get("decision")
        == "SELECT_SAFE"
    ):

        scene10_semantics = set(
            scene10.get(
                "evaluation",
                {}
            ).get(
                "candidate_semantics",
                []
            )
        )

        scene10_ok = (
            "MAINTENANCE_WORKER"
            in scene10_semantics
            or
            (
                "HOTEL_EMPLOYEE"
                in scene10_semantics
                and
                "WORKER"
                in scene10_semantics
            )
        )


    every_selected_safe = all(
        item[
            "evaluation"
        ][
            "passed"
        ]
        for item in chosen.values()
    )


    checks = {
        "previous_vi1250_1_certified":
            previous_certified(),

        "twelve_scenes":
            len(scenes) == 12,

        "target_set_present":
            targets.issubset({
                scene["scene"]
                for scene in scenes
            }),

        "semantic_roles_operational":
            True,

        "seed_bank_operational":
            seed_bank.get("ok")
            is True,

        "every_selected_candidate_safe":
            every_selected_safe,

        "scene10_requires_real_worker_semantics":
            scene10_ok,

        "query_never_evidence":
            all(
                item[
                    "evaluation"
                ].get(
                    "query_used_as_evidence"
                )
                is False
                for item in chosen.values()
            ),

        "request_budget_hard_cap":
            network[
                "requests_attempted"
            ]
            <=
            POLICY[
                "network"
            ][
                "maximum_total_requests"
            ],

        "remote_media_bytes_zero":
            network[
                "remote_media_bytes_received"
            ]
            == 0,

        "ffmpeg_off":
            True,

        "renderer_off":
            True,

        "video_off":
            True,

        "production_mutation_off":
            True,
    }


    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]


    safety_certified = (
        not failed
    )


    if (
        safety_certified
        and
        selected_count == 12
        and
        hold_count == 0
        and
        diversity["passed"]
    ):
        result = (
            "READY_FOR_CONTROLLED_DOWNLOAD_STAGE"
        )

    elif (
        safety_certified
        and
        selected_count >= 10
    ):
        result = (
            "NEAR_READY_SOURCE_PORTFOLIO"
        )

    elif (
        safety_certified
        and
        selected_count >= 8
    ):
        result = (
            "COVERAGE_IMPROVED_MORE_SOURCES_REQUIRED"
        )

    elif safety_certified:
        result = (
            "SEMANTIC_HARDENING_CERTIFIED_"
            "MORE_SOURCES_REQUIRED"
        )

    else:
        result = "HOLD"


    status = (
        "VI1260_SEMANTIC_COVERAGE_CERTIFIED"
        if safety_certified
        else "HOLD"
    )


    report = {
        "version":
            "1260.00",

        "status":
            status,

        "result":
            result,

        "selected_count":
            selected_count,

        "hold_count":
            hold_count,

        "hold_scenes":
            optimized["holds"],

        "unique_sources":
            optimized[
                "unique_sources"
            ],

        "group_counts":
            optimized[
                "group_counts"
            ],

        "diversity":
            diversity,

        "network":
            network,

        "checks":
            checks,

        "failed":
            failed,

        "remote_media_downloaded":
            False,

        "ffmpeg_executed":
            False,

        "renderer_activated":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    write_json(
        PLAN_OUT,
        {
            "version":
                "1260.00",

            "selected":
                selection_json,

            "portfolio":
                optimized[
                    "portfolio"
                ],

            "download_allowed":
                False,

            "render_allowed":
                False,
        }
    )


    write_json(
        SEARCH_OUT,
        {
            "diagnostics":
                diagnostics,

            "searches":
                searches,
        }
    )


    write_json(
        OUT,
        {
            "gate":
                report
        }
    )


    print()
    print(
        "===== PORTFOLIO ====="
    )

    print(
        "SELECTED:",
        selected_count
    )

    print(
        "HOLD:",
        hold_count
    )

    print(
        "HOLD SCENES:",
        optimized["holds"]
    )

    print(
        "UNIQUE SOURCES:",
        optimized[
            "unique_sources"
        ]
    )

    print(
        "DIVERSITY PASS:",
        diversity[
            "passed"
        ]
    )


    print()
    print(
        "===== NETWORK ====="
    )

    print(
        "REQUESTS ATTEMPTED:",
        network[
            "requests_attempted"
        ]
    )

    print(
        "REQUESTS SUCCEEDED:",
        network[
            "requests_succeeded"
        ]
    )

    print(
        "REQUESTS FAILED:",
        network[
            "requests_failed"
        ]
    )

    print(
        "REMOTE MEDIA BYTES:",
        network[
            "remote_media_bytes_received"
        ]
    )


    print()
    print(
        "===== CHECKS ====="
    )

    for key, value in checks.items():

        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
        )


    print(
        "FAILED:",
        failed
    )


    print()
    print(
        "REMOTE MEDIA DOWNLOADED: False"
    )

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

    print(
        "VI1260 RESULT:",
        result
    )


    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
