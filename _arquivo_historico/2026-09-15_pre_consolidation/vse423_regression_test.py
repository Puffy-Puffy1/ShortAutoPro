#!/usr/bin/env python3

import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="vse423_regression",
)

score = ns[
    "score_candidate"
]


STATE = {
    "providers": [
        "pixabay",
        "pixabay",
    ],
    "groups": [],
    "types": [],
    "keys": [],
}


CASES = [


    # ========================================================
    # 1. FALSE MEDICINE ASSOCIATION
    # ========================================================

    {
        "name":
            "FORENSIC_VS_PILLS",

        "scene":
            (
                "O laudo pericial revelou "
                "novos indícios encontrados "
                "durante a investigação."
            ),

        "candidate": {
            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                (
                    "Pills medication tablets "
                    "on pharmacy table"
                ),

            "must":
                "1/2",

            "score":
                210,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            True,
    },


    # ========================================================
    # 2. GENERIC WOMAN
    # ========================================================

    {
        "name":
            "INVESTIGATION_VS_RELAXING_WOMAN",

        "scene":
            (
                "A polícia iniciou a investigação "
                "dentro do apartamento."
            ),

        "candidate": {
            "provider":
                "Pexels",

            "tipo":
                "video",

            "title":
                (
                    "Happy woman relaxing in "
                    "bedroom on bed lifestyle"
                ),

            "must":
                "1/2",

            "score":
                220,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            True,
    },


    # ========================================================
    # 3. MEDICINE IS ACTUALLY IN SCENE
    # ========================================================

    {
        "name":
            "MEDICINE_VS_PILLS",

        "scene":
            (
                "A investigação encontrou "
                "medicamentos e comprimidos "
                "no local."
            ),

        "candidate": {
            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                (
                    "Medicine pills tablets "
                    "prescription medication"
                ),

            "must":
                "2/2",

            "score":
                180,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            False,
    },


    # ========================================================
    # 4. BEDROOM IS ACTUALLY RELEVANT
    # ========================================================

    {
        "name":
            "BEDROOM_VS_BEDROOM",

        "scene":
            (
                "A perícia examinou o quarto "
                "do apartamento."
            ),

        "candidate": {
            "provider":
                "Pexels",

            "tipo":
                "foto",

            "title":
                (
                    "Apartment bedroom interior "
                    "crime investigation room"
                ),

            "must":
                "2/2",

            "score":
                170,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            False,
    },


    # ========================================================
    # 5. GENERIC OFFICE
    # ========================================================

    {
        "name":
            "CRIME_SCENE_VS_GENERIC_OFFICE",

        "scene":
            (
                "Investigadores reconstruíram "
                "a cena do crime."
            ),

        "candidate": {
            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                (
                    "Modern office desk workspace "
                    "business lifestyle"
                ),

            "must":
                "1/2",

            "score":
                205,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            True,
    },


    # ========================================================
    # 6. SAO PAULO VS NEW YORK
    # ========================================================

    {
        "name":
            "SAO_PAULO_VS_NEW_YORK",

        "scene":
            (
                "Investigação em apartamento "
                "na cidade de São Paulo."
            ),

        "candidate": {
            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                (
                    "Empire State Building "
                    "Manhattan New York"
                ),

            "must":
                "2/2",

            "score":
                250,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            True,
    },


    # ========================================================
    # 7. CORRECT SAO PAULO
    # ========================================================

    {
        "name":
            "SAO_PAULO_CORRECT",

        "scene":
            (
                "Investigação em apartamento "
                "na cidade de São Paulo."
            ),

        "candidate": {
            "provider":
                "Wikimedia",

            "tipo":
                "foto",

            "title":
                (
                    "Residential apartment "
                    "building Sao Paulo Brazil"
                ),

            "must":
                "1/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            False,
    },


    # ========================================================
    # 8. COURT VS LIFESTYLE BEACH
    # ========================================================

    {
        "name":
            "COURT_VS_BEACH_LIFESTYLE",

        "scene":
            (
                "O tribunal condenou os réus "
                "após o julgamento."
            ),

        "candidate": {
            "provider":
                "Pexels",

            "tipo":
                "video",

            "title":
                (
                    "Happy couple relaxing "
                    "on beach vacation lifestyle"
                ),

            "must":
                "1/2",

            "score":
                240,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            True,
    },


    # ========================================================
    # 9. COURT CORRECT
    # ========================================================

    {
        "name":
            "COURT_CORRECT",

        "scene":
            (
                "O tribunal condenou os réus "
                "após o julgamento."
            ),

        "candidate": {
            "provider":
                "Pixabay",

            "tipo":
                "video",

            "title":
                (
                    "Courtroom judge legal "
                    "trial courthouse"
                ),

            "must":
                "2/2",

            "score":
                180,

            "width":
                1920,

            "height":
                1080,
        },

        "expected":
            False,
    },

]


failed = []


for case in CASES:

    result = score(
        case[
            "candidate"
        ],
        case[
            "scene"
        ],
        STATE,
    )


    actual = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


    print()
    print(
        "=" * 72
    )

    print(
        "CASE=",
        case[
            "name"
        ],
    )

    print(
        "=" * 72
    )


    print(
        "EXPECTED=",
        case[
            "expected"
        ],
    )

    print(
        "ACTUAL=",
        actual,
    )

    print(
        "HARD_REASON=",
        result.get(
            "hard_reason",
            "",
        ),
    )

    print(
        "EFFECTIVE=",
        result.get(
            "effective"
        ),
    )

    print(
        "SEMANTIC_HITS=",
        result.get(
            "semantic_hits"
        ),
    )

    print(
        "VSE423_SUPPORT=",
        result.get(
            "vse423_semantic_support"
        ),
    )

    print(
        "VSE423_SERIOUS=",
        result.get(
            "vse423_serious_scene"
        ),
    )

    print(
        "VSE423_GENERIC=",
        result.get(
            "vse423_generic_candidate"
        ),
    )

    print(
        "VSE423_MEDICINE_SUPPORTED=",
        result.get(
            "vse423_medicine_supported"
        ),
    )

    print(
        "VSE423_OVERLAP=",
        result.get(
            "vse423_concept_overlap"
        ),
    )


    ok = (
        actual
        ==
        case[
            "expected"
        ]
    )


    print(
        "CASE_RESULT="
        +
        (
            "PASS"
            if ok
            else
            "FAIL"
        )
    )


    if not ok:

        failed.append(
            case[
                "name"
            ]
        )


print()
print(
    "=" * 72
)

print(
    " VSE423 REGRESSION SUMMARY"
)

print(
    "=" * 72
)


print(
    "TOTAL_CASES=",
    len(
        CASES
    ),
)

print(
    "PASSED=",
    len(
        CASES
    )
    -
    len(
        failed
    ),
)

print(
    "FAILED=",
    len(
        failed
    ),
)


if failed:

    print(
        "FAILED_CASES="
        +
        ",".join(
            failed
        )
    )

    print(
        "VSE423_REGRESSION=FAIL"
    )

    raise SystemExit(1)


print(
    "FAILED_CASES=NONE"
)

print(
    "VSE423_REGRESSION=PASS"
)
