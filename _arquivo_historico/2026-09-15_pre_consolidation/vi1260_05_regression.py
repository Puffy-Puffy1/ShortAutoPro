#!/usr/bin/env python3

from vi1000_1_semantic_core import (
    extract_entities,
)

from vi1200_04_real_candidate_adapter import (
    adapt,
)

from vi1250_04_candidate_engine import (
    evaluate_candidate_record,
)

from vi1260_03_semantic_candidate_gate import (
    evaluate_vi1260,
)


SEGMENTS = [
    "Elisa Lam desapareceu no Hotel Cecil.",
    "Elisa Lam foi vista antes do desaparecimento.",
]


ENTITIES = extract_entities(
    SEGMENTS
)


def raw(
    title,
    description,
):
    return {
        "provider":
            "WIKIMEDIA_COMMONS",

        "pageid":
            abs(
                hash(title)
            )
            % 10000000,

        "title":
            title,

        "description":
            description,

        "object_name":
            title,

        "categories":
            "",

        "artist":
            "Test Author",

        "credit":
            "Synthetic regression metadata",

        "license":
            "CC BY 4.0",

        "license_url":
            (
                "https://creativecommons.org/"
                "licenses/by/4.0/"
            ),

        "width":
            2400,

        "height":
            3200,

        "mime":
            "image/jpeg",

        "remote_url":
            "https://commons.wikimedia.org/test.jpg",

        "metadata_only":
            True,
    }


def scene(
    number,
    segment,
    role,
    *,
    identity_scope="NONE",
    location_scope="NONE",
):
    return {
        "scene":
            number,

        "segment":
            segment,

        "role":
            role,

        "factual":
            False,

        "identity_required":
            identity_scope.startswith(
                "SPECIFIC_PERSON"
            ),

        "identity_scope":
            identity_scope,

        "location_scope":
            location_scope,

        "hook_priority":
            0,

        "cta":
            False,

        "epistemic_mode":
            "ILLUSTRATIVE_ALLOWED",
    }


def evaluate(
    scene_data,
    raw_data,
    query="",
):
    candidate = adapt(
        raw_data,
        scene_data,
        ENTITIES,
        search_query=query
    )

    candidate = (
        evaluate_candidate_record(
            scene_data,
            candidate,
            ENTITIES
        )[
            "candidate"
        ]
    )

    return evaluate_vi1260(
        scene_data,
        candidate,
        ENTITIES
    )


def main():
    tests = []


    s2 = scene(
        2,
        (
            "Em fevereiro de 2013, "
            "Elisa Lam desapareceu no Hotel Cecil."
        ),
        "HUMAN",
        identity_scope=(
            "SPECIFIC_PERSON_INFERRED"
        ),
        location_scope=(
            "SPECIFIC_LOCATION_EXPLICIT"
        ),
    )


    tests.append((
        "SCENE2_CASE_LOCATION_CONTEXT",
        evaluate(
            s2,
            raw(
                "File:Hotel Cecil exterior.jpg",
                (
                    "Hotel Cecil in Los Angeles, "
                    "California."
                )
            )
        )[
            "passed"
        ],
        True,
    ))


    tests.append((
        "SCENE2_GENERIC_WOMAN_REJECTED",
        evaluate(
            s2,
            raw(
                "File:Unknown woman.jpg",
                "Portrait photograph of an unknown woman."
            )
        )[
            "passed"
        ],
        False,
    ))


    tests.append((
        "QUERY_CONTAMINATION_NOT_LOCATION_PROOF",
        evaluate(
            s2,
            raw(
                "File:Arizona hotel.jpg",
                "Hotel building in Arizona."
            ),
            query="Elisa Lam Hotel Cecil"
        )[
            "passed"
        ],
        False,
    ))


    s6 = scene(
        6,
        "e parece se esconder,",
        "CONTEXT",
    )


    tests.append((
        "ACTION_CONTEXT_HALLWAY",
        evaluate(
            s6,
            raw(
                "File:Hotel hallway door.jpg",
                "Empty hotel hallway with doorway."
            )
        )[
            "passed"
        ],
        True,
    ))


    s9 = scene(
        9,
        (
            "ao transtorno bipolar "
            "do qual Lam sofria."
        ),
        "CONTEXT",
    )


    tests.append((
        "BIPOLAR_DIAGRAM_ALLOWED",
        evaluate(
            s9,
            raw(
                "File:Bipolar disorder diagram.jpg",
                (
                    "Educational diagram about "
                    "bipolar disorder and mental health."
                )
            )
        )[
            "passed"
        ],
        True,
    ))


    tests.append((
        "MEDICINE_BOX_NOT_BIPOLAR_PROOF",
        evaluate(
            s9,
            raw(
                "File:Medicine box.jpg",
                "Generic medicine packaging."
            )
        )[
            "passed"
        ],
        False,
    ))


    s10 = scene(
        10,
        (
            "Funcionários da manutenção "
            "descobriram o corpo."
        ),
        "HUMAN",
        identity_scope=(
            "GENERIC_HUMAN_OR_GROUP"
        ),
    )


    tests.append((
        "MAINTENANCE_WORKER_ALLOWED",
        evaluate(
            s10,
            raw(
                "File:Maintenance worker.jpg",
                (
                    "Building maintenance worker "
                    "performing maintenance."
                )
            )
        )[
            "passed"
        ],
        True,
    ))


    tests.append((
        "EMPTY_HOTEL_CORRIDOR_REJECTED_FOR_WORKER",
        evaluate(
            s10,
            raw(
                "File:Hotel corridor.jpg",
                "Empty hotel hallway and corridor."
            )
        )[
            "passed"
        ],
        False,
    ))


    s11 = scene(
        11,
        (
            "dentro de um tanque de água "
            "no topo do hotel."
        ),
        "LOCATION",
        location_scope=(
            "SPECIFIC_LOCATION_INFERRED_STORY_CONTEXT"
        ),
    )


    tests.append((
        "ROOFTOP_WATER_TANK_ILLUSTRATION",
        evaluate(
            s11,
            raw(
                "File:Rooftop water tanks.jpg",
                (
                    "Water tanks and water towers "
                    "on an urban rooftop."
                )
            )
        )[
            "passed"
        ],
        True,
    ))


    tests.append((
        "GENERIC_ROOFTOP_WITHOUT_TANK_REJECTED",
        evaluate(
            s11,
            raw(
                "File:City rooftop.jpg",
                "Urban building rooftop skyline."
            )
        )[
            "passed"
        ],
        False,
    ))


    failed = []


    print()
    print(
        "=============================================="
    )
    print(
        " VI1260 SEMANTIC REGRESSION"
    )
    print(
        "=============================================="
    )


    for name, actual, expected in tests:

        passed = (
            actual == expected
        )

        print(
            name,
            "=",
            "PASS"
            if passed
            else "FAIL",
            "| expected=",
            expected,
            "| actual=",
            actual
        )

        if not passed:
            failed.append(name)


    print(
        "FAILED:",
        failed
    )


    if failed:
        raise SystemExit(1)


    print(
        "VI1260_SEMANTIC_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
