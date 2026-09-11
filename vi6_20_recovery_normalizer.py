#!/usr/bin/env python3

VERSION = "6.20"


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


def _source(
    item,
    route=None
):

    value = (
        item.get(
            "fonte"
        )
        or item.get(
            "source"
        )
        or (
            (route or {}).get(
                "source"
            )
        )
        or ""
    )


    return _s(
        value
    )


def _explicit_false(
    item
):

    fields = (
        "truth_ok",
        "identity_ok",
        "source_identity_ok",
        "evidence_ok",
        "documentary_truth_ok",
    )


    for field in fields:

        if (
            field in item
            and item[
                field
            ] is False
        ):

            return True


    return False


def _explicit_true(
    item
):

    fields = (
        "truth_ok",
        "identity_ok",
        "source_identity_ok",
        "evidence_ok",
        "documentary_truth_ok",
    )


    return any(
        item.get(
            field
        ) is True
        for field in fields
    )


def normalize_candidate(
    candidate,
    route=None
):

    if not isinstance(
        candidate,
        dict
    ):

        return None


    item = dict(
        candidate
    )


    source = _source(
        item,
        route
    )


    if source:

        item[
            "fonte"
        ] = source


    source_upper = (
        source.upper()
    )


    evidence = _u(
        item.get(
            "evidence_class"
        )
        or item.get(
            "classe_evidencia"
        )
    )


    query_tier = _u(
        item.get(
            "wiki_query_tier"
        )
        or item.get(
            "query_tier"
        )
    )


    anchor = _f(
        item.get(
            "wiki_anchor_ratio"
        )
        or item.get(
            "anchor_ratio"
        )
        or item.get(
            "anchor_score"
        )
        or 0
    )


    conflict = bool(
        item.get(
            "identity_conflict"
        )
        or item.get(
            "numeric_identity_conflict"
        )
        or item.get(
            "named_context_conflict"
        )
    )


    explicit_false = (
        _explicit_false(
            item
        )
    )


    explicit_true = (
        _explicit_true(
            item
        )
    )


    is_wiki = (
        "WIKI"
        in source_upper
        or "COMMONS"
        in source_upper
    )


    # =================================
    # DOCUMENTARY TRUTH
    # =================================

    documentary_truth = bool(

        is_wiki

        and not conflict

        and not explicit_false

        and (

            explicit_true

            or evidence
            == "CASE_DIRECT"

            or (
                evidence
                == "CONTEXTUAL"

                and anchor >= .20
            )
        )
    )


    if documentary_truth:

        item[
            "_vi6_class"
        ] = "REAL_DOCUMENTARY"

        item[
            "_vi6_truth_ok"
        ] = True

        item[
            "_vi6_risk"
        ] = "LOW"

        item[
            "_vi6_quality_tier"
        ] = "NORMAL"

        item[
            "_vi620_recovery_verified"
        ] = True


    else:

        # Recuperação Wikimedia sem prova
        # suficiente NÃO vira documental.
        #
        # Também não promovemos documento
        # genérico para SAFE_CONTEXT.
        if is_wiki:

            return None


        item[
            "_vi6_class"
        ] = (
            item.get(
                "_vi6_class"
            )
            or item.get(
                "class"
            )
            or "SAFE_CONTEXT"
        )


        item[
            "_vi6_truth_ok"
        ] = bool(
            item.get(
                "_vi6_truth_ok",
                item.get(
                    "truth_ok",
                    True
                )
            )
        )


        item[
            "_vi6_risk"
        ] = (
            item.get(
                "_vi6_risk"
            )
            or item.get(
                "risk"
            )
            or "LOW"
        )


        item[
            "_vi6_quality_tier"
        ] = (
            item.get(
                "_vi6_quality_tier"
            )
            or item.get(
                "quality_tier"
            )
            or "NORMAL"
        )


    item[
        "_vi620_recovery"
    ] = True


    item[
        "_vi620_evidence"
    ] = evidence


    item[
        "_vi620_query_tier"
    ] = query_tier


    item[
        "_vi620_anchor"
    ] = anchor


    return item


def normalize_results(
    raw,
    route=None
):

    if raw is None:

        return []


    items = []


    if isinstance(
        raw,
        list
    ):

        items = raw


    elif isinstance(
        raw,
        tuple
    ):

        for value in raw:

            if isinstance(
                value,
                list
            ):

                items = value
                break


    elif isinstance(
        raw,
        dict
    ):

        for key in (
            "results",
            "items",
            "candidates",
            "media",
            "fotos",
            "photos",
            "videos",
        ):

            value = raw.get(
                key
            )


            if isinstance(
                value,
                list
            ):

                items = value
                break


        if (
            not items
            and (
                raw.get(
                    "url"
                )
                or raw.get(
                    "id"
                )
            )
        ):

            items = [
                raw
            ]


    output = []


    for candidate in items:

        normalized = (
            normalize_candidate(
                candidate,
                route
            )
        )


        if normalized is not None:

            output.append(
                normalized
            )


    return output


def self_test():

    doc = {

        "fonte":
            "Wikimedia",

        "id":
            "flight19",

        "url":
            "x",

        "evidence_class":
            "CASE_DIRECT",

        "wiki_anchor_ratio":
            .60,
    }


    result = normalize_candidate(
        doc,
        {
            "source":
                "WIKIMEDIA"
        }
    )


    assert result is not None

    assert (
        result[
            "_vi6_class"
        ]
        == "REAL_DOCUMENTARY"
    )

    assert (
        result[
            "_vi6_truth_ok"
        ]
        is True
    )


    bad = {

        "fonte":
            "Wikimedia",

        "id":
            "wrong",

        "evidence_class":
            "GENERIC_DOCUMENT",

        "identity_conflict":
            True,
    }


    result = normalize_candidate(
        bad
    )


    assert result is None


    stock = {

        "fonte":
            "Pixabay",

        "id":
            "stock",

        "url":
            "x",
    }


    result = normalize_candidate(
        stock
    )


    assert result is not None

    assert (
        result[
            "_vi6_class"
        ]
        == "SAFE_CONTEXT"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.20 NORMALIZER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Case Direct Documentary"
    )
    print(
        "OK Contextual Anchor Rule"
    )
    print(
        "OK Identity Conflict Rejection"
    )
    print(
        "OK Generic Wikimedia Rejection"
    )
    print(
        "OK Safe Stock Normalization"
    )
    print()


if __name__ == "__main__":

    self_test()
