#!/usr/bin/env python3

import copy
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

from vi1260_03_semantic_candidate_gate import (
    adapt_and_evaluate_vi1260,
)

from vi1260_04_global_optimizer import (
    optimize,
)

from vi1260_1_01_strict_semantic_audit import (
    strict_item,
)

from vi1260_1_02_repair_search import (
    search_repair_scene,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1260_1_predownload_policy.json"
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
    / "temp/vi1260/"
    "selection_plan.json"
)

PREVIOUS_REPORT = (
    BASE
    / "logs/producao/"
    "vi1260_00_coverage_resolver_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1260_1_00_predownload_audit_latest.json"
)

PLAN_OUT = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

SEARCH_OUT = (
    BASE
    / "temp/vi1260_1/"
    "repair_search.json"
)


def read_json(
    path,
    default=None,
):
    if not path.exists():
        return (
            {}
            if default is None
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
            {}
            if default is None
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


def previous_certified():
    report = read_json(
        PREVIOUS_REPORT
    ).get(
        "gate",
        {}
    )

    return (
        report.get(
            "status"
        )
        ==
        "VI1260_SEMANTIC_COVERAGE_CERTIFIED"
    )


def current_selection():
    return (
        read_json(
            PREVIOUS
        ).get(
            "selected"
        )
        or {}
    )


def item_from_previous(
    stored,
):
    if (
        stored.get(
            "decision"
        )
        != "SELECT_SAFE"
    ):
        return None


    candidate = copy.deepcopy(
        stored.get(
            "candidate"
        )
        or {}
    )


    evaluation = copy.deepcopy(
        stored.get(
            "evaluation"
        )
        or {}
    )


    if not candidate:
        return None


    return {
        "candidate":
            candidate,

        "evaluation":
            evaluation,

        "rank":
            float(
                stored.get(
                    "rank",
                    0
                )
            ),
    }


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
            item.get(
                "evaluation",
                {}
            ).get(
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


def main():
    transport.POLICY[
        "network"
    ][
        "maximum_total_requests"
    ] = int(
        POLICY[
            "network"
        ][
            "metadata_request_budget"
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


    old_selection = (
        current_selection()
    )


    seed_bank = (
        fetch_seed_bank()
    )


    repair_targets = {
        3,
        6,
        8,
    }


    candidates_by_scene = {}

    repair_searches = {}

    strict_diagnostics = {}


    print()
    print(
        "=============================================="
    )

    print(
        " VI1260.1 PRE-DOWNLOAD SEMANTIC AUDIT"
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
        "REPAIR TARGETS:",
        sorted(
            repair_targets
        )
    )


    for scene in scenes:

        number = scene[
            "scene"
        ]

        alternatives = []


        stored = old_selection.get(
            str(number),
            {}
        )


        old_item = item_from_previous(
            stored
        )


        if old_item:

            audited = strict_item(
                scene,
                old_item,
                entities
            )

            alternatives.append(
                audited
            )


        search = None


        if number in repair_targets:

            search = search_repair_scene(
                number
            )


            repair_searches[
                str(number)
            ] = search


            raw_results = list(
                search[
                    "results"
                ]
            )


            # VI1260.2:
            # evaluate all already verified real seeds.
            # Strict semantic audit decides suitability.
            verified_seeds = list(
                seed_bank.get(
                    "seeds",
                    []
                )
            )

            raw_results.extend(
                verified_seeds
            )


            query_label = " || ".join(
                search[
                    "queries"
                ]
            )


            for raw in raw_results:

                item = (
                    adapt_and_evaluate_vi1260(
                        raw,
                        scene,
                        entities,
                        query=query_label
                    )
                )


                item = strict_item(
                    scene,
                    item,
                    entities
                )


                alternatives.append(
                    item
                )


        alternatives = dedupe(
            alternatives
        )


        passing = [
            item

            for item in alternatives

            if item.get(
                "evaluation",
                {}
            ).get(
                "passed"
            )
        ]


        candidates_by_scene[
            number
        ] = passing[
            :10
        ]


        strict_diagnostics[
            str(number)
        ] = {
            "scene":
                number,

            "role":
                scene.get(
                    "role"
                ),

            "targeted":
                number
                in repair_targets,

            "passing_count":
                len(
                    passing
                ),

            "top": [
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

                for item in passing[
                    :5
                ]
            ],
        }


    optimized = optimize(
        scenes,
        candidates_by_scene,
        beam_width=500
    )


    chosen = optimized[
        "chosen"
    ]


    selection_json = {}


    print()
    print(
        "===== STRICT FINAL SELECTION ====="
    )


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
                    scene.get(
                        "role"
                    ),
            }


            print(
                "SCENE",
                number,
                "| HOLD_SAFE",
                "| passing=",
                strict_diagnostics[
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
                scene.get(
                    "role"
                ),

            "candidate":
                candidate,

            "evaluation":
                evaluation,

            "rank":
                item[
                    "rank"
                ],
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
            )[:90]
        )


    selected_count = (
        optimized[
            "selected_count"
        ]
    )

    hold_count = (
        optimized[
            "hold_count"
        ]
    )

    diversity = (
        optimized[
            "diversity"
        ]
    )


    all_selected_safe = all(
        item.get(
            "evaluation",
            {}
        ).get(
            "passed"
        )
        is True

        for item in (
            chosen.values()
        )
    )


    no_scene3_document = True

    no_scene6_transport = True


    scene3 = selection_json.get(
        "3",
        {}
    )

    if (
        scene3.get(
            "decision"
        )
        == "SELECT_SAFE"
    ):

        title = str(
            scene3.get(
                "candidate",
                {}
            ).get(
                "title"
            )
            or ""
        ).lower()


        if (
            title.endswith(
                ".pdf"
            )
            or
            "autopsy report"
            in title
        ):
            no_scene3_document = False


    scene6 = selection_json.get(
        "6",
        {}
    )


    if (
        scene6.get(
            "decision"
        )
        == "SELECT_SAFE"
    ):

        title = str(
            scene6.get(
                "candidate",
                {}
            ).get(
                "title"
            )
            or ""
        ).lower()


        if any(
            word in title

            for word in [
                "railroad",
                "railway",
                "station",
                "tram",
                "airport",
            ]
        ):
            no_scene6_transport = False


    network = transport.stats()


    checks = {
        "previous_vi1260_certified":
            previous_certified(),

        "scene_count_12":
            len(
                scenes
            )
            == 12,

        "strict_scene3_operational":
            no_scene3_document,

        "strict_scene6_operational":
            no_scene6_transport,

        "every_selected_safe":
            all_selected_safe,

        "query_never_evidence":
            all(
                item[
                    "evaluation"
                ].get(
                    "query_used_as_evidence"
                )
                is False

                for item in (
                    chosen.values()
                )
            ),

        "request_budget_respected":
            network[
                "requests_attempted"
            ]
            <=
            POLICY[
                "network"
            ][
                "metadata_request_budget"
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


    ready = (
        safety_certified

        and

        selected_count == 12

        and

        hold_count == 0

        and

        diversity.get(
            "passed"
        )
        is True
    )


    status = (
        "VI1260_1_PREDOWNLOAD_SEMANTICS_CERTIFIED"

        if safety_certified

        else "HOLD"
    )


    result = (
        "READY_FOR_CONTROLLED_DOWNLOAD_STAGE"

        if ready

        else
        "PREDOWNLOAD_SEMANTICS_CERTIFIED_MORE_SOURCES_REQUIRED"
        if safety_certified

        else "HOLD"
    )


    report = {
        "version":
            "1260.1",

        "status":
            status,

        "result":
            result,

        "ready_for_controlled_download":
            ready,

        "selected_count":
            selected_count,

        "hold_count":
            hold_count,

        "hold_scenes":
            optimized[
                "holds"
            ],

        "unique_sources":
            optimized[
                "unique_sources"
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
                "1260.1",

            "selected":
                selection_json,

            "portfolio":
                optimized[
                    "portfolio"
                ],

            "download_allowed":
                ready,

            "render_allowed":
                False,
        }
    )


    write_json(
        SEARCH_OUT,
        {
            "repair_searches":
                repair_searches,

            "diagnostics":
                strict_diagnostics,
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
        "===== PRE-DOWNLOAD PORTFOLIO ====="
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
        optimized[
            "unique_sources"
        ]
    )

    print(
        "DIVERSITY PASS:",
        diversity.get(
            "passed"
        )
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
        "VI1260.1 RESULT:",
        result
    )


    if failed:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
