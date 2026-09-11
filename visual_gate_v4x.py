#!/usr/bin/env python3

import os

from vg4x_common import (
    dedupe_candidates,
    flatten_candidates,
    media_type,
    norm,
    provider,
)

from vg4x_score import (
    choose_best,
    note_selection,
    rank_candidates,
    reset_state,
    runtime_state,
    score_candidate,
)


VERSION = "4.2"


def build_scene_from_locals(
    local_vars,
):

    scene = {}

    aliases = {

        "texto":
            (
                "texto",
                "segmento",
                "narracao",
                "texto_cena",
            ),

        "visual_query":
            (
                "visual_query",
                "busca",
                "query",
            ),

        "must_have":
            (
                "must_have",
                "must",
            ),

        "avoid":
            (
                "avoid",
                "avoid_terms",
            ),

        "location":
            (
                "location",
                "local",
                "geography",
            ),

        "visual_mode":
            (
                "visual_mode",
                "modo_visual",
            ),
    }

    for target, names in aliases.items():

        for name in names:

            if name in local_vars:

                value = local_vars[
                    name
                ]

                if value is not None:
                    scene[
                        target
                    ] = value

                    break

    # Se existir uma scene/cena estruturada,
    # preserva seus campos.
    structured = (
        local_vars.get("scene")
        or local_vars.get("cena")
    )

    if isinstance(
        structured,
        dict,
    ):

        merged = dict(
            structured
        )

        for key, value in scene.items():

            if key not in merged:
                merged[key] = value

        scene = merged

    return scene


def choose_from_locals(
    local_vars,
    pool,
    reference,
):

    if (
        os.getenv(
            "SAP_VG4X",
            "1",
        )
        ==
        "0"
    ):
        return (
            reference,
            pool,
            {
                "override": False,
                "reason": "DISABLED",
            },
        )

    scene = build_scene_from_locals(
        local_vars
    )

    candidates = dedupe_candidates(
        flatten_candidates(
            pool
        )
    )

    if (
        reference is not None
        and all(
            candidate is not reference
            for candidate in candidates
        )
    ):
        candidates.insert(
            0,
            reference,
        )

    chosen, ranked, meta = choose_best(
        candidates,
        scene,
        reference=reference,
        state=runtime_state(),
    )

    ranked_candidates = [
        row["candidate"]
        for row in ranked
    ]

    if (
        chosen is not None
        and all(
            candidate is not chosen
            for candidate in ranked_candidates
        )
    ):
        ranked_candidates.insert(
            0,
            chosen,
        )

    before = (
        rank_candidates(
            [reference],
            scene,
            runtime_state(),
        )[0]
        if reference is not None
        else None
    )

    after = (
        rank_candidates(
            [chosen],
            scene,
            runtime_state(),
        )[0]
        if chosen is not None
        else None
    )

    print()
    print("VG4X_FINAL_GATE:")

    if before:

        print(
            "  BEFORE="
            f"{before['provider']}/"
            f"{before['media_type']} "
            f"must={before['must_hits']}/"
            f"{before['must_total']} "
            f"tier={before['must_tier']} "
            f"effective="
            f"{before['effective']:.1f} "
            f"hard="
            f"{before['hard_mismatch']}"
        )

        if before[
            "hard_reasons"
        ]:

            print(
                "  BEFORE_REASONS="
                +
                ",".join(
                    before[
                        "hard_reasons"
                    ]
                )
            )

    if after:

        print(
            "  AFTER="
            f"{after['provider']}/"
            f"{after['media_type']} "
            f"must={after['must_hits']}/"
            f"{after['must_total']} "
            f"tier={after['must_tier']} "
            f"effective="
            f"{after['effective']:.1f} "
            f"hard="
            f"{after['hard_mismatch']}"
        )

    print(
        "  OVERRIDE="
        +
        (
            "YES"
            if meta.get("override")
            else "NO"
        )
    )

    print(
        "  REASON="
        +
        str(
            meta.get("reason")
        )
    )

    return (
        chosen,
        ranked_candidates,
        meta,
    )


def self_test():

    reset_state()

    scene = {
        "texto":
            "Investigação em apartamento "
            "na cidade de São Paulo",

        "must_have":
            [
                "apartamento",
                "São Paulo",
            ],
    }

    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building New York",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }

    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Apartment building Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }

    a = score_candidate(
        wrong,
        scene,
        runtime_state(),
    )

    b = score_candidate(
        correct,
        scene,
        runtime_state(),
    )

    assert a[
        "hard_mismatch"
    ]

    assert not b[
        "hard_mismatch"
    ]

    chosen, _, meta = choose_best(
        [
            wrong,
            correct,
        ],
        scene,
        reference=wrong,
        state=runtime_state(),
    )

    assert chosen is correct
    assert meta["override"]

    print(
        "VG4X_SELF_TEST=PASS"
    )

    print(
        "GEO_CONTRADICTION_TEST=PASS"
    )

    print(
        "FINAL_GATE_TEST=PASS"
    )


if __name__ == "__main__":
    self_test()
