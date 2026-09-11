#!/usr/bin/env python3

import hashlib
import json
import os

from pathlib import Path


from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
    norm,
)

from vi1000_1_query_gate import (
    plan_queries,
    evaluate_candidate,
    fallback_decision,
    audit_portfolio,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

OUT = (
    BASE
    / "logs/producao"
    / "vi1000_1_full_dry_run_latest.json"
)

DRY = (
    BASE
    / "temp/vi1000_1_dry_run"
)

MOCK = (
    DRY
    / "mock_assets"
)

MOCK_MANIFEST = (
    DRY
    / "mock_manifest.json"
)


def sha256_bytes(
    value
):
    return hashlib.sha256(
        str(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_current_segments():
    blueprint = (
        BASE
        / "temp/vi1000_launch"
        / "launch_blueprint.json"
    )

    if not blueprint.exists():
        raise RuntimeError(
            "vi1000_blueprint_missing"
        )

    data = json.loads(
        blueprint.read_text(
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


def benchmark_current():
    segments = (
        load_current_segments()
    )

    entities = (
        extract_entities(
            segments
        )
    )

    scenes = (
        classify_scenes(
            segments,
            entities
        )
    )

    names = {
        norm(
            item[
                "name"
            ]
        )
        for item in (
            entities[
                "entities"
            ]
        )
    }


    forbidden = {
        "nele",
        "comente",
        "elisa",
        "lam"
    }


    checks = {
        "elisa_lam_canonical":
            "elisa lam"
            in names,

        "hotel_cecil_canonical":
            "hotel cecil"
            in names,

        "false_anchor_fragments_removed":
            not bool(
                names
                &
                forbidden
            ),

        "no_duplicate_canonical_entities":
            len(
                names
            )
            ==
            len(
                entities[
                    "entities"
                ]
            ),
    }


    scene2 = next(
        (
            item
            for item in scenes
            if item[
                "scene"
            ]
            == 2
        ),
        None
    )


    if (
        scene2
        and
        scene2[
            "role"
        ]
        == "HUMAN"
    ):
        checks[
            "scene2_specific_person_hardened"
        ] = (
            scene2[
                "identity_required"
            ]
        )

    else:
        checks[
            "scene2_specific_person_hardened"
        ] = True


    scene10 = next(
        (
            item
            for item in scenes
            if item[
                "scene"
            ]
            == 10
        ),
        None
    )


    if (
        scene10
        and
        scene10[
            "role"
        ]
        == "HUMAN"
        and
        scene10[
            "generic_human"
        ]
    ):
        checks[
            "scene10_generic_group_not_identity"
        ] = (
            not scene10[
                "identity_required"
            ]
        )

    else:
        checks[
            "scene10_generic_group_not_identity"
        ] = True


    return {
        "entities":
            entities,

        "scenes":
            scenes,

        "checks":
            checks,

        "passed":
            all(
                checks.values()
            ),
    }


SYNTHETIC_SEGMENTS = [
    (
        "No Hotel Aurora, na cidade de Porto Azul, "
        "uma câmera do elevador registrou os últimos "
        "minutos antes do desaparecimento."
    ),

    (
        "Em 2024, a estudante Marina Duarte chegou "
        "ao Hotel Aurora para passar três noites."
    ),

    (
        "Naquela noite, hóspedes disseram que o "
        "corredor do oitavo andar estava vazio."
    ),

    (
        "A polícia divulgou imagens da câmera de "
        "segurança mostrando Marina Duarte entrando "
        "no elevador."
    ),

    (
        "Ela entra e sai do elevador várias vezes, "
        "olhando para o corredor."
    ),

    (
        "Minutos depois, uma funcionária caminha "
        "pelo corredor durante a busca."
    ),

    (
        "O elevador continua parado com as portas "
        "abertas por alguns segundos."
    ),

    (
        "Os investigadores confirmaram que a "
        "filmagem pertencia ao Hotel Aurora."
    ),

    (
        "A família informou que Marina Duarte "
        "utilizava medicação prescrita."
    ),

    (
        "Funcionários da manutenção foram chamados "
        "para verificar a cobertura do hotel."
    ),

    (
        "A busca chegou ao topo do prédio e às "
        "estruturas de água."
    ),

    (
        "O relatório oficial encerrou o caso com "
        "uma conclusão registrada pela perícia."
    )
]


def candidate_for_scene(
    scene,
    entities
):
    person = (
        entities.get(
            "primary_person"
        )
        or {}
    ).get(
        "name"
    ) or "Marina Duarte"

    location = (
        entities.get(
            "primary_location"
        )
        or {}
    ).get(
        "name"
    ) or "Hotel Aurora"


    generic = False


    if scene[
        "identity_required"
    ]:
        evidence = (
            f"verified archival image of {person}"
        )

        mentions = [
            person
        ]

        usage = (
            "CASE_SPECIFIC"
        )


    elif scene[
        "factual"
    ]:
        if scene[
            "role"
        ] == "DOCUMENT":
            evidence = (
                f"official report document concerning "
                f"{person} and {location}"
            )

        elif scene[
            "role"
        ] == "EVIDENCE":
            evidence = (
                f"{location} surveillance footage evidence "
                f"connected to {person}"
            )

        else:
            evidence = (
                f"{location} investigation context "
                f"connected to {person}"
            )

        mentions = [
            person,
            location
        ]

        usage = (
            "CASE_SPECIFIC"
        )


    elif (
        scene[
            "hook_priority"
        ]
        == 100
    ):
        evidence = (
            f"verified {location} elevator and building context"
        )

        mentions = [
            location
        ]

        usage = (
            "CASE_SPECIFIC"
        )


    else:
        evidence = (
            "licensed documentary b-roll "
            + scene[
                "role"
            ].lower()
        )

        mentions = []

        usage = (
            "ILLUSTRATIVE"
        )

        generic = True


    role_tags = [
        scene[
            "role"
        ]
    ]


    if (
        scene[
            "role"
        ]
        == "EVIDENCE"
    ):
        role_tags.append(
            "EVIDENCE"
        )


    if (
        scene[
            "role"
        ]
        == "DOCUMENT"
    ):
        role_tags.append(
            "DOCUMENT"
        )


    source_group = (
        {
            1:
                "verified_hotel_aurora",

            2:
                "marina_duarte_archive",

            3:
                "corridor_generic_a",

            4:
                "case_evidence_a",

            5:
                "elevator_generic_a",

            6:
                "anonymous_human_a",

            7:
                "elevator_generic_b",

            8:
                "case_evidence_b",

            9:
                "medication_generic_a",

            10:
                "maintenance_context_a",

            11:
                "rooftop_generic_a",

            12:
                "case_document_a",
        }[
            scene[
                "scene"
            ]
        ]
    )


    return {
        "title":
            (
                "Dry candidate "
                + str(
                    scene[
                        "scene"
                    ]
                )
            ),

        "evidence_text":
            evidence,

        "entity_mentions":
            mentions,

        "role_tags":
            role_tags,

        "license":
            "CC BY 4.0",

        "family":
            (
                "VIDEO"
                if scene[
                    "role"
                ]
                == "EVIDENCE"
                else "IMAGE"
            ),

        "width":
            1080,

        "height":
            1920,

        "intended_usage":
            usage,

        "illustration_label":
            generic,

        "source_group":
            source_group,

        "generic":
            generic,

        "sha256":
            sha256_bytes(
                source_group
                + ":"
                + str(
                    scene[
                        "scene"
                    ]
                )
            ),
    }


def synthetic_run():
    entities = extract_entities(
        SYNTHETIC_SEGMENTS
    )

    scenes = classify_scenes(
        SYNTHETIC_SEGMENTS,
        entities
    )

    queries = plan_queries(
        scenes,
        entities
    )


    gates = []

    portfolio = []

    decisions = []


    for scene in scenes:
        candidate = candidate_for_scene(
            scene,
            entities
        )

        evaluation = (
            evaluate_candidate(
                scene,
                candidate,
                entities
            )
        )

        decision = fallback_decision([
            {
                "candidate":
                    candidate,

                "evaluation":
                    evaluation,
            }
        ])


        gates.append({
            "scene":
                scene[
                    "scene"
                ],

            "passed":
                evaluation[
                    "passed"
                ],

            "evaluation":
                evaluation,
        })


        decisions.append({
            "scene":
                scene[
                    "scene"
                ],

            "decision":
                decision[
                    "decision"
                ],

            "tier":
                decision[
                    "tier"
                ],
        })


        portfolio.append({
            "scene":
                scene[
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

            "sha256":
                candidate[
                    "sha256"
                ],

            "title":
                candidate[
                    "title"
                ],
        })


    diversity = audit_portfolio(
        portfolio
    )


    return {
        "entities":
            entities,

        "scenes":
            scenes,

        "queries":
            queries,

        "gates":
            gates,

        "decisions":
            decisions,

        "portfolio":
            portfolio,

        "diversity":
            diversity,

        "all_candidate_gates_pass":
            all(
                item[
                    "passed"
                ]
                for item in gates
            ),

        "all_fallbacks_select":
            all(
                item[
                    "decision"
                ]
                == "SELECT"
                for item in decisions
            ),
    }


def runtime_contract(
    synthetic
):
    MOCK.mkdir(
        parents=True,
        exist_ok=True
    )


    scenes = {}


    for scene in (
        synthetic[
            "scenes"
        ]
    ):
        number = scene[
            "scene"
        ]

        mock = (
            MOCK
            / f"scene_{number:02d}.mock"
        )

        mock.write_text(
            f"VI1000.1 MOCK SCENE {number}\n",
            encoding="utf-8"
        )


        digest = hashlib.sha256(
            mock.read_bytes()
        ).hexdigest()


        scenes[
            str(number)
        ] = {
            "scene":
                number,

            "original_path":
                str(
                    BASE
                    / "imagens"
                    / "dry_run"
                    / f"scene_{number:02d}.jpg"
                ),

            "override_active":
                True,

            "canary_path":
                str(
                    mock
                ),

            "expected_sha256":
                digest,

            "mode":
                "VI1000_1_DRY_RUN_ONLY",
        }


    manifest = {
        "version":
            "1000.1",

        "short_id":
            "SYNTHETIC_DRY_RUN",

        "active_override_scenes":
            list(
                range(
                    1,
                    13
                )
            ),

        "scenes":
            scenes,

        "dry_run_only":
            True,
    }


    MOCK_MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    os.environ[
        "VI1000_MODE"
    ] = "ON"

    os.environ[
        "VI1000_MANIFEST"
    ] = str(
        MOCK_MANIFEST
    )


    import vi1000_runtime
    import vi1000_command_hook


    validation = (
        vi1000_runtime
        .validate_manifest()
    )

    synthetic_hook = (
        vi1000_command_hook
        .synthetic_test()
    )


    rewrite_ok = all(
        item[
            "matches"
        ]
        ==
        [
            item[
                "scene"
            ]
        ]

        for item in synthetic_hook
    )


    return {
        "manifest_valid":
            validation[
                "valid"
            ],

        "active_scenes":
            validation[
                "active_scenes"
            ],

        "synthetic_hook_count":
            len(
                synthetic_hook
            ),

        "every_scene_rewrites":
            rewrite_ok,

        "passed":
            (
                validation[
                    "valid"
                ]
                and
                len(
                    synthetic_hook
                )
                == 12
                and
                rewrite_ok
            ),
    }


def main():
    benchmark = (
        benchmark_current()
    )

    synthetic = (
        synthetic_run()
    )

    runtime = runtime_contract(
        synthetic
    )


    checks = {
        "benchmark_entity_resolution":
            benchmark[
                "passed"
            ],

        "synthetic_entity_resolution":
            bool(
                synthetic[
                    "entities"
                ][
                    "primary_person"
                ]
                and
                synthetic[
                    "entities"
                ][
                    "primary_location"
                ]
            ),

        "synthetic_candidate_gates":
            synthetic[
                "all_candidate_gates_pass"
            ],

        "synthetic_fallbacks":
            synthetic[
                "all_fallbacks_select"
            ],

        "synthetic_diversity":
            synthetic[
                "diversity"
            ][
                "passed"
            ],

        "runtime_contract":
            runtime[
                "passed"
            ],

        "query_is_never_evidence":
            all(
                item[
                    "query_is_evidence"
                ]
                is False

                for item in (
                    synthetic[
                        "queries"
                    ]
                )
            ),
    }


    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]


    report = {
        "version":
            "1000.1",

        "status":
            (
                "VI1000_1_FULL_DRY_RUN_CERTIFIED"
                if not failed
                else "HOLD"
            ),

        "benchmark":
            benchmark,

        "synthetic":
            synthetic,

        "runtime":
            runtime,

        "checks":
            checks,

        "failed":
            failed,

        "network_executed":
            False,

        "downloads_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "renderer_activation":
            False,

        "production_mutation":
            False,
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
        " VI1000.1 FULL DRY-RUN"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        report[
            "status"
        ]
    )


    print()
    print(
        "===== CURRENT BENCHMARK ENTITIES ====="
    )

    for entity in (
        benchmark[
            "entities"
        ][
            "entities"
        ]
    ):
        print(
            entity[
                "type"
            ],
            "|",
            entity[
                "name"
            ],
            "| confidence=",
            entity[
                "confidence"
            ]
        )


    print(
        "BENCHMARK CHECKS:",
        benchmark[
            "checks"
        ]
    )


    print()
    print(
        "===== NEW SYNTHETIC SHORT ====="
    )

    print(
        "PRIMARY PERSON:",
        synthetic[
            "entities"
        ][
            "primary_person"
        ]
    )

    print(
        "PRIMARY LOCATION:",
        synthetic[
            "entities"
        ][
            "primary_location"
        ]
    )


    for scene in (
        synthetic[
            "scenes"
        ]
    ):
        print(
            "SCENE",
            scene[
                "scene"
            ],
            "| role=",
            scene[
                "role"
            ],
            "| factual=",
            scene[
                "factual"
            ],
            "| identity=",
            scene[
                "identity_scope"
            ],
            "| location=",
            scene[
                "location_scope"
            ]
        )


    print()
    print(
        "CANDIDATE GATES:",
        synthetic[
            "all_candidate_gates_pass"
        ]
    )

    print(
        "FALLBACKS:",
        synthetic[
            "all_fallbacks_select"
        ]
    )

    print(
        "DIVERSITY:",
        synthetic[
            "diversity"
        ]
    )

    print(
        "RUNTIME:",
        runtime
    )


    print()
    print(
        "CHECKS:"
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
        "NETWORK EXECUTED: False"
    )

    print(
        "DOWNLOADS EXECUTED: False"
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


if __name__ == "__main__":
    main()
