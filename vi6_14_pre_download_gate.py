#!/usr/bin/env python3

from vi6_10_coverage_predictor import (
    contract
)


VERSION = "6.14"


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def final_gate(
    candidate,
    scene,
    meta=None
):

    meta = (
        meta
        or {}
    )


    c = contract(
        scene
    )


    if candidate is None:

        return {

            "action":
                "FALLBACK",

            "reason":
                "vi614_no_candidate",

            "contract":
                c,
        }


    classe = _u(
        meta.get(
            "class"
        )
        or candidate.get(
            "_vi611_class"
        )
        or candidate.get(
            "_vi6_class"
        )
        or candidate.get(
            "class"
        )
    )


    risk = _u(
        candidate.get(
            "_vi6_risk"
        )
        or candidate.get(
            "risk"
        )
    )


    truth_ok = bool(
        meta.get(
            "truth_ok",
            candidate.get(
                "_vi611_truth",
                candidate.get(
                    "_vi6_truth_ok",
                    candidate.get(
                        "truth_ok",
                        False
                    )
                )
            )
        )
    )


    score = _f(
        meta.get(
            "score",
            candidate.get(
                "_vi611_score",
                candidate.get(
                    "_vi6_score",
                    candidate.get(
                        "score",
                        0
                    )
                )
            )
        )
    )


    semantic = _f(
        meta.get(
            "semantic",
            candidate.get(
                "semantic",
                0
            )
        )
    )


    anchor = _f(
        meta.get(
            "anchor",
            meta.get(
                "anchor_ratio",
                candidate.get(
                    "_vi66_anchor",
                    0
                )
            )
        )
    )


    role = _u(
        meta.get(
            "role"
        )
        or c[
            "role"
        ]
    )


    # =================================
    # HARD SAFETY
    # =================================

    if risk == "HIGH":

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_high_risk",
            "contract": c,
        }


    if "MISLEADING" in classe:

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_misleading",
            "contract": c,
        }


    if classe not in {
        "REAL_DOCUMENTARY",
        "SAFE_CONTEXT"
    }:

        return {
            "action": "FALLBACK",
            "reason":
                "vi614_invalid_class",
            "contract": c,
        }


    # =================================
    # CTA
    # =================================

    if role == "CTA":

        return {
            "action": "ACCEPT",
            "reason":
                "vi614_cta_accept",
            "contract": c,
        }


    # =================================
    # DOCUMENTARY
    # =================================

    if classe == "REAL_DOCUMENTARY":

        if not truth_ok:

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi614_documentary_truth_failed",

                "contract":
                    c,
            }


        evidence = _u(
            candidate.get(
                "evidence_class"
            )
        )


        strong_evidence = (
            evidence
            == "CASE_DIRECT"
        )


        # Se o retrieval tinha identidade
        # forte mas o documental não possui
        # nenhuma âncora, exija evidência
        # direta para liberar.
        if (
            c.get(
                "retrieval_strength",
                0
            ) >= 6

            and anchor < .08

            and not strong_evidence
        ):

            return {
                "action":
                    "FALLBACK",

                "reason":
                    "vi614_documentary_anchor_gap",

                "contract":
                    c,
            }


        return {
            "action":
                "ACCEPT",

            "reason":
                "vi614_documentary_accept",

            "score":
                score,

            "anchor":
                anchor,

            "contract":
                c,
        }


    # =================================
    # SAFE CONTEXT FINAL CHECK
    # =================================

    if score < c[
        "min_score"
    ]:

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_score_floor",

            "contract":
                c,
        }


    if semantic < c[
        "min_semantic"
    ]:

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_semantic_floor",

            "contract":
                c,
        }


    # Cenas factuais com retrieval forte
    # não devem passar com contexto solto.
    if (
        role
        in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }

        and c.get(
            "retrieval_strength",
            0
        ) >= 5

        and anchor
        < c[
            "min_anchor"
        ]
    ):

        return {
            "action":
                "FALLBACK",

            "reason":
                "vi614_final_anchor_floor",

            "anchor":
                anchor,

            "required":
                c[
                    "min_anchor"
                ],

            "contract":
                c,
        }


    return {
        "action":
            "ACCEPT",

        "reason":
            "vi614_final_accept",

        "score":
            score,

        "semantic":
            semantic,

        "anchor":
            anchor,

        "contract":
            c,
    }


def self_test():

    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    weak = {

        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_risk":
            "LOW",

        "_vi6_score":
            80,
    }


    result = final_gate(
        weak,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                80,

            "semantic":
                70,

            "anchor":
                .05,

            "role":
                "EVIDENCE",
        }
    )


    assert result[
        "action"
    ] == "FALLBACK"


    strong = final_gate(
        weak,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                85,

            "semantic":
                75,

            "anchor":
                .45,

            "role":
                "EVIDENCE",
        }
    )


    assert strong[
        "action"
    ] == "ACCEPT"


    doc = {

        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_risk":
            "LOW",

        "_vi6_truth_ok":
            True,

        "evidence_class":
            "CASE_DIRECT",
    }


    result = final_gate(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,

            "score":
                90,

            "anchor":
                0,

            "role":
                "EVIDENCE",
        }
    )


    assert result[
        "action"
    ] == "ACCEPT"


    print()
    print(
        "======================================"
    )
    print(
        " VI6.14 PRE-DOWNLOAD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Final Semantic Floor"
    )
    print(
        "OK Final Anchor Floor"
    )
    print(
        "OK Documentary Truth"
    )
    print(
        "OK Case-Direct Exception"
    )
    print(
        "OK CTA Acceptance"
    )
    print()


if __name__ == "__main__":

    self_test()
