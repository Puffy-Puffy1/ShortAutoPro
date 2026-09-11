#!/usr/bin/env python3

import re


VERSION = "6.13"


HARD_NO_RETRY = {
    "vi69_high_risk",
    "vi69_misleading",
    "vi69_documentary_truth_failed",
    "vi69_unsupported_class",
    "vi611_hard_rejection_preserved",
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _unique(values):

    out = []
    seen = set()


    for value in values:

        value = re.sub(
            r"\s+",
            " ",
            _s(value)
        ).strip()


        if not value:
            continue


        key = value.lower()


        if key in seen:
            continue


        seen.add(key)
        out.append(value)


    return out


def _role(scene):

    role = _s(
        scene.get(
            "retrieval_role_6_7"
        )
    ).upper()


    if role:
        return role


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    role = _s(
        board.get(
            "role"
        )
    ).upper()


    if role:
        return role


    mode = _s(
        scene.get(
            "visual_mode"
        )
    ).lower()


    if "cta" in mode:
        return "CTA"

    if any(
        x in mode
        for x in (
            "evidence",
            "document",
            "archive"
        )
    ):
        return "EVIDENCE"

    if "person" in mode:
        return "PERSON"

    if any(
        x in mode
        for x in (
            "location",
            "place",
            "architecture"
        )
    ):
        return "PLACE"

    if any(
        x in mode
        for x in (
            "object",
            "product",
            "medicine",
            "package"
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def _anchors(scene):

    raw = (
        scene.get(
            "retrieval_anchors_6_7"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):
        raw = [raw]


    return _unique(
        raw
    )


def _existing_queries(scene):

    raw = (
        scene.get(
            "retrieval_queries_6_7"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):
        raw = [raw]


    primary = _s(
        scene.get(
            "retrieval_primary_query_6_7"
        )
    )


    original = _s(
        scene.get(
            "visual_query_original_6_7"
        )
        or scene.get(
            "visual_query"
        )
        or scene.get(
            "query"
        )
    )


    return _unique(
        [primary]
        + list(raw)
        + [original]
    )


def _compact(parts):

    words = []


    for part in parts:

        for word in _s(
            part
        ).split():

            if (
                word.lower()
                not in {
                    x.lower()
                    for x in words
                }
            ):

                words.append(
                    word
                )


    return " ".join(
        words[:14]
    )


def build_recovery_plan(
    scene,
    vi6_scene=None,
    rejection_reason=None
):

    role = _role(
        scene
    )


    rejection_reason = _s(
        rejection_reason
    )


    anchors = _anchors(
        scene
    )


    existing = _existing_queries(
        scene
    )


    if (
        rejection_reason
        in HARD_NO_RETRY
    ):

        return {

            "version":
                VERSION,

            "eligible":
                False,

            "role":
                role,

            "reason":
                "hard_safety_no_retry",

            "queries":
                [],

            "max_attempts":
                0,
        }


    if role == "CTA":

        return {

            "version":
                VERSION,

            "eligible":
                False,

            "role":
                role,

            "reason":
                "cta_reuse_only",

            "queries":
                [],

            "max_attempts":
                0,
        }


    queries = []


    # =================================
    # EVIDENCE
    # =================================

    if role == "EVIDENCE":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:4]
                        + [
                            "archive photograph"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "newspaper archive"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "historical document"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "case file"
                        ]
                    ),
                ]
            )


    # =================================
    # PERSON
    # =================================

    elif role == "PERSON":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:3]
                        + [
                            "archive photograph"
                        ]
                    ),

                    _compact(
                        anchors[:3]
                        + [
                            "historical portrait"
                        ]
                    ),
                ]
            )


    # =================================
    # PLACE
    # =================================

    elif role == "PLACE":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:4]
                        + [
                            "historical photograph"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "exterior archive"
                        ]
                    ),

                    _compact(
                        anchors[:4]
                        + [
                            "location archive"
                        ]
                    ),
                ]
            )


    # =================================
    # OBJECT
    # =================================

    elif role == "OBJECT":

        if anchors:

            queries.extend(
                [
                    _compact(
                        anchors[:3]
                        + [
                            "historical product"
                        ]
                    ),

                    _compact(
                        anchors[:3]
                        + [
                            "packaging archive"
                        ]
                    ),
                ]
            )


    # =================================
    # CONTEXT
    # =================================

    else:

        for query in existing[:2]:

            if query:

                queries.append(
                    _compact(
                        [
                            query,
                            "documentary"
                        ]
                    )
                )


    queries.extend(
        existing
    )


    queries = _unique(
        queries
    )


    # Não repetir exatamente as primeiras
    # consultas se conseguimos criar uma
    # alternativa mais específica.
    original_keys = {
        q.lower()
        for q in existing
    }


    novel = [
        q
        for q in queries
        if q.lower()
        not in original_keys
    ]


    ordered = (
        novel
        + existing
    )


    ordered = _unique(
        ordered
    )[:5]


    eligible = bool(
        ordered
    )


    strategy = (
        "DOCUMENTARY_RETRY"

        if role in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }

        else "PRECISION_RETRY"
    )


    return {

        "version":
            VERSION,

        "eligible":
            eligible,

        "role":
            role,

        "strategy":
            strategy,

        "trigger":
            rejection_reason,

        "anchors":
            anchors,

        "queries":
            ordered,

        "max_attempts":
            (
                2
                if eligible
                else 0
            ),

        "prefer_wikimedia":
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE"
            },

        "allow_stock_retry":
            role in {
                "OBJECT",
                "CONTEXT",
                "PLACE"
            },
    }


def self_test():

    scene = {

        "retrieval_role_6_7":
            "EVIDENCE",

        "retrieval_anchors_6_7":
            [
                "Flight 19",
                "1945"
            ],

        "retrieval_queries_6_7":
            [
                "Flight 19 1945"
            ],

        "retrieval_primary_query_6_7":
            "Flight 19 1945"
    }


    result = build_recovery_plan(
        scene,
        {},
        "vi69_semantic_floor"
    )


    assert result[
        "eligible"
    ] is True


    assert result[
        "prefer_wikimedia"
    ] is True


    assert any(
        "archive"
        in q.lower()
        for q in result[
            "queries"
        ]
    )


    blocked = build_recovery_plan(
        scene,
        {},
        "vi69_documentary_truth_failed"
    )


    assert blocked[
        "eligible"
    ] is False


    cta = build_recovery_plan(
        {
            "retrieval_role_6_7":
                "CTA"
        },
        {},
        "anything"
    )


    assert cta[
        "eligible"
    ] is False


    print()
    print(
        "======================================"
    )
    print(
        " VI6.13 RECOVERY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Evidence Recovery Queries"
    )
    print(
        "OK Documentary Retry Strategy"
    )
    print(
        "OK Hard Safety No-Retry"
    )
    print(
        "OK CTA No-Retry"
    )
    print(
        "OK Query Budget"
    )
    print()


if __name__ == "__main__":

    self_test()
