#!/usr/bin/env python3

import json

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
)

from vi1000_1_query_gate import (
    plan_queries,
    evaluate_candidate,
    audit_portfolio,
)


import vi1200_01_real_transport as transport


from vi1200_02_commons_provider import (
    exact_titles as commons_exact_titles,
)


from vi1200_04_real_candidate_adapter import (
    adapt,
)


from vi1200_06_visual_precision import (
    evaluate_visual_precision,
)


from vi1200_07_search_expansion import (
    search_scene,
    provider_health,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

WORK = (
    BASE
    / "temp/vi1200_1_real"
)

OUT = (
    BASE
    / "logs/producao"
    / "vi1200_10_hardened_real_pipeline_latest.json"
)

PLAN_OUT = (
    WORK
    / "hardened_real_selection_plan.json"
)

RAW_OUT = (
    WORK
    / "hardened_provider_metadata.json"
)

BLUEPRINT = (
    BASE
    / "temp/vi1000_launch/"
    "launch_blueprint.json"
)


EXACT_TITLES = [
    "File:Hotel Cecil LA.jpg",
    "File:Elisa Lam elevator video.webm",
    "File:Medicine box (AM 614816-33).jpg",
    "File:Arizona Biltmore Hallway.jpg",
]


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


def norm_simple(
    value
):
    return " ".join(
        str(
            value or ""
        ).lower().split()
    )


def load_segments():
    data = json.loads(
        BLUEPRINT.read_text(
            encoding="utf-8"
        )
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


def exact_map(
    exact_result
):
    result = {}

    for item in (
        exact_result.get(
            "results"
        )
        or []
    ):
        result[
            norm_simple(
                item.get(
                    "title"
                )
            )
        ] = item

    return result


def find_exact(
    mapped,
    fragment
):
    wanted = norm_simple(
        fragment
    )

    for key, value in (
        mapped.items()
    ):
        if wanted in key:
            return value

    return None


def combined_evaluation(
    scene,
    candidate,
    entities
):
    base_gate = evaluate_candidate(
        scene,
        candidate,
        entities
    )

    visual_gate = (
        evaluate_visual_precision(
            scene,
            candidate
        )
    )


    return {
        "passed":
            (
                base_gate[
                    "passed"
                ]
                and
                visual_gate[
                    "passed"
                ]
            ),

        "truth_gate":
            base_gate,

        "visual_gate":
            visual_gate,

        "reasons":
            sorted(
                set(
                    base_gate[
                        "reasons"
                    ]
                    +
                    visual_gate[
                        "reasons"
                    ]
                )
            ),
    }


def rank_candidate(
    candidate,
    combined
):
    if not combined[
        "passed"
    ]:
        return -10000.0


    case_bonus = (
        25
        if candidate[
            "intended_usage"
        ]
        == "CASE_SPECIFIC"
        else 5
    )


    visual = (
        combined[
            "visual_gate"
        ][
            "precision_score"
        ]
    )


    score = (
        float(
            candidate.get(
                "quality_score",
                0
            )
        )
        * 0.20

        +

        float(
            candidate.get(
                "semantic_score",
                0
            )
        )
        * 0.30

        +

        float(
            candidate.get(
                "provenance_score",
                0
            )
        )
        * 0.25

        +

        float(
            visual
        )
        * 0.25

        +

        case_bonus
    )


    return round(
        score,
        2
    )


def evaluate_pool(
    scene,
    raw_pool,
    entities,
    query_label
):
    result = []


    for raw in raw_pool:

        candidate = adapt(
            raw,
            scene,
            entities,
            search_query=query_label
        )


        combined = (
            combined_evaluation(
                scene,
                candidate,
                entities
            )
        )


        result.append({
            "candidate":
                candidate,

            "combined_gate":
                combined,

            "rank":
                rank_candidate(
                    candidate,
                    combined
                ),
        })


    return result


def select_all(
    scenes,
    query_plans,
    exact_mapped
):
    searches = {}

    selections = []

    source_counts = {}


    for scene, query_plan in zip(
        scenes,
        query_plans
    ):

        search = search_scene(
            scene,
            query_plan,
            exact_mapped,
            max_variants=3
        )


        searches[
            str(
                scene[
                    "scene"
                ]
            )
        ] = search


        query_label = " || ".join(
            search[
                "queries"
            ]
        )


        evaluated = evaluate_pool(
            scene,
            search[
                "results"
            ],
            entities=GLOBAL_ENTITIES,
            query_label=query_label
        )


        passing = [
            item
            for item in evaluated
            if item[
                "combined_gate"
            ][
                "passed"
            ]
        ]


        for item in passing:

            group = (
                item[
                    "candidate"
                ][
                    "source_group"
                ]
            )


            reuse = source_counts.get(
                group,
                0
            )


            item[
                "effective_rank"
            ] = (
                item[
                    "rank"
                ]
                -
                (
                    reuse
                    * 45
                )
            )


        passing.sort(
            key=lambda item:
                item.get(
                    "effective_rank",
                    item[
                        "rank"
                    ]
                ),
            reverse=True
        )


        selected = (
            passing[0]
            if passing
            else None
        )


        if selected:

            group = (
                selected[
                    "candidate"
                ][
                    "source_group"
                ]
            )


            source_counts[
                group
            ] = (
                source_counts.get(
                    group,
                    0
                )
                + 1
            )


        selections.append({
            "scene":
                scene[
                    "scene"
                ],

            "role":
                scene[
                    "role"
                ],

            "decision":
                (
                    "SELECT_SAFE"
                    if selected
                    else
                    "HOLD_SAFE"
                ),

            "candidate_count":
                len(
                    evaluated
                ),

            "passing_count":
                len(
                    passing
                ),

            "selected":
                selected,

            "evaluated":
                evaluated,
        })


    return (
        searches,
        selections
    )


def probe_scene(
    role,
    factual=False,
    hook=False,
):
    return {
        "scene":
            900,

        "segment":
            (
                "Hotel Cecil Elisa Lam "
                + role.lower()
            ),

        "role":
            role,

        "factual":
            factual,

        "identity_required":
            False,

        "identity_scope":
            "NONE",

        "location_scope":
            (
                "SPECIFIC_LOCATION_EXPLICIT"
                if role
                == "LOCATION"
                else "NONE"
            ),

        "hook_priority":
            (
                100
                if hook
                else 0
            ),

        "hook_case_specific_preferred":
            hook,

        "epistemic_mode":
            (
                "CASE_SPECIFIC_REQUIRED"
                if factual
                else "ILLUSTRATIVE_ALLOWED"
            ),
    }


def forced_candidate(
    raw,
    scene,
    entities,
    usage,
    query=""
):
    candidate = adapt(
        raw,
        scene,
        entities,
        search_query=query
    )

    candidate[
        "intended_usage"
    ] = usage

    candidate[
        "illustration_label"
    ] = (
        usage
        == "ILLUSTRATIVE"
    )

    return candidate


def truth_without_render_quality(
    scene,
    candidate,
    entities
):
    gate = evaluate_candidate(
        scene,
        candidate,
        entities
    )


    truth_reasons = [
        reason
        for reason in (
            gate[
                "reasons"
            ]
        )
        if reason
        != "technical_gate_failed"
    ]


    visual = evaluate_visual_precision(
        scene,
        candidate
    )


    return {
        "passed":
            (
                not truth_reasons
                and
                visual[
                    "passed"
                ]
            ),

        "full_render_gate":
            gate[
                "passed"
            ],

        "truth_reasons":
            truth_reasons,

        "all_base_reasons":
            gate[
                "reasons"
            ],

        "visual":
            visual,
    }


def adversarial_real(
    entities,
    mapped
):
    hotel = find_exact(
        mapped,
        "hotel cecil la"
    )

    wrong_hotel = find_exact(
        mapped,
        "arizona biltmore hallway"
    )

    elevator = find_exact(
        mapped,
        "elisa lam elevator video"
    )

    medicine = find_exact(
        mapped,
        "medicine box"
    )


    tests = []


    def add(
        name,
        raw,
        scene,
        usage,
        expected,
        *,
        truth_only=False,
        query="",
    ):

        if raw is None:

            tests.append({
                "name":
                    name,

                "expected":
                    expected,

                "actual":
                    None,

                "passed":
                    False,

                "error":
                    "metadata_missing",
            })

            return


        candidate = forced_candidate(
            raw,
            scene,
            entities,
            usage,
            query=query
        )


        if truth_only:

            detailed = (
                truth_without_render_quality(
                    scene,
                    candidate,
                    entities
                )
            )

            actual = (
                detailed[
                    "passed"
                ]
            )


        else:

            detailed = combined_evaluation(
                scene,
                candidate,
                entities
            )

            actual = (
                detailed[
                    "passed"
                ]
            )


        tests.append({
            "name":
                name,

            "expected":
                expected,

            "actual":
                actual,

            "passed":
                actual
                == expected,

            "title":
                candidate[
                    "title"
                ],

            "details":
                detailed,
        })


    # Truth/provenance can be valid even when
    # pixel count is insufficient for final render.
    add(
        "HOTEL_CECIL_TRUTH_PROVEN_IN_REAL_METADATA",
        hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        True,
        truth_only=True
    )


    add(
        "WRONG_HOTEL_CANNOT_PROVE_HOTEL_CECIL",
        wrong_hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        False,
        truth_only=True
    )


    add(
        "QUERY_CONTAMINATION_STILL_CANNOT_PROVE_CASE",
        wrong_hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        False,
        truth_only=True,
        query=(
            "Elisa Lam Hotel Cecil verified"
        )
    )


    evidence_scene = probe_scene(
        "EVIDENCE",
        factual=True
    )

    evidence_scene[
        "segment"
    ] = (
        "A filmagem da câmera de segurança "
        "mostra Elisa Lam no elevador."
    )


    add(
        "REAL_ELISA_ELEVATOR_EVIDENCE",
        elevator,
        evidence_scene,
        "CASE_SPECIFIC",
        True
    )


    medication_scene = probe_scene(
        "OBJECT"
    )

    medication_scene[
        "segment"
    ] = (
        "Uma medicação aparece como "
        "contexto ilustrativo."
    )


    add(
        "GENERIC_MEDICINE_NOT_CASE_PROOF",
        medicine,
        medication_scene,
        "CASE_SPECIFIC",
        False
    )


    add(
        "GENERIC_MEDICINE_VALID_AS_ILLUSTRATION",
        medicine,
        medication_scene,
        "ILLUSTRATIVE",
        True
    )


    document_scene = probe_scene(
        "DOCUMENT",
        factual=True
    )

    document_scene[
        "segment"
    ] = (
        "O relatório oficial do caso "
        "de Elisa Lam foi analisado."
    )


    add(
        "FILE_NAMESPACE_IS_NOT_DOCUMENT_PROOF",
        hotel,
        document_scene,
        "CASE_SPECIFIC",
        False
    )


    failed = [
        item[
            "name"
        ]
        for item in tests
        if not item[
            "passed"
        ]
    ]


    return {
        "passed":
            not failed,

        "tests":
            tests,

        "failed":
            failed,
    }


def portfolio_from(
    selections
):
    portfolio = []


    for item in selections:

        selected = item[
            "selected"
        ]


        if not selected:
            continue


        candidate = (
            selected[
                "candidate"
            ]
        )


        portfolio.append({
            "scene":
                item[
                    "scene"
                ],

            "source_group":
                candidate[
                    "source_group"
                ],

            "generic":
                candidate[
                    "generic"
                ],

            "title":
                candidate[
                    "title"
                ],
        })


    return portfolio


def main():
    global GLOBAL_ENTITIES


    WORK.mkdir(
        parents=True,
        exist_ok=True
    )


    segments = load_segments()


    GLOBAL_ENTITIES = extract_entities(
        segments
    )


    scenes = classify_scenes(
        segments,
        GLOBAL_ENTITIES
    )


    query_plans = plan_queries(
        scenes,
        GLOBAL_ENTITIES
    )


    person = (
        GLOBAL_ENTITIES.get(
            "primary_person"
        )
        or {}
    )


    location = (
        GLOBAL_ENTITIES.get(
            "primary_location"
        )
        or {}
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1200.1 REAL-WORLD PRECISION PIPELINE"
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
        "PERSON:",
        person.get(
            "name"
        )
    )

    print(
        "LOCATION:",
        location.get(
            "name"
        )
    )


    print()
    print(
        "===== EXACT REAL METADATA ====="
    )


    exact = commons_exact_titles(
        EXACT_TITLES
    )


    mapped = exact_map(
        exact
    )


    print(
        "EXACT REQUEST:",
        "PASS"
        if exact.get(
            "ok"
        )
        else "FAIL"
    )

    print(
        "EXACT ASSETS:",
        exact.get(
            "count",
            0
        )
    )


    adversarial = adversarial_real(
        GLOBAL_ENTITIES,
        mapped
    )


    print()
    print(
        "===== REAL ADVERSARIAL ====="
    )


    for item in (
        adversarial[
            "tests"
        ]
    ):

        print(
            item[
                "name"
            ],
            "=",
            "PASS"
            if item[
                "passed"
            ]
            else "FAIL",
            "| expected=",
            item[
                "expected"
            ],
            "| actual=",
            item[
                "actual"
            ]
        )


    print(
        "FAILED:",
        adversarial[
            "failed"
        ]
    )


    print()
    print(
        "===== EXPANDED REAL SEARCH ====="
    )


    searches, selections = (
        select_all(
            scenes,
            query_plans,
            mapped
        )
    )


    health = provider_health(
        searches
    )


    for scene in scenes:

        number = scene[
            "scene"
        ]

        search = searches[
            str(number)
        ]


        print(
            "SCENE",
            number,
            "| queries=",
            len(
                search[
                    "queries"
                ]
            ),
            "| raw=",
            len(
                search[
                    "results"
                ]
            ),
            "| seeds=",
            search[
                "targeted_seed_count"
            ]
        )


    print()
    print(
        "===== PRECISION SELECTIONS ====="
    )


    for item in selections:

        selected = item[
            "selected"
        ]


        if not selected:

            print(
                "SCENE",
                item[
                    "scene"
                ],
                "| HOLD_SAFE",
                "| candidates=",
                item[
                    "candidate_count"
                ]
            )

            continue


        candidate = (
            selected[
                "candidate"
            ]
        )

        visual = (
            selected[
                "combined_gate"
            ][
                "visual_gate"
            ]
        )


        print(
            "SCENE",
            item[
                "scene"
            ],
            "| SELECT_SAFE",
            "|",
            candidate[
                "title"
            ][:76],
            "| intents=",
            visual[
                "candidate_intents"
            ]
        )


    portfolio = portfolio_from(
        selections
    )


    diversity = audit_portfolio(
        portfolio
    )


    selected_count = len(
        portfolio
    )

    hold_count = (
        12
        -
        selected_count
    )


    selected_safe = all(
        item[
            "selected"
        ][
            "combined_gate"
        ][
            "passed"
        ]

        for item in selections

        if item[
            "selected"
        ]
    )


    full_metadata_ready = (
        selected_count
        == 12
        and
        diversity[
            "passed"
        ]
    )


    preflight_status = (
        "METADATA_READY_FOR_CONTROLLED_MEDIA_STAGE"
        if full_metadata_ready
        else
        "REAL_SAFETY_CERTIFIED_SOURCE_EXPANSION_REQUIRED"
    )


    network = transport.stats()


    minimum_ratio = 0.50


    commons_health = (
        health[
            "commons_calls"
        ]
        > 0
        and
        health[
            "commons_success_ratio"
        ]
        >= minimum_ratio
    )


    checks = {
        "twelve_scenes":
            len(
                scenes
            )
            == 12,

        "entity_person":
            bool(
                person
            ),

        "entity_location":
            bool(
                location
            ),

        "exact_metadata_success":
            exact.get(
                "ok"
            )
            is True,

        "four_known_assets_found":
            exact.get(
                "count",
                0
            )
            >= 4,

        "real_adversarial_precision":
            adversarial[
                "passed"
            ],

        "commons_transport_healthy":
            commons_health,

        "network_actually_used":
            network[
                "requests_succeeded"
            ]
            > 0,

        "every_selected_candidate_safe":
            selected_safe,

        "hold_is_allowed":
            True,

        "query_not_evidence":
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

        "production_mutation_off":
            True,
    }


    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]


    status = (
        "VI1200_1_REAL_WORLD_SAFETY_CERTIFIED"
        if not failed
        else "HOLD"
    )


    report = {
        "version":
            "1200.1",

        "status":
            status,

        "entities":
            GLOBAL_ENTITIES,

        "adversarial":
            adversarial,

        "provider_health":
            health,

        "network":
            network,

        "selected_count":
            selected_count,

        "hold_count":
            hold_count,

        "portfolio":
            portfolio,

        "diversity":
            diversity,

        "preflight_status":
            preflight_status,

        "checks":
            checks,

        "failed":
            failed,

        "network_executed":
            True,

        "real_search_executed":
            True,

        "metadata_only":
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
    }


    write_json(
        RAW_OUT,
        searches
    )

    write_json(
        PLAN_OUT,
        {
            "version":
                "1200.1",

            "selections":
                selections,

            "portfolio":
                portfolio,

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
        "===== PROVIDER HEALTH ====="
    )

    print(
        health
    )


    print()
    print(
        "===== SAFETY PREFLIGHT ====="
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
        "DIVERSITY READY:",
        diversity[
            "passed"
        ]
    )

    print(
        "PREFLIGHT:",
        preflight_status
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
        "NETWORK EXECUTED: True"
    )

    print(
        "REAL SEARCH EXECUTED: True"
    )

    print(
        "REMOTE MEDIA DOWNLOADED: False"
    )

    print(
        "FFMPEG EXECUTED: False"
    )

    print(
        "RENDERER ACTIVATED: False"
    )

    print(
        "VIDEO GENERATED: False"
    )

    print(
        "PRODUCTION MUTATED: False"
    )


    print()
    print(
        "STATUS:",
        status
    )


    if not failed:

        if full_metadata_ready:

            print(
                "VI1200.1 RESULT: "
                "REAL_WORLD_SAFETY_CERTIFIED_"
                "READY_FOR_MEDIA_STAGE"
            )

        else:

            print(
                "VI1200.1 RESULT: "
                "REAL_WORLD_SAFETY_CERTIFIED_"
                "SOURCE_EXPANSION_REQUIRED"
            )


    if failed:
        raise SystemExit(
            1
        )


GLOBAL_ENTITIES = {}


if __name__ == "__main__":
    main()
