#!/usr/bin/env python3

from vi6_10_coverage_predictor import (
    contract
)


VERSION = "6.9"


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def _f(v, default=0.0):

    try:
        return float(v)

    except Exception:
        return float(default)


def check(
    candidate,
    scene,
    meta=None
):

    meta = meta or {}

    c = contract(scene)


    if candidate is None:

        return {
            "action": "FALLBACK",
            "reason": "vi69_no_candidate",
            "contract": c,
        }


    classe = _u(
        meta.get("class")
        or candidate.get("_vi6_class")
        or candidate.get("class")
    )


    risk = _u(
        candidate.get("_vi6_risk")
        or candidate.get("risk")
    )


    quality = _u(
        candidate.get(
            "_vi6_quality_tier"
        )
        or candidate.get(
            "quality_tier"
        )
    )


    truth_ok = bool(
        meta.get(
            "truth_ok",
            candidate.get(
                "_vi6_truth_ok",
                candidate.get(
                    "truth_ok",
                    False
                )
            )
        )
    )


    score = _f(
        meta.get(
            "score",
            candidate.get(
                "_vi6_score",
                candidate.get(
                    "score",
                    0
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
        meta.get("role")
        or c["role"]
    )


    reasons = (
        meta.get("reasons")
        or []
    )


    if isinstance(
        reasons,
        str
    ):
        reasons = [reasons]


    reason_text = " ".join(
        str(x)
        for x in reasons
    ).lower()


    reason_text += " " + _s(
        candidate.get("_vi6_reason")
        or candidate.get("reason")
    ).lower()


    # =================================
    # HARD BLOCKS
    # =================================

    if risk == "HIGH":

        return {
            "action": "FALLBACK",
            "reason": "vi69_high_risk",
            "contract": c,
        }


    if "MISLEADING" in classe:

        return {
            "action": "FALLBACK",
            "reason": "vi69_misleading",
            "contract": c,
        }


    if (
        quality
        and quality not in {
            "NORMAL",
            "CONTROLLED_FALLBACK"
        }
    ):

        return {
            "action": "FALLBACK",
            "reason": "vi69_quality_floor",
            "contract": c,
        }


    # =================================
    # CTA MEMORY
    # =================================

    if role == "CTA":

        return {
            "action": "KEEP",
            "reason": "vi69_cta_reuse",
            "contract": c,
        }


    # =================================
    # DOCUMENTARY
    # =================================

    if classe == "REAL_DOCUMENTARY":

        if not truth_ok:

            return {
                "action": "FALLBACK",
                "reason":
                    "vi69_documentary_truth_failed",
                "contract": c,
            }


        if score < c["min_score"]:

            return {
                "action": "FALLBACK",
                "reason":
                    "vi69_documentary_score_floor",
                "contract": c,
            }


        return {
            "action": "KEEP",
            "reason":
                "vi69_verified_documentary",
            "contract": c,
        }


    # =================================
    # SAFE CONTEXT
    # =================================

    if classe != "SAFE_CONTEXT":

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_unsupported_class",
            "contract": c,
        }


    if score < c["min_score"]:

        return {
            "action": "FALLBACK",
            "reason": "vi69_score_floor",
            "contract": c,
        }


    if semantic < c["min_semantic"]:

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_semantic_floor",
            "contract": c,
        }


    generic = any(
        marker in reason_text

        for marker in (
            "generic_stock",
            "generic_context",
            "generic_person",
            "generic_place",
            "weak_anchor_stock",
        )
    )


    guard = c[
        "generic_guard"
    ]


    if (
        generic
        and guard == "STRICT"
        and anchor < c["min_anchor"]
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_strict_veto",
            "contract": c,
        }


    if (
        generic
        and guard == "MEDIUM"
        and anchor < c["min_anchor"]
        and semantic < 62
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_medium_veto",
            "contract": c,
        }


    if (
        role == "EVIDENCE"
        and (
            semantic < 60
            or anchor < .18
        )
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_stock_not_evidence_grade",
            "contract": c,
        }


    if (
        role == "PERSON"
        and generic
        and anchor < .20
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_random_person_veto",
            "contract": c,
        }


    if (
        role == "PLACE"
        and generic
        and anchor < .14
    ):

        return {
            "action": "FALLBACK",
            "reason":
                "vi69_generic_place_veto",
            "contract": c,
        }


    return {
        "action": "KEEP",
        "reason": "vi69_quality_pass",
        "contract": c,
    }


def self_test():

    scene = {
        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchor_strength_6_7":
            7,
    }


    stock = {
        "_vi6_class":
            "SAFE_CONTEXT",

        "_vi6_risk":
            "LOW",

        "_vi6_quality_tier":
            "NORMAL",

        "_vi6_truth_ok":
            True,

        "_vi6_score":
            80,

        "_vi6_reason":
            "generic_context_without_identity_claim",
    }


    x = check(
        stock,
        scene,
        {
            "class":
                "SAFE_CONTEXT",

            "score":
                80,

            "semantic":
                50,

            "anchor":
                .05,

            "role":
                "EVIDENCE",

            "reasons":
                ["generic_stock"]
        }
    )

    assert x["action"] == "FALLBACK"


    x = check(
        stock,
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

            "reasons":
                ["relevant_motion"]
        }
    )

    assert x["action"] == "KEEP"


    doc = {
        "_vi6_class":
            "REAL_DOCUMENTARY",

        "_vi6_risk":
            "LOW",

        "_vi6_quality_tier":
            "NORMAL",

        "_vi6_truth_ok":
            False,

        "_vi6_score":
            100,
    }


    x = check(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                100,

            "truth_ok":
                False,

            "role":
                "EVIDENCE",
        }
    )

    assert x["action"] == "FALLBACK"


    doc[
        "_vi6_truth_ok"
    ] = True


    x = check(
        doc,
        scene,
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                100,

            "truth_ok":
                True,

            "role":
                "EVIDENCE",
        }
    )

    assert x["action"] == "KEEP"


    print()
    print("======================================")
    print(" VI6.9 FIREWALL SELF TEST: PASS")
    print("======================================")
    print("OK Generic Evidence Veto")
    print("OK Strong Evidence Context")
    print("OK Documentary Truth Lock")
    print("OK Semantic Floor")
    print("OK Anchor Floor")
    print()


if __name__ == "__main__":
    self_test()
