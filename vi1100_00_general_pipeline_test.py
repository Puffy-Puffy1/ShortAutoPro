#!/usr/bin/env python3

import copy
import hashlib
import importlib
import json
import os
import sys

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


VERSION = "1100.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

WORK = (
    BASE
    / "temp/vi1100_general"
)

MOCK_ROOT = (
    WORK
    / "mock_assets"
)

MANIFEST_ROOT = (
    WORK
    / "manifests"
)

OUT = (
    BASE
    / "logs/producao"
    / "vi1100_00_general_pipeline_test_latest.json"
)

VI1000_REPORT = (
    BASE
    / "logs/producao"
    / "vi1000_1_full_dry_run_latest.json"
)

ADVERSARIAL_REPORT = (
    BASE
    / "logs/producao"
    / "vi1000_1_adversarial_suite_latest.json"
)

VIDEO_PY = (
    BASE
    / "video.py"
)

EXECUTOR_PY = (
    BASE
    / "vi6_95_scene_executor.py"
)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def load_json(path):
    return json.loads(
        path.read_text(
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


def digest_text(value):
    return hashlib.sha256(
        str(value).encode(
            "utf-8"
        )
    ).hexdigest()


def result(
    passed,
    **kwargs
):
    return {
        "passed":
            bool(passed),

        **kwargs,
    }


STORIES = {
    "HOTEL_AURORA": [
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
    ],


    "HOSPITAL_SANTA_CLARA": [
        (
            "No Hospital Santa Clara, uma câmera do "
            "corredor registrou movimentação durante a madrugada."
        ),
        (
            "O técnico Rafael Nunes chegou ao "
            "Hospital Santa Clara pouco antes da meia-noite."
        ),
        (
            "O corredor do setor antigo estava quase vazio."
        ),
        (
            "A polícia analisou a filmagem da câmera "
            "de segurança ligada ao desaparecimento de Rafael Nunes."
        ),
        (
            "Rafael Nunes aparece caminhando pelo corredor."
        ),
        (
            "Depois disso, uma funcionária passa pelo local."
        ),
        (
            "Uma porta permanece aberta por vários segundos."
        ),
        (
            "Investigadores confirmaram que as imagens "
            "pertenciam ao Hospital Santa Clara."
        ),
        (
            "Entre os objetos analisados havia uma mochila."
        ),
        (
            "Funcionários verificaram outras áreas do prédio."
        ),
        (
            "A busca chegou ao último andar da construção."
        ),
        (
            "O relatório oficial registrou a conclusão "
            "da investigação sobre Rafael Nunes."
        )
    ],


    "UNIVERSITY_NORTHBRIDGE": [
        (
            "Na University Northbridge, uma câmera do "
            "elevador registrou uma sequência incomum."
        ),
        (
            "A estudante Clara Mendes chegou à "
            "University Northbridge no início da noite."
        ),
        (
            "O corredor principal estava praticamente vazio."
        ),
        (
            "A polícia divulgou a filmagem de segurança "
            "mostrando Clara Mendes perto do elevador."
        ),
        (
            "Clara Mendes aparece olhando para o corredor."
        ),
        (
            "Mais tarde, uma pessoa atravessa o corredor."
        ),
        (
            "As portas do elevador permanecem abertas."
        ),
        (
            "Investigadores confirmaram que a gravação "
            "era da University Northbridge."
        ),
        (
            "Um objeto pessoal foi citado durante a busca."
        ),
        (
            "Funcionários percorrem outras partes do prédio."
        ),
        (
            "A investigação chegou ao topo da construção."
        ),
        (
            "O relatório oficial registrou a conclusão "
            "do caso envolvendo Clara Mendes."
        )
    ],
}


def primary_names(
    entities
):
    person = (
        entities.get(
            "primary_person"
        )
        or {}
    ).get(
        "name"
    ) or ""

    location = (
        entities.get(
            "primary_location"
        )
        or {}
    ).get(
        "name"
    ) or ""

    return (
        person,
        location
    )


def role_tags_for(
    scene
):
    role = scene[
        "role"
    ]

    if role == "DOCUMENT":
        return [
            "DOCUMENT"
        ]

    if role == "EVIDENCE":
        return [
            "EVIDENCE"
        ]

    if role == "OBJECT":
        return [
            "OBJECT"
        ]

    if role == "HUMAN":
        return [
            "HUMAN"
        ]

    if role == "LOCATION":
        return [
            "LOCATION"
        ]

    return [
        "CONTEXT"
    ]


def good_candidate(
    story_name,
    scene,
    entities
):
    person, location = (
        primary_names(
            entities
        )
    )

    number = scene[
        "scene"
    ]

    role = scene[
        "role"
    ]

    tags = role_tags_for(
        scene
    )

    generic = False


    if scene[
        "identity_required"
    ]:
        evidence = (
            f"verified archival photograph of {person}"
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
        evidence = (
            f"verified investigation material concerning "
            f"{person} and {location}"
        )

        mentions = [
            person,
            location
        ]

        usage = (
            "CASE_SPECIFIC"
        )

        if role == "DOCUMENT":
            evidence += (
                " official report document"
            )

        elif role == "EVIDENCE":
            evidence += (
                " surveillance footage evidence"
            )


    elif scene[
        "hook_priority"
    ] == 100:
        evidence = (
            f"verified visual context of {location}"
        )

        mentions = [
            location
        ]

        usage = (
            "CASE_SPECIFIC"
        )


    else:
        evidence = (
            "licensed documentary illustrative "
            + role.lower()
            + " b-roll"
        )

        mentions = []

        usage = (
            "ILLUSTRATIVE"
        )

        generic = True


    source_group = (
        story_name.lower()
        + "_scene_"
        + f"{number:02d}"
    )


    return {
        "candidate_id":
            (
                story_name
                + "_GOOD_"
                + str(number)
            ),

        "title":
            (
                "Verified candidate "
                + str(number)
            ),

        "evidence_text":
            evidence,

        "entity_mentions":
            mentions,

        "role_tags":
            tags,

        "license":
            "CC BY 4.0",

        "family":
            (
                "VIDEO"
                if role
                == "EVIDENCE"
                else "IMAGE"
            ),

        "width":
            1200,

        "height":
            1800,

        "intended_usage":
            usage,

        "illustration_label":
            generic,

        "source_group":
            source_group,

        "generic":
            generic,

        "quality_score":
            94,

        "semantic_score":
            96,

        "provenance_score":
            95,
    }


def bad_query_contaminated_candidate(
    story_name,
    scene,
    entities
):
    person, location = (
        primary_names(
            entities
        )
    )

    return {
        "candidate_id":
            story_name
            + "_QUERY_TRAP_"
            + str(
                scene[
                    "scene"
                ]
            ),

        "title":
            "Unrelated generic media",

        "evidence_text":
            "generic unrelated stock image",

        "entity_mentions":
            [],

        "role_tags":
            role_tags_for(
                scene
            ),

        "license":
            "CC BY 4.0",

        "family":
            "IMAGE",

        "width":
            1400,

        "height":
            1800,

        "intended_usage":
            "CASE_SPECIFIC",

        "illustration_label":
            False,

        # This MUST NOT become evidence.
        "search_query":
            f"{person} {location}",

        "source_group":
            story_name.lower()
            + "_query_trap",

        "generic":
            False,

        "quality_score":
            95,

        "semantic_score":
            10,

        "provenance_score":
            15,
    }


def bad_unlabeled_candidate(
    story_name,
    scene
):
    return {
        "candidate_id":
            story_name
            + "_UNLABELED_"
            + str(
                scene[
                    "scene"
                ]
            ),

        "title":
            "Generic illustrative candidate",

        "evidence_text":
            (
                "generic documentary "
                + scene[
                    "role"
                ].lower()
            ),

        "entity_mentions":
            [],

        "role_tags":
            role_tags_for(
                scene
            ),

        "license":
            "CC BY 4.0",

        "family":
            "IMAGE",

        "width":
            1200,

        "height":
            1800,

        "intended_usage":
            "ILLUSTRATIVE",

        "illustration_label":
            False,

        "source_group":
            story_name.lower()
            + "_unlabeled_trap",

        "generic":
            True,

        "quality_score":
            87,

        "semantic_score":
            60,

        "provenance_score":
            90,
    }


def candidate_rank(
    candidate,
    evaluation
):
    if not evaluation[
        "passed"
    ]:
        return -10000


    usage = str(
        candidate.get(
            "intended_usage"
        )
        or ""
    ).upper()


    tier_bonus = (
        30
        if usage == "CASE_SPECIFIC"
        else 10
    )


    quality = float(
        candidate.get(
            "quality_score"
        )
        or 0
    )

    semantic = float(
        candidate.get(
            "semantic_score"
        )
        or 0
    )

    provenance = float(
        candidate.get(
            "provenance_score"
        )
        or 0
    )


    return round(
        (
            quality * 0.25
            +
            semantic * 0.45
            +
            provenance * 0.30
            +
            tier_bonus
        ),
        2
    )


def select_candidate(
    scene,
    candidates,
    entities
):
    evaluated = []


    for candidate in candidates:
        gate = evaluate_candidate(
            scene,
            candidate,
            entities
        )

        score = candidate_rank(
            candidate,
            gate
        )

        evaluated.append({
            "candidate":
                candidate,

            "evaluation":
                gate,

            "rank":
                score,
        })


    passing = [
        item
        for item in evaluated
        if item[
            "evaluation"
        ][
            "passed"
        ]
    ]


    passing.sort(
        key=lambda item:
            item[
                "rank"
            ],
        reverse=True
    )


    if not passing:
        return {
            "decision":
                "HOLD_SCENE",

            "selected":
                None,

            "evaluated":
                evaluated,
        }


    selected = passing[0]


    usage = str(
        selected[
            "candidate"
        ].get(
            "intended_usage"
        )
        or ""
    ).upper()


    tier = (
        "CASE_SPECIFIC_VERIFIED"
        if usage
        == "CASE_SPECIFIC"
        else
        "CONTEXTUAL_ILLUSTRATIVE_LICENSED"
    )


    return {
        "decision":
            "SELECT",

        "tier":
            tier,

        "selected":
            selected,

        "evaluated":
            evaluated,
    }


def build_candidate_pool(
    story_name,
    scene,
    entities
):
    pool = [
        bad_query_contaminated_candidate(
            story_name,
            scene,
            entities
        )
    ]


    if (
        not scene[
            "factual"
        ]
        and
        not scene[
            "identity_required"
        ]
        and
        scene[
            "hook_priority"
        ] != 100
    ):
        pool.append(
            bad_unlabeled_candidate(
                story_name,
                scene
            )
        )


    pool.append(
        good_candidate(
            story_name,
            scene,
            entities
        )
    )


    return pool


def make_mock_asset(
    story_name,
    scene,
    candidate
):
    folder = (
        MOCK_ROOT
        / story_name.lower()
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    path = (
        folder
        / (
            "scene_"
            + f"{scene:02d}"
            + ".mock"
        )
    )


    path.write_text(
        (
            "SHORTAUTOPRO VI1100 MOCK\n"
            f"story={story_name}\n"
            f"scene={scene}\n"
            f"candidate={candidate['candidate_id']}\n"
        ),
        encoding="utf-8"
    )


    return (
        path,
        sha256(
            path
        )
    )


def build_manifest(
    story_name,
    selections
):
    scenes = {}


    for item in selections:
        scene = item[
            "scene"
        ]

        selected = item[
            "selection"
        ][
            "selected"
        ]


        if not selected:
            continue


        candidate = selected[
            "candidate"
        ]


        mock_path, digest = (
            make_mock_asset(
                story_name,
                scene,
                candidate
            )
        )


        original = (
            BASE
            / "imagens"
            / "vi1100_dry_run"
            / story_name.lower()
            / (
                "scene_"
                + f"{scene:02d}"
                + ".jpg"
            )
        )


        scenes[
            str(scene)
        ] = {
            "scene":
                scene,

            "original_path":
                str(
                    original
                ),

            "override_active":
                True,

            "canary_path":
                str(
                    mock_path
                ),

            "expected_sha256":
                digest,

            "title":
                candidate[
                    "title"
                ],

            "source_title":
                candidate[
                    "title"
                ],

            "source_group":
                candidate[
                    "source_group"
                ],

            "family":
                candidate[
                    "family"
                ],

            "license":
                candidate[
                    "license"
                ],

            "illustration_label":
                candidate[
                    "illustration_label"
                ],

            "epistemic_usage":
                candidate[
                    "intended_usage"
                ],

            "mode":
                "VI1100_DRY_RUN_ONLY",
        }


    manifest = {
        "version":
            VERSION,

        "short_id":
            (
                "VI1100_"
                + story_name
            ),

        "dry_run_only":
            True,

        "active_override_scenes":
            sorted(
                int(key)
                for key in scenes
            ),

        "scenes":
            scenes,
    }


    path = (
        MANIFEST_ROOT
        / (
            story_name.lower()
            + "_manifest.json"
        )
    )


    write_json(
        path,
        manifest
    )


    return (
        path,
        manifest
    )


def manifest_contract(
    manifest
):
    errors = []


    required = {
        "original_path",
        "override_active",
        "canary_path",
        "expected_sha256",
        "source_group",
        "family",
        "license",
    }


    for key, entry in (
        manifest.get(
            "scenes",
            {}
        ).items()
    ):
        missing = sorted(
            field
            for field in required
            if field not in entry
        )


        if missing:
            errors.append(
                f"scene_{key}_missing:"
                + ",".join(
                    missing
                )
            )


        candidate = Path(
            entry.get(
                "canary_path"
            )
            or ""
        )


        if not candidate.exists():
            errors.append(
                f"scene_{key}_asset_missing"
            )

            continue


        actual = sha256(
            candidate
        )


        if (
            actual
            != entry.get(
                "expected_sha256"
            )
        ):
            errors.append(
                f"scene_{key}_hash_mismatch"
            )


    return result(
        not errors,
        errors=errors
    )


def reload_runtime_modules():
    import vi1000_runtime
    import vi1000_command_hook

    vi1000_runtime = (
        importlib.reload(
            vi1000_runtime
        )
    )

    vi1000_command_hook = (
        importlib.reload(
            vi1000_command_hook
        )
    )

    return (
        vi1000_runtime,
        vi1000_command_hook
    )


def runtime_contract(
    manifest_path,
    manifest
):
    os.environ[
        "VI1000_MODE"
    ] = "ON"

    os.environ[
        "VI1000_MANIFEST"
    ] = str(
        manifest_path
    )


    runtime, hook = (
        reload_runtime_modules()
    )


    validation = (
        runtime.validate_manifest()
    )


    synthetic = (
        hook.synthetic_test()
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

        for item in synthetic
    )


    active_expected = sorted(
        manifest[
            "active_override_scenes"
        ]
    )


    active_actual = (
        validation[
            "active_scenes"
        ]
    )


    # OFF must always return original media.
    first_scene = active_expected[
        0
    ]

    first_entry = (
        manifest[
            "scenes"
        ][
            str(
                first_scene
            )
        ]
    )

    original = (
        first_entry[
            "original_path"
        ]
    )


    os.environ[
        "VI1000_MODE"
    ] = "OFF"


    off_resolution = (
        runtime.resolve_scene_media(
            first_scene,
            original
        )
    )


    off_fallback_ok = (
        off_resolution
        == original
    )


    # Restore.
    os.environ[
        "VI1000_MODE"
    ] = "ON"


    return {
        "passed":
            (
                validation[
                    "valid"
                ]
                and
                active_actual
                == active_expected
                and
                len(
                    synthetic
                )
                ==
                len(
                    active_expected
                )
                and
                rewrite_ok
                and
                off_fallback_ok
            ),

        "manifest_valid":
            validation[
                "valid"
            ],

        "expected_active":
            active_expected,

        "actual_active":
            active_actual,

        "synthetic_rewrites":
            len(
                synthetic
            ),

        "every_active_scene_rewrites":
            rewrite_ok,

        "mode_off_returns_original":
            off_fallback_ok,
    }


def corrupted_hash_fallback_contract(
    manifest_path,
    manifest
):
    broken = copy.deepcopy(
        manifest
    )


    scene = (
        broken[
            "active_override_scenes"
        ][0]
    )


    entry = (
        broken[
            "scenes"
        ][
            str(scene)
        ]
    )


    original = entry[
        "original_path"
    ]


    entry[
        "expected_sha256"
    ] = (
        "0"
        * 64
    )


    broken_path = (
        manifest_path.parent
        / (
            manifest_path.stem
            + "_broken_hash.json"
        )
    )


    write_json(
        broken_path,
        broken
    )


    os.environ[
        "VI1000_MODE"
    ] = "ON"

    os.environ[
        "VI1000_MANIFEST"
    ] = str(
        broken_path
    )


    runtime, hook = (
        reload_runtime_modules()
    )


    validation = (
        runtime.validate_manifest()
    )


    resolved = (
        runtime.resolve_scene_media(
            scene,
            original
        )
    )


    command = [
        "ffmpeg",
        "-i",
        original,
        "-f",
        "null",
        "-"
    ]


    rewritten, matches = (
        hook.rewrite_command(
            command
        )
    )


    invalid_detected = (
        scene
        in validation[
            "invalid"
        ]
    )


    fallback_ok = (
        resolved
        == original
    )


    rewrite_skipped = (
        not any(
            item[
                "scene"
            ]
            == scene
            for item in matches
        )
    )


    return {
        "passed":
            (
                invalid_detected
                and
                fallback_ok
                and
                rewrite_skipped
            ),

        "invalid_hash_detected":
            invalid_detected,

        "legacy_original_returned":
            fallback_ok,

        "invalid_override_not_rewritten":
            rewrite_skipped,
    }


def renderer_static_contract():
    errors = []

    if not VIDEO_PY.exists():
        errors.append(
            "video_py_missing"
        )

    if not EXECUTOR_PY.exists():
        errors.append(
            "executor_missing"
        )


    if errors:
        return result(
            False,
            errors=errors
        )


    video_text = (
        VIDEO_PY.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    )


    executor_text = (
        EXECUTOR_PY.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    )


    checks = {
        "vi700_canary_gate":
            (
                "VI700_CANARY_MODE"
                in video_text
            ),

        "scene_executor_import":
            (
                "vi6_95_scene_executor"
                in video_text
            ),

        "scene_executor_execute":
            (
                "execute"
                in video_text
            ),

        "executor_has_execute_definition":
            (
                "def execute("
                in executor_text
            ),

        "legacy_subprocess_path_present":
            (
                "subprocess.run"
                in video_text
            ),

        "ffmpeg_command_pipeline_present":
            (
                "ffmpeg"
                in video_text.lower()
            ),
    }


    return {
        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "video_sha256":
            sha256(
                VIDEO_PY
            ),

        "executor_sha256":
            sha256(
                EXECUTOR_PY
            ),

        "errors":
            [],
    }


def trusted_baseline_observation():
    expected_video = (
        "756c0db576f664d474cb92676b4ad817"
        "37158f8a275bfad6348aa0a542d87b06"
    )

    expected_gerar = (
        "25af0e189440d3646de8da8772535e00"
        "ac1e8446097f5db56ed93144ab45eb7a"
    )


    current_video = (
        sha256(
            BASE
            / "video.py"
        )
        if (
            BASE
            / "video.py"
        ).exists()
        else None
    )


    current_gerar = (
        sha256(
            BASE
            / "gerar_short.sh"
        )
        if (
            BASE
            / "gerar_short.sh"
        ).exists()
        else None
    )


    return {
        "video_matches_known_stable":
            (
                current_video
                == expected_video
            ),

        "gerar_matches_known_stable":
            (
                current_gerar
                == expected_gerar
            ),

        "video_current":
            current_video,

        "gerar_current":
            current_gerar,

        # Observation only.
        # The relative integrity audit remains authoritative.
        "blocking":
            False,
    }


def run_story(
    story_name,
    segments
):
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


    selections = []

    trap_results = []

    provider_checks = []


    for scene in scenes:
        pool = build_candidate_pool(
            story_name,
            scene,
            entities
        )


        selection = select_candidate(
            scene,
            pool,
            entities
        )


        selections.append({
            "scene":
                scene[
                    "scene"
                ],

            "selection":
                selection,
        })


        evaluated = (
            selection[
                "evaluated"
            ]
        )


        query_traps = [
            item
            for item in evaluated
            if "_QUERY_TRAP_"
            in item[
                "candidate"
            ][
                "candidate_id"
            ]
        ]


        trap_results.append({
            "scene":
                scene[
                    "scene"
                ],

            "query_trap_rejected":
                all(
                    not item[
                        "evaluation"
                    ][
                        "passed"
                    ]
                    for item in query_traps
                ),
        })


    for query in queries:
        providers = (
            query.get(
                "providers"
            )
            or []
        )


        provider_checks.append({
            "scene":
                query[
                    "scene"
                ],

            "nonempty":
                bool(
                    providers
                ),

            "query_not_evidence":
                (
                    query.get(
                        "query_is_evidence"
                    )
                    is False
                ),

            "case_specific_avoids_current_media":
                (
                    True
                    if not (
                        query.get(
                            "case_specific_required"
                        )
                        or
                        query.get(
                            "identity_required"
                        )
                    )
                    else
                    "CURRENT_MEDIA"
                    not in providers
                ),
        })


    all_selected = all(
        item[
            "selection"
        ][
            "decision"
        ]
        == "SELECT"

        for item in selections
    )


    selected_ids = [
        item[
            "selection"
        ][
            "selected"
        ][
            "candidate"
        ][
            "candidate_id"
        ]

        for item in selections

        if item[
            "selection"
        ][
            "selected"
        ]
    ]


    good_selected = all(
        "_GOOD_"
        in candidate_id

        for candidate_id in (
            selected_ids
        )
    )


    query_traps_rejected = all(
        item[
            "query_trap_rejected"
        ]

        for item in trap_results
    )


    providers_pass = all(
        item[
            "nonempty"
        ]
        and
        item[
            "query_not_evidence"
        ]
        and
        item[
            "case_specific_avoids_current_media"
        ]

        for item in provider_checks
    )


    portfolio = []


    for item in selections:
        selected = (
            item[
                "selection"
            ][
                "selected"
            ]
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

            "sha256":
                digest_text(
                    candidate[
                        "candidate_id"
                    ]
                ),
        })


    diversity = audit_portfolio(
        portfolio
    )


    manifest_path, manifest = (
        build_manifest(
            story_name,
            selections
        )
    )


    manifest_check = (
        manifest_contract(
            manifest
        )
    )


    runtime = runtime_contract(
        manifest_path,
        manifest
    )


    broken_hash = (
        corrupted_hash_fallback_contract(
            manifest_path,
            manifest
        )
    )


    person = (
        entities.get(
            "primary_person"
        )
    )

    location = (
        entities.get(
            "primary_location"
        )
    )


    checks = {
        "scene_count_12":
            len(
                scenes
            )
            == 12,

        "primary_person_resolved":
            person
            is not None,

        "primary_location_resolved":
            location
            is not None,

        "query_plan_12":
            len(
                queries
            )
            == 12,

        "providers_valid":
            providers_pass,

        "all_scenes_selected":
            all_selected,

        "correct_candidates_selected":
            good_selected,

        "query_contamination_rejected":
            query_traps_rejected,

        "diversity_gate":
            diversity[
                "passed"
            ],

        "manifest_contract":
            manifest_check[
                "passed"
            ],

        "runtime_contract":
            runtime[
                "passed"
            ],

        "legacy_fallback_contract":
            broken_hash[
                "passed"
            ],
    }


    return {
        "story":
            story_name,

        "entities":
            entities,

        "scenes":
            scenes,

        "queries":
            queries,

        "selections":
            selections,

        "provider_checks":
            provider_checks,

        "trap_results":
            trap_results,

        "portfolio":
            portfolio,

        "diversity":
            diversity,

        "manifest_path":
            str(
                manifest_path
            ),

        "manifest_contract":
            manifest_check,

        "runtime":
            runtime,

        "broken_hash_fallback":
            broken_hash,

        "checks":
            checks,

        "passed":
            all(
                checks.values()
            ),
    }


def previous_certification_contract():
    checks = {}


    if ADVERSARIAL_REPORT.exists():
        data = load_json(
            ADVERSARIAL_REPORT
        ).get(
            "gate",
            {}
        )

        checks[
            "adversarial_certified"
        ] = (
            data.get(
                "status"
            )
            ==
            "VI1000_1_ADVERSARIAL_CERTIFIED"
        )

    else:
        checks[
            "adversarial_certified"
        ] = False


    if VI1000_REPORT.exists():
        data = load_json(
            VI1000_REPORT
        ).get(
            "gate",
            {}
        )

        checks[
            "previous_full_dry_run_certified"
        ] = (
            data.get(
                "status"
            )
            ==
            "VI1000_1_FULL_DRY_RUN_CERTIFIED"
        )

        benchmark = (
            data.get(
                "benchmark",
                {}
            )
        )

        checks[
            "elisa_lam_regression"
        ] = (
            benchmark.get(
                "checks",
                {}
            ).get(
                "elisa_lam_canonical"
            )
            is True
        )

        checks[
            "hotel_cecil_regression"
        ] = (
            benchmark.get(
                "checks",
                {}
            ).get(
                "hotel_cecil_canonical"
            )
            is True
        )

    else:
        checks[
            "previous_full_dry_run_certified"
        ] = False

        checks[
            "elisa_lam_regression"
        ] = False

        checks[
            "hotel_cecil_regression"
        ] = False


    return {
        "passed":
            all(
                checks.values()
            ),

        "checks":
            checks,
    }


def main():
    WORK.mkdir(
        parents=True,
        exist_ok=True
    )

    MOCK_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    MANIFEST_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


    previous = (
        previous_certification_contract()
    )


    renderer = (
        renderer_static_contract()
    )


    baseline = (
        trusted_baseline_observation()
    )


    stories = {}


    for story_name, segments in (
        STORIES.items()
    ):
        stories[
            story_name
        ] = run_story(
            story_name,
            segments
        )


    story_pass = all(
        item[
            "passed"
        ]

        for item in (
            stories.values()
        )
    )


    checks = {
        "previous_certifications":
            previous[
                "passed"
            ],

        "three_independent_stories":
            len(
                stories
            )
            == 3,

        "all_story_pipelines":
            story_pass,

        "renderer_static_contract":
            renderer[
                "passed"
            ],

        "network_off":
            True,

        "downloads_off":
            True,

        "ffmpeg_off":
            True,

        "video_generation_off":
            True,

        "renderer_activation_off":
            True,
    }


    failed = [
        key
        for key, value
        in checks.items()
        if value is not True
    ]


    report = {
        "version":
            VERSION,

        "status":
            (
                "VI1100_GENERAL_PIPELINE_CERTIFIED"
                if not failed
                else "HOLD"
            ),

        "previous_certification":
            previous,

        "stories":
            stories,

        "renderer_contract":
            renderer,

        "trusted_baseline_observation":
            baseline,

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

        "renderer_activated":
            False,

        "production_media_mutated":
            False,

        "core_source_mutated":
            False,
    }


    write_json(
        OUT,
        {
            "gate":
                report
        }
    )


    print()
    print(
        "=============================================="
    )
    print(
        " VI1100 GENERAL PIPELINE TEST"
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
        "===== PREVIOUS CERTIFICATION ====="
    )

    for key, value in (
        previous[
            "checks"
        ].items()
    ):
        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
        )


    for story_name, story in (
        stories.items()
    ):
        print()
        print(
            "=============================================="
        )

        print(
            " STORY:",
            story_name
        )

        print(
            "=============================================="
        )

        person = (
            story[
                "entities"
            ].get(
                "primary_person"
            )
            or {}
        )

        location = (
            story[
                "entities"
            ].get(
                "primary_location"
            )
            or {}
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


        for key, value in (
            story[
                "checks"
            ].items()
        ):
            print(
                key,
                "=",
                "PASS"
                if value
                else "FAIL"
            )


        print(
            "DIVERSITY:",
            story[
                "diversity"
            ][
                "unique_source_count"
            ],
            "unique | ratio=",
            story[
                "diversity"
            ][
                "unique_source_ratio"
            ],
            "| max_run=",
            story[
                "diversity"
            ][
                "maximum_consecutive_same_source"
            ]
        )


        print(
            "RUNTIME:",
            story[
                "runtime"
            ]
        )


        print(
            "BROKEN HASH FALLBACK:",
            story[
                "broken_hash_fallback"
            ]
        )


    print()
    print(
        "===== RENDER CONTRACT ====="
    )

    for key, value in (
        renderer.get(
            "checks",
            {}
        ).items()
    ):
        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
        )


    print()
    print(
        "===== GLOBAL CHECKS ====="
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


    if failed:
        raise SystemExit(
            1
        )


    print()
    print(
        "VI1100 RESULT: "
        "GENERAL_PIPELINE_CERTIFIED"
    )


if __name__ == "__main__":
    main()
