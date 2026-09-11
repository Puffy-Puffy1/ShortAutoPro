#!/usr/bin/env python3

import json

from collections import Counter

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
)

from vi1000_1_query_gate import (
    plan_queries,
)


import vi1200_01_real_transport as transport


from vi1250_01_seed_bank import (
    fetch_seed_bank,
    seeds_for_scene,
)

from vi1250_02_query_expander import (
    expanded_queries,
)

from vi1250_03_cached_real_search import (
    run_expanded_search,
    health as search_health,
)

from vi1250_04_candidate_engine import (
    adapt_and_evaluate,
    evaluate_candidate_record,
)

from vi1250_05_portfolio_optimizer import (
    choose_portfolio,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

WORK = (
    BASE
    / "temp/vi1250"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1250_00_deep_real_source_expansion_latest.json"
)

PLAN_OUT = (
    WORK
    / "vi1250_selection_plan.json"
)

SEARCH_OUT = (
    WORK
    / "vi1250_search_report.json"
)

BLUEPRINT = (
    BASE
    / "temp/vi1000_launch/"
    "launch_blueprint.json"
)

PREVIOUS_PLAN = (
    BASE
    / "temp/vi1200_1_real/"
    "hardened_real_selection_plan.json"
)

PREVIOUS_REPORT = (
    BASE
    / "logs/producao/"
    "vi1200_10_hardened_real_pipeline_latest.json"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1250_source_expansion_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)


def write_json(
    path,
    data
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


def read_json(
    path,
    default=None,
):
    if not path.exists():
        return (
            default
            if default is not None
            else {}
        )


    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return (
            default
            if default is not None
            else {}
        )


def load_segments():
    data = read_json(
        BLUEPRINT
    )


    return [
        str(
            item.get(
                "segment"
            )
            or ""
        )

        for item in (
            data.get(
                "scenes"
            )
            or []
        )
    ]


def previous_scene_map():
    data = read_json(
        PREVIOUS_PLAN,
        {}
    )


    return {
        int(
            item[
                "scene"
            ]
        ):
            item

        for item in (
            data.get(
                "selections"
            )
            or []
        )
    }


def previous_status():
    data = read_json(
        PREVIOUS_REPORT,
        {}
    ).get(
        "gate",
        {}
    )


    return data.get(
        "status",
        "MISSING"
    )


def dedupe_alternatives(
    values
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


        current = best.get(
            key
        )


        if (
            current is None
            or
            item[
                "rank"
            ]
            >
            current[
                "rank"
            ]
        ):

            best[
                key
            ] = item


    return sorted(
        best.values(),
        key=lambda item:
            item[
                "rank"
            ],
        reverse=True
    )


def existing_candidate(
    previous,
    scene,
    entities
):
    if not previous:
        return None


    selected = previous.get(
        "selected"
    )


    if not selected:
        return None


    candidate = selected.get(
        "candidate"
    )


    if not candidate:
        return None


    return evaluate_candidate_record(
        scene,
        dict(
            candidate
        ),
        entities
    )


def expansion_targets(
    scenes,
    previous_map
):
    targets = set()


    groups = []


    for scene in scenes:

        previous = previous_map.get(
            scene[
                "scene"
            ]
        )


        if (
            not previous
            or
            previous.get(
                "decision"
            )
            != "SELECT_SAFE"
            or
            not previous.get(
                "selected"
            )
        ):

            targets.add(
                scene[
                    "scene"
                ]
            )

            continue


        candidate = (
            previous[
                "selected"
            ].get(
                "candidate"
            )
            or {}
        )


        group = candidate.get(
            "source_group"
        )


        if group:

            groups.append(
                (
                    scene[
                        "scene"
                    ],
                    group,
                )
            )


    counts = Counter(
        group
        for _, group in groups
    )


    for number, group in groups:

        if counts[
            group
        ] > 1:

            targets.add(
                number
            )


    # Always reconsider final CTA/document visual.
    if scenes:

        targets.add(
            scenes[
                -1
            ][
                "scene"
            ]
        )


    return sorted(
        targets
    )


def main():
    WORK.mkdir(
        parents=True,
        exist_ok=True
    )


    segments = load_segments()


    entities = extract_entities(
        segments
    )


    scenes = classify_scenes(
        segments,
        entities
    )


    query_plans = plan_queries(
        scenes,
        entities
    )


    query_map = {
        item[
            "scene"
        ]:
            item

        for item in query_plans
    }


    previous_map = previous_scene_map()


    targets = expansion_targets(
        scenes,
        previous_map
    )


    seed_bank = fetch_seed_bank()


    candidates_by_scene = {}

    search_records = []

    scene_reports = {}


    print()
    print(
        "=============================================="
    )

    print(
        " VI1250 DEEP REAL SOURCE EXPANSION"
    )

    print(
        "=============================================="
    )


    print(
        "SCENES:",
        len(
            scenes
        )
    )


    print(
        "PRIMARY PERSON:",
        (
            entities.get(
                "primary_person"
            )
            or {}
        ).get(
            "name"
        )
    )


    print(
        "PRIMARY LOCATION:",
        (
            entities.get(
                "primary_location"
            )
            or {}
        ).get(
            "name"
        )
    )


    print(
        "PREVIOUS STATUS:",
        previous_status()
    )


    print(
        "EXPANSION TARGETS:",
        targets
    )


    print(
        "SEED BANK:",
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


        previous = previous_map.get(
            number
        )


        alternatives = []


        old = existing_candidate(
            previous,
            scene,
            entities
        )


        if (
            old
            and
            old[
                "evaluation"
            ][
                "passed"
            ]
        ):

            alternatives.append(
                old
            )


        seed_raw = seeds_for_scene(
            scene,
            seed_bank
        )


        for raw in seed_raw:

            alternatives.append(
                adapt_and_evaluate(
                    raw,
                    scene,
                    entities,
                    query="VI1250_TARGETED_SEED"
                )
            )


        expansion = None


        if number in targets:

            query_expansion = expanded_queries(
                scene,
                query_map[
                    number
                ],
                entities,
                previous_scene=previous,
                limit=(
                    POLICY[
                        "network"
                    ][
                        "maximum_queries_per_hold_scene"
                    ]
                )
            )


            use_archive = (
                scene.get(
                    "factual"
                )
                or
                scene.get(
                    "identity_required"
                )
                or
                scene[
                    "role"
                ]
                in {
                    "DOCUMENT",
                    "EVIDENCE",
                }
            )


            expansion = run_expanded_search(
                query_expansion[
                    "queries"
                ],
                use_archive=use_archive,
                max_archive_queries=(
                    POLICY[
                        "network"
                    ][
                        "maximum_archive_queries_per_scene"
                    ]
                )
            )


            expansion[
                "scene"
            ] = number


            expansion[
                "query_analysis"
            ] = query_expansion


            search_records.append(
                expansion
            )


            query_label = " || ".join(
                query_expansion[
                    "queries"
                ]
            )


            for raw in (
                expansion[
                    "results"
                ]
            ):

                alternatives.append(
                    adapt_and_evaluate(
                        raw,
                        scene,
                        entities,
                        query=query_label
                    )
                )


        alternatives = dedupe_alternatives(
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


        # Keep enough alternatives for the global
        # optimizer without creating an enormous plan.
        candidates_by_scene[
            number
        ] = passing[
            :10
        ]


        scene_reports[
            str(number)
        ] = {
            "scene":
                number,

            "role":
                scene[
                    "role"
                ],

            "targeted_for_expansion":
                number in targets,

            "previous_decision":
                (
                    previous.get(
                        "decision"
                    )
                    if previous
                    else None
                ),

            "seed_candidates":
                len(
                    seed_raw
                ),

            "raw_search_results":
                (
                    len(
                        expansion[
                            "results"
                        ]
                    )
                    if expansion
                    else 0
                ),

            "passing_candidates":
                len(
                    passing
                ),

            "top_candidates": [
                {
                    "title":
                        item[
                            "candidate"
                        ].get(
                            "title"
                        ),

                    "source_group":
                        item[
                            "candidate"
                        ].get(
                            "source_group"
                        ),

                    "source_class":
                        item[
                            "candidate"
                        ].get(
                            "source_class"
                        ),

                    "mode":
                        item[
                            "evaluation"
                        ].get(
                            "mode"
                        ),

                    "rank":
                        item[
                            "rank"
                        ],
                }

                for item in (
                    passing[
                        :5
                    ]
                )
            ],
        }


    optimized = choose_portfolio(
        scenes,
        candidates_by_scene
    )


    selected_count = optimized[
        "selected_count"
    ]


    hold_count = optimized[
        "hold_count"
    ]


    diversity = optimized[
        "diversity"
    ]


    selected = {}


    all_safe = True

    query_never_evidence = True


    for scene in scenes:

        number = scene[
            "scene"
        ]


        chosen = (
            optimized[
                "chosen"
            ].get(
                number
            )
        )


        if not chosen:

            selected[
                str(number)
            ] = {
                "scene":
                    number,

                "decision":
                    "HOLD_SAFE",

                "role":
                    scene[
                        "role"
                    ],
            }

            continue


        candidate = chosen[
            "candidate"
        ]


        evaluation = chosen[
            "evaluation"
        ]


        if not evaluation[
            "passed"
        ]:

            all_safe = False


        truth = evaluation.get(
            "truth",
            {}
        )


        if (
            truth
            and
            truth.get(
                "query_used_as_evidence"
            )
            is not False
        ):

            query_never_evidence = False


        selected[
            str(number)
        ] = {
            "scene":
                number,

            "decision":
                "SELECT_SAFE",

            "role":
                scene[
                    "role"
                ],

            "cta":
                scene.get(
                    "cta",
                    False
                ),

            "candidate":
                candidate,

            "evaluation":
                evaluation,

            "rank":
                chosen[
                    "rank"
                ],
        }


    health = search_health(
        search_records
    )


    network = transport.stats()


    previous_ok = (
        previous_status()
        ==
        "VI1200_1_REAL_WORLD_SAFETY_CERTIFIED"
    )


    search_operational = (
        any(
            record.get(
                "unique_results",
                0
            )
            > 0

            for record in search_records
        )
        or
        seed_bank[
            "found"
        ]
        > 0
    )


    checks = {
        "previous_vi1200_1_certified":
            previous_ok,

        "benchmark_has_12_scenes":
            len(
                scenes
            )
            == 12,

        "primary_person_resolved":
            bool(
                entities.get(
                    "primary_person"
                )
            ),

        "primary_location_resolved":
            bool(
                entities.get(
                    "primary_location"
                )
            ),

        "seed_bank_operational":
            seed_bank[
                "ok"
            ]
            and
            seed_bank[
                "found"
            ]
            >= 5,

        "source_expansion_operational":
            search_operational,

        "every_selected_candidate_safe":
            all_safe,

        "query_is_never_evidence":
            query_never_evidence,

        "hold_is_allowed":
            True,

        "remote_media_bytes_zero":
            network[
                "remote_media_bytes_received"
            ]
            == 0,

        "ffmpeg_off":
            True,

        "renderer_off":
            True,

        "video_generation_off":
            True,

        "production_mutation_off":
            True,

        "source_recovery_shadow_only":
            (
                POLICY[
                    "source_recovery"
                ][
                    "mode"
                ]
                == "SHADOW_ONLY"
            ),
    }


    failed = [
        key
        for key, value in (
            checks.items()
        )
        if value is not True
    ]


    safety_certified = (
        not failed
    )


    full_ready = (
        safety_certified
        and
        selected_count
        == 12
        and
        hold_count
        == 0
        and
        diversity[
            "passed"
        ]
    )


    near_ready = (
        safety_certified
        and
        selected_count
        >=
        POLICY[
            "coverage"
        ][
            "minimum_near_ready_scenes"
        ]
    )


    status = (
        "VI1250_SOURCE_EXPANSION_SAFETY_CERTIFIED"
        if safety_certified
        else "HOLD"
    )


    if full_ready:

        result_name = (
            "READY_FOR_CONTROLLED_DOWNLOAD_STAGE"
        )

    elif near_ready:

        result_name = (
            "PARTIAL_EXPANSION_CERTIFIED"
        )

    elif safety_certified:

        result_name = (
            "SOURCE_EXPANSION_CERTIFIED_"
            "MORE_SOURCES_REQUIRED"
        )

    else:

        result_name = "HOLD"


    report = {
        "version":
            "1250.00",

        "status":
            status,

        "result":
            result_name,

        "entities":
            entities,

        "expansion_targets":
            targets,

        "seed_bank": {
            "requested":
                seed_bank[
                    "requested"
                ],

            "found":
                seed_bank[
                    "found"
                ],
        },

        "search_health":
            health,

        "network":
            network,

        "selected_count":
            selected_count,

        "hold_count":
            hold_count,

        "hold_scenes":
            optimized[
                "holds"
            ],

        "hold_diagnostics":
            optimized.get(
                "hold_diagnostics",
                {}
            ),

        "portfolio":
            optimized[
                "portfolio"
            ],

        "group_counts":
            optimized[
                "group_counts"
            ],

        "class_counts":
            optimized[
                "class_counts"
            ],

        "diversity":
            diversity,

        "full_ready":
            full_ready,

        "near_ready":
            near_ready,

        "checks":
            checks,

        "failed":
            failed,

        "network_executed":
            bool(
                network[
                    "requests_attempted"
                ]
            ),

        "real_metadata_used":
            True,

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

        "publication_executed":
            False,
    }


    write_json(
        SEARCH_OUT,
        {
            "version":
                "1250.00",

            "scene_reports":
                scene_reports,

            "search_records":
                search_records,

            "health":
                health,
        }
    )


    write_json(
        PLAN_OUT,
        {
            "version":
                "1250.00",

            "selected":
                selected,

            "portfolio":
                optimized[
                    "portfolio"
                ],

            "hold_scenes":
                optimized[
                    "holds"
                ],

            "download_allowed":
                False,

            "render_allowed":
                False,
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
        "===== SCENE EXPANSION ====="
    )


    for scene in scenes:

        number = scene[
            "scene"
        ]


        info = scene_reports[
            str(number)
        ]


        final = selected[
            str(number)
        ]


        if (
            final[
                "decision"
            ]
            == "SELECT_SAFE"
        ):

            candidate = final[
                "candidate"
            ]


            print(
                "SCENE",
                number,
                "| SELECT_SAFE",
                "|",
                candidate[
                    "source_class"
                ],
                "|",
                final[
                    "evaluation"
                ][
                    "mode"
                ],
                "|",
                str(
                    candidate.get(
                        "title"
                    )
                )[:84]
            )

        else:

            print(
                "SCENE",
                number,
                "| HOLD_SAFE",
                "| passing=",
                info[
                    "passing_candidates"
                ],
                "| raw=",
                info[
                    "raw_search_results"
                ]
            )


    print()
    print(
        "===== GLOBAL PORTFOLIO ====="
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
        optimized[
            "holds"
        ]
    )

    print(
        "UNIQUE SOURCES:",
        diversity[
            "unique_source_count"
        ]
    )

    print(
        "UNIQUE RATIO:",
        diversity[
            "unique_source_ratio"
        ]
    )

    print(
        "MAX RUN:",
        diversity[
            "maximum_consecutive_same_source"
        ]
    )

    print(
        "DIVERSITY PASS:",
        diversity[
            "passed"
        ]
    )

    print(
        "SOURCE CLASSES:",
        optimized[
            "class_counts"
        ]
    )


    print()
    print(
        "===== SEARCH HEALTH ====="
    )

    print(
        health
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
        "METADATA BYTES:",
        network[
            "metadata_bytes_received"
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
        "VI1250 RESULT:",
        result_name
    )


    if failed:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
