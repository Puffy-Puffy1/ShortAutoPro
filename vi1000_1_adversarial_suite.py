#!/usr/bin/env python3

import json

from pathlib import Path

from vi1000_1_semantic_core import (
    extract_entities,
    classify_scenes,
)

from vi1000_1_query_gate import (
    evaluate_candidate,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

OUT = (
    BASE
    / "logs/producao"
    / "vi1000_1_adversarial_suite_latest.json"
)


SEGMENTS = [
    (
        "No Hotel Aurora, Marina Duarte "
        "foi vista pela última vez perto do elevador."
    ),

    (
        "A estudante Marina Duarte chegou ao "
        "Hotel Aurora para passar três noites."
    ),

    (
        "A polícia divulgou a filmagem da câmera "
        "de segurança do Hotel Aurora."
    ),

    (
        "O relatório oficial registrou detalhes "
        "sobre o desaparecimento de Marina Duarte."
    )
]


entities = extract_entities(
    SEGMENTS
)

scenes = classify_scenes(
    SEGMENTS,
    entities
)


scene_identity = scenes[1]

scene_evidence = scenes[2]

scene_document = scenes[3]


def candidate(
    **kwargs
):
    base = {
        "title":
            "Candidate",

        "evidence_text":
            "",

        "entity_mentions":
            [],

        "role_tags":
            [],

        "license":
            "CC BY 4.0",

        "family":
            "IMAGE",

        "width":
            1200,

        "height":
            1800,

        "intended_usage":
            "CASE_SPECIFIC",

        "illustration_label":
            False,
    }

    base.update(
        kwargs
    )

    return base


tests = []


def add(
    name,
    scene,
    cand,
    expected
):
    result = evaluate_candidate(
        scene,
        cand,
        entities
    )

    tests.append({
        "name":
            name,

        "expected":
            expected,

        "actual":
            result[
                "passed"
            ],

        "passed":
            result[
                "passed"
            ]
            == expected,

        "result":
            result,
    })


add(
    "QUERY_CONTAMINATION_DOES_NOT_PROVE_CASE",
    scene_evidence,
    candidate(
        title="Random city skyline",
        evidence_text="city skyline at night",
        role_tags=[
            "EVIDENCE"
        ]
    ),
    False
)


add(
    "GENERIC_LOCATION_DOES_NOT_PROVE_NAMED_HOTEL",
    scenes[0],
    candidate(
        title="Generic hotel elevator",
        evidence_text="hotel elevator interior",
        role_tags=[
            "LOCATION"
        ]
    ),
    False
)


add(
    "FILE_NAMESPACE_DOES_NOT_PROVE_DOCUMENT",
    scene_document,
    candidate(
        title="File:RandomPhoto.jpg",
        evidence_text="random photograph",
        role_tags=[
            "LOCATION"
        ]
    ),
    False
)


add(
    "GENERIC_HUMAN_DOES_NOT_PROVE_SPECIFIC_PERSON",
    scene_identity,
    candidate(
        title="Anonymous woman",
        evidence_text="anonymous woman walking",
        role_tags=[
            "HUMAN"
        ]
    ),
    False
)


add(
    "SPECIFIC_PERSON_EVIDENCE_PASSES",
    scene_identity,
    candidate(
        title="Marina Duarte archival photograph",
        evidence_text=(
            "verified archival photograph "
            "of Marina Duarte"
        ),
        entity_mentions=[
            "Marina Duarte"
        ],
        role_tags=[
            "HUMAN"
        ]
    ),
    True
)


illustrative_scene = dict(
    scenes[0]
)

illustrative_scene.update({
    "scene":
        99,

    "factual":
        False,

    "hook_priority":
        0,

    "hook_case_specific_preferred":
        False,

    "location_scope":
        "GENERIC_LOCATION",

    "epistemic_mode":
        "ILLUSTRATIVE_ALLOWED",

    "identity_required":
        False,
})


add(
    "LABELED_ILLUSTRATIVE_LOCATION_PASSES",
    illustrative_scene,
    candidate(
        title="Hotel hallway",
        evidence_text="generic hotel hallway corridor",
        role_tags=[
            "LOCATION"
        ],
        intended_usage="ILLUSTRATIVE",
        illustration_label=True
    ),
    True
)


add(
    "UNLABELED_ILLUSTRATIVE_LOCATION_FAILS",
    illustrative_scene,
    candidate(
        title="Hotel hallway",
        evidence_text="generic hotel hallway corridor",
        role_tags=[
            "LOCATION"
        ],
        intended_usage="ILLUSTRATIVE",
        illustration_label=False
    ),
    False
)


add(
    "VALID_CASE_EVIDENCE_PASSES",
    scene_evidence,
    candidate(
        title="Hotel Aurora surveillance footage",
        evidence_text=(
            "Hotel Aurora surveillance footage "
            "connected to Marina Duarte investigation"
        ),
        entity_mentions=[
            "Hotel Aurora",
            "Marina Duarte"
        ],
        role_tags=[
            "EVIDENCE"
        ],
        family="VIDEO"
    ),
    True
)


add(
    "VALID_CASE_DOCUMENT_PASSES",
    scene_document,
    candidate(
        title="Marina Duarte official report",
        evidence_text=(
            "official report document "
            "concerning Marina Duarte"
        ),
        entity_mentions=[
            "Marina Duarte"
        ],
        role_tags=[
            "DOCUMENT"
        ]
    ),
    True
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


report = {
    "version":
        "1000.1",

    "status":
        (
            "VI1000_1_ADVERSARIAL_CERTIFIED"
            if not failed
            else "HOLD"
        ),

    "tests":
        tests,

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
    " VI1000.1 ADVERSARIAL TRUTH SUITE"
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

for item in tests:
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
    failed
)
