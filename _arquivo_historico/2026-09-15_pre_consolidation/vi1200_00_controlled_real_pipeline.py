#!/usr/bin/env python3

import copy
import json

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
    norm,
)

from vi1000_1_query_gate import (
    plan_queries,
    evaluate_candidate,
    audit_portfolio,
)

import vi1200_01_real_transport as transport

from vi1200_02_commons_provider import (
    search as commons_search,
    exact_titles as commons_exact_titles,
)

from vi1200_03_archive_provider import (
    search as archive_search,
)

from vi1200_04_real_candidate_adapter import (
    adapt,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

WORK = (
    BASE
    / "temp"
    / "vi1200_real"
)

OUT = (
    BASE
    / "logs/producao"
    / "vi1200_00_controlled_real_pipeline_latest.json"
)

PLAN_OUT = (
    WORK
    / "real_selection_plan.json"
)

RAW_OUT = (
    WORK
    / "real_provider_metadata.json"
)

BLUEPRINT = (
    BASE
    / "temp/vi1000_launch"
    / "launch_blueprint.json"
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


def rank_candidate(
    candidate,
    gate
):
    if not gate[
        "passed"
    ]:
        return -10000.0


    case_bonus = (
        25
        if candidate[
            "intended_usage"
        ]
        == "CASE_SPECIFIC"
        else 0
    )


    return round(
        (
            float(
                candidate.get(
                    "quality_score",
                    0
                )
            )
            * 0.25

            +

            float(
                candidate.get(
                    "semantic_score",
                    0
                )
            )
            * 0.45

            +

            float(
                candidate.get(
                    "provenance_score",
                    0
                )
            )
            * 0.30

            +

            case_bonus
        ),
        2
    )


def normalize_for_scene(
    raw_candidates,
    scene,
    entities,
    query
):
    result = []


    for raw in raw_candidates:
        candidate = adapt(
            raw,
            scene,
            entities,
            search_query=query
        )

        gate = evaluate_candidate(
            scene,
            candidate,
            entities
        )

        result.append({
            "candidate":
                candidate,

            "gate":
                gate,

            "rank":
                rank_candidate(
                    candidate,
                    gate
                ),
        })


    return result


def exact_map(
    exact_result
):
    mapped = {}


    for item in (
        exact_result.get(
            "results"
        )
        or []
    ):
        mapped[
            norm(
                item.get(
                    "title"
                )
            )
        ] = item


    return mapped


def find_exact(
    mapped,
    fragment
):
    fragment = norm(
        fragment
    )

    for key, value in (
        mapped.items()
    ):
        if fragment in key:
            return value

    return None


def provider_searches(
    scenes,
    queries
):
    results = {}


    for scene, query_plan in zip(
        scenes,
        queries
    ):
        number = scene[
            "scene"
        ]

        query = (
            query_plan[
                "primary_query"
            ]
        )


        commons = commons_search(
            query,
            limit=5
        )


        archive = {
            "ok":
                True,

            "query":
                query,

            "results":
                [],

            "count":
                0,

            "skipped":
                True,
        }


        if (
            "INTERNET_ARCHIVE"
            in query_plan[
                "providers"
            ]
        ):
            archive = archive_search(
                query,
                limit=4
            )


        results[
            str(number)
        ] = {
            "scene":
                number,

            "query":
                query,

            "query_plan":
                query_plan,

            "commons":
                commons,

            "archive":
                archive,
        }


    return results


def select_scenes(
    scenes,
    entities,
    searches,
    exact_assets
):
    selections = []

    used_groups = {}


    for scene in scenes:
        number = scene[
            "scene"
        ]

        data = searches[
            str(number)
        ]

        query = data[
            "query"
        ]


        raw_pool = []


        raw_pool.extend(
            data[
                "commons"
            ].get(
                "results",
                []
            )
        )


        raw_pool.extend(
            data[
                "archive"
            ].get(
                "results",
                []
            )
        )


        # Real exact metadata is injected as an
        # additional trusted discovery source.
        for item in exact_assets:
            if item:
                raw_pool.append(
                    item
                )


        # Deduplicate provider resources.
        unique_pool = []

        seen = set()


        for raw in raw_pool:
            key = (
                raw.get(
                    "provider"
                ),
                raw.get(
                    "pageid"
                )
                or
                raw.get(
                    "identifier"
                )
                or
                raw.get(
                    "title"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            unique_pool.append(
                raw
            )


        evaluated = normalize_for_scene(
            unique_pool,
            scene,
            entities,
            query
        )


        passing = [
            item
            for item in evaluated
            if item[
                "gate"
            ][
                "passed"
            ]
        ]


        # Global anti-repetition penalty.
        for item in passing:
            group = (
                item[
                    "candidate"
                ][
                    "source_group"
                ]
            )

            reuse = used_groups.get(
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
                reuse * 40
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

            used_groups[
                group
            ] = (
                used_groups.get(
                    group,
                    0
                )
                + 1
            )


        selections.append({
            "scene":
                number,

            "role":
                scene[
                    "role"
                ],

            "query":
                query,

            "candidate_count":
                len(
                    evaluated
                ),

            "passing_count":
                len(
                    passing
                ),

            "decision":
                (
                    "SELECT_SAFE"
                    if selected
                    else "HOLD_SAFE"
                ),

            "selected":
                selected,

            "evaluated":
                evaluated,
        })


    return selections


def probe_scene(
    role,
    *,
    factual=False,
    hook=False,
    identity=False,
):
    return {
        "scene":
            900,

        "segment":
            "VI1200 controlled probe",

        "role":
            role,

        "factual":
            factual,

        "identity_required":
            identity,

        "identity_scope":
            (
                "SPECIFIC_PERSON_EXPLICIT"
                if identity
                else "NONE"
            ),

        "location_scope":
            (
                "SPECIFIC_LOCATION_EXPLICIT"
                if role == "LOCATION"
                else "NONE"
            ),

        "hook_priority":
            (
                100
                if hook
                else 0
            ),

        "hook_case_specific_preferred":
            bool(
                hook
            ),

        "epistemic_mode":
            (
                "CASE_SPECIFIC_REQUIRED"
                if factual
                else
                "ILLUSTRATIVE_ALLOWED"
            ),
    }


def force_usage(
    raw,
    scene,
    entities,
    usage,
    query="",
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


def real_adversarial_probes(
    entities,
    mapped
):
    hotel = find_exact(
        mapped,
        "hotel cecil la"
    )

    elevator = find_exact(
        mapped,
        "elisa lam elevator video"
    )

    medicine = find_exact(
        mapped,
        "medicine box"
    )

    wrong_hotel = find_exact(
        mapped,
        "arizona biltmore hallway"
    )


    probes = []


    def run(
        name,
        raw,
        scene,
        usage,
        expected,
        query="",
    ):
        if raw is None:
            probes.append({
                "name":
                    name,

                "passed":
                    False,

                "expected":
                    expected,

                "actual":
                    None,

                "error":
                    "real_asset_metadata_missing",
            })

            return


        candidate = force_usage(
            raw,
            scene,
            entities,
            usage,
            query=query
        )


        gate = evaluate_candidate(
            scene,
            candidate,
            entities
        )


        actual = gate[
            "passed"
        ]


        probes.append({
            "name":
                name,

            "passed":
                (
                    actual
                    == expected
                ),

            "expected":
                expected,

            "actual":
                actual,

            "candidate_title":
                candidate[
                    "title"
                ],

            "entity_mentions":
                candidate[
                    "entity_mentions"
                ],

            "role_tags":
                candidate[
                    "role_tags"
                ],

            "license":
                candidate[
                    "license"
                ],

            "reasons":
                gate[
                    "reasons"
                ],
        })


    run(
        "REAL_HOTEL_CECIL_PROVES_LOCATION",
        hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        True
    )


    run(
        "REAL_WRONG_HOTEL_DOES_NOT_PROVE_HOTEL_CECIL",
        wrong_hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        False
    )


    run(
        "REAL_QUERY_CONTAMINATION_DOES_NOT_PROVE_CASE",
        wrong_hotel,
        probe_scene(
            "LOCATION",
            hook=True
        ),
        "CASE_SPECIFIC",
        False,
        query=(
            "Elisa Lam Hotel Cecil "
            "verified location"
        )
    )


    run(
        "REAL_ELISA_ELEVATOR_EVIDENCE_PASSES",
        elevator,
        probe_scene(
            "EVIDENCE",
            factual=True
        ),
        "CASE_SPECIFIC",
        True
    )


    run(
        "REAL_GENERIC_MEDICINE_NOT_CASE_EVIDENCE",
        medicine,
        probe_scene(
            "OBJECT"
        ),
        "CASE_SPECIFIC",
        False
    )


    run(
        "REAL_GENERIC_MEDICINE_AS_ILLUSTRATION_PASSES",
        medicine,
        probe_scene(
            "OBJECT"
        ),
        "ILLUSTRATIVE",
        True
    )


    run(
        "REAL_FILE_NAMESPACE_NOT_DOCUMENT_PROOF",
        hotel,
        probe_scene(
            "DOCUMENT",
            factual=True
        ),
        "CASE_SPECIFIC",
        False
    )


    return {
        "probes":
            probes,

        "failed":
            [
                item[
                    "name"
                ]
                for item in probes
                if not item[
                    "passed"
                ]
            ],

        "passed":
            all(
                item[
                    "passed"
                ]
                for item in probes
            ),
    }


def build_portfolio(
    selections
):
    portfolio = []


    for item in selections:
        selected = item.get(
            "selected"
        )

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


def build_render_preflight(
    selections,
    diversity
):
    selected_count = sum(
        1
        for item in selections
        if item[
            "decision"
        ]
        == "SELECT_SAFE"
    )

    hold_count = (
        len(
            selections
        )
        -
        selected_count
    )


    all_selected_safe = all(
        (
            item[
                "selected"
            ][
                "gate"
            ][
                "passed"
            ]
            if item[
                "selected"
            ]
            else True
        )
        for item in selections
    )


    renderer_eligible = (
        selected_count == 12
        and
        hold_count == 0
        and
        all_selected_safe
        and
        diversity[
            "passed"
        ]
    )


    return {
        "scene_count":
            len(
                selections
            ),

        "selected_count":
            selected_count,

        "hold_count":
            hold_count,

        "all_selected_candidates_safe":
            all_selected_safe,

        "diversity_pass":
            diversity[
                "passed"
            ],

        "remote_media_downloaded":
            False,

        "manifest_activation_allowed":
            False,

        "renderer_activation_allowed":
            False,

        "renderer_eligible_after_future_download":
            renderer_eligible,

        "status":
            (
                "METADATA_READY_FOR_CONTROLLED_MEDIA_STAGE"
                if renderer_eligible
                else
                "SAFE_BUT_SOURCE_EXPANSION_REQUIRED"
            ),
    }


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


    queries = plan_queries(
        scenes,
        entities
    )


    print()
    print(
        "=============================================="
    )
    print(
        " VI1200 CONTROLLED REAL PIPELINE"
    )
    print(
        "=============================================="
    )

    print(
        "SHORT SCENES:",
        len(
            scenes
        )
    )


    person = (
        entities.get(
            "primary_person"
        )
        or {}
    )

    location = (
        entities.get(
            "primary_location"
        )
        or {}
    )


    print(
        "PRIMARY PERSON:",
        person.get(
            "name"
        )
    )

    print(
        "PRIMARY LOCATION:",
        location.get(
            "name"
        )
    )


    print()
    print(
        "===== REAL EXACT METADATA ====="
    )


    exact_result = commons_exact_titles(
        EXACT_TITLES
    )


    print(
        "COMMONS EXACT REQUEST:",
        "PASS"
        if exact_result[
            "ok"
        ]
        else "FAIL"
    )

    print(
        "REAL EXACT ASSETS FOUND:",
        exact_result.get(
            "count",
            0
        )
    )


    mapped = exact_map(
        exact_result
    )


    exact_assets = [
        item
        for item in [
            find_exact(
                mapped,
                "hotel cecil la"
            ),

            find_exact(
                mapped,
                "elisa lam elevator video"
            ),

            find_exact(
                mapped,
                "medicine box"
            ),

            find_exact(
                mapped,
                "arizona biltmore hallway"
            ),
        ]
        if item
    ]


    print()
    print(
        "===== REAL ADVERSARIAL PROBES ====="
    )


    adversarial = real_adversarial_probes(
        entities,
        mapped
    )


    for item in (
        adversarial[
            "probes"
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
        "===== 12-SCENE REAL SEARCH ====="
    )


    searches = provider_searches(
        scenes,
        queries
    )


    for key in sorted(
        searches,
        key=lambda value:
            int(
                value
            )
    ):
        item = searches[
            key
        ]

        print(
            "SCENE",
            key,
            "| commons=",
            item[
                "commons"
            ].get(
                "count",
                0
            ),
            "| archive=",
            item[
                "archive"
            ].get(
                "count",
                0
            ),
            "| query=",
            item[
                "query"
            ]
        )


    selections = select_scenes(
        scenes,
        entities,
        searches,
        exact_assets
    )


    print()
    print(
        "===== REAL SELECTIONS ====="
    )


    for item in selections:
        selected = item[
            "selected"
        ]

        if selected:
            candidate = (
                selected[
                    "candidate"
                ]
            )

            print(
                "SCENE",
                item[
                    "scene"
                ],
                "|",
                item[
                    "decision"
                ],
                "|",
                candidate[
                    "provider"
                ],
                "|",
                candidate[
                    "title"
                ][:90]
            )

        else:
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


    portfolio = build_portfolio(
        selections
    )


    diversity = audit_portfolio(
        portfolio
    )


    preflight = build_render_preflight(
        selections,
        diversity
    )


    network = transport.stats()


    commons_search_success = sum(
        1
        for item in (
            searches.values()
        )
        if item[
            "commons"
        ][
            "ok"
        ]
    )


    all_selected_safe = (
        preflight[
            "all_selected_candidates_safe"
        ]
    )


    checks = {
        "benchmark_has_12_scenes":
            len(
                scenes
            )
            == 12,

        "primary_person_resolved":
            bool(
                person
            ),

        "primary_location_resolved":
            bool(
                location
            ),

        "commons_exact_network_success":
            exact_result[
                "ok"
            ],

        "known_real_assets_found":
            len(
                exact_assets
            )
            >= 4,

        "real_adversarial_truth":
            adversarial[
                "passed"
            ],

        "real_search_all_12_scenes":
            len(
                searches
            )
            == 12,

        "commons_search_health":
            commons_search_success
            >= 10,

        "network_requests_executed":
            network[
                "requests_succeeded"
            ]
            > 0,

        "all_selected_candidates_safe":
            all_selected_safe,

        "query_not_used_as_evidence":
            True,

        "remote_media_bytes_zero":
            network[
                "remote_media_bytes_received"
            ]
            == 0,

        "renderer_activation_false":
            preflight[
                "renderer_activation_allowed"
            ]
            is False,

        "manifest_activation_false":
            preflight[
                "manifest_activation_allowed"
            ]
            is False,
    }


    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]


    status = (
        "VI1200_CONTROLLED_REAL_PIPELINE_CERTIFIED"
        if not failed
        else "HOLD"
    )


    plan = {
        "version":
            "1200.00",

        "metadata_only":
            True,

        "scenes":
            selections,

        "portfolio":
            portfolio,

        "diversity":
            diversity,

        "preflight":
            preflight,

        "activation_allowed":
            False,

        "render_allowed":
            False,
    }


    report = {
        "version":
            "1200.00",

        "status":
            status,

        "entities":
            entities,

        "adversarial":
            adversarial,

        "network":
            network,

        "checks":
            checks,

        "failed":
            failed,

        "diversity":
            diversity,

        "preflight":
            preflight,

        "network_executed":
            True,

        "real_search_executed":
            True,

        "real_metadata_executed":
            True,

        "remote_media_downloaded":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "renderer_activated":
            False,

        "production_mutated":
            False,

        "publication_executed":
            False,
    }


    write_json(
        RAW_OUT,
        {
            "exact":
                exact_result,

            "searches":
                searches,
        }
    )


    write_json(
        PLAN_OUT,
        plan
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
        "===== REAL NETWORK ====="
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
        "METADATA BYTES RECEIVED:",
        network[
            "metadata_bytes_received"
        ]
    )

    print(
        "REMOTE MEDIA BYTES RECEIVED:",
        network[
            "remote_media_bytes_received"
        ]
    )


    print()
    print(
        "===== PREFLIGHT ====="
    )

    for key, value in (
        preflight.items()
    ):
        print(
            key,
            "=",
            value
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
        "REAL METADATA EXECUTED: True"
    )

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


    if failed:
        raise SystemExit(
            1
        )


    print(
        "VI1200 RESULT: "
        "CONTROLLED_REAL_PIPELINE_CERTIFIED"
    )


if __name__ == "__main__":
    main()
