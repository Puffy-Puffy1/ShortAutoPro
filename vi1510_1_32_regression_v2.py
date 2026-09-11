#!/usr/bin/env python3

import inspect

from pathlib import Path


from vi1510_1_25_scene_usage import (
    collect,
)

from vi1510_1_26_evidence_text import (
    evidence_blob,
)

from vi1510_1_28_relevance_v2 import (
    tokens,
)

from vi1510_1_29_lineage_v2 import (
    similarity,
)


def check(
    name,
    actual,
    expected,
    failed,
):
    passed = (
        actual
        ==
        expected
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
        actual,
    )


    if not passed:

        failed.append(
            name
        )


def main():
    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510.1 V2.2 ADVERSARIAL REGRESSION"
    )

    print(
        "=============================================="
    )


    signature = inspect.signature(
        collect
    )


    check(
        "SCENE_USAGE_SIGNATURE_COMPATIBLE",
        (
            "run"
            in signature.parameters

            and

            "run_dir"
            in signature.parameters

            and

            "fallback_inventory"
            in signature.parameters

            and

            signature.parameters[
                "fallback_inventory"
            ].default
            is not inspect._empty
        ),
        True,
        failed,
    )


    evidence = evidence_blob({
        "title":
            "Independent historical object",

        "query":
            "CONTAMINATING QUERY SHOULD DISAPPEAR",

        "search_query":
            "CONTAMINATING SEARCH SHOULD DISAPPEAR",

        "description":
            "Independent source description",
    })


    check(
        "QUERY_NOT_IN_EVIDENCE",
        (
            "CONTAMINATING"
            not in evidence
        ),
        True,
        failed,
    )


    generic_tokens = tokens(
        "The unexplained disappearance of Example Colony"
    )


    check(
        "TOPIC_TOKENIZER_OPERATIONAL",
        bool(
            generic_tokens
        ),
        True,
        failed,
    )


    # --------------------------------------------------
    # Scene number alone must never prove lineage.
    # --------------------------------------------------

    asset = {
        "scene":
            5,

        "path":
            "/tmp/a.jpg",

        "sha256":
            "a" * 64,
    }


    unrelated = {
        "scene":
            5,

        "local_path":
            "/tmp/b.jpg",

        "sha256":
            "b" * 64,

        "title":
            "Different file",

        "source_url":
            "https://example.org/different.jpg",
    }


    score, reasons = similarity(
        asset,
        unrelated,
    )


    check(
        "SCENE_ONLY_SCORE_ZERO",
        score,
        0,
        failed,
    )


    # --------------------------------------------------
    # SHA is decisive independent evidence.
    # --------------------------------------------------

    sha_record = {
        "scene":
            9,

        "sha256":
            "a" * 64,
    }


    score, reasons = similarity(
        asset,
        sha_record,
    )


    check(
        "SHA256_EXACT_CERTIFIES",
        (
            score >= 300
            and
            "sha256_exact"
            in reasons
        ),
        True,
        failed,
    )


    # --------------------------------------------------
    # Exact source group is strong evidence.
    # --------------------------------------------------

    group_asset = {
        "scene":
            1,

        "source_group":
            "COMMONS:12345",
    }


    group_record = {
        "scene":
            2,

        "source_group":
            "COMMONS:12345",
    }


    score, reasons = similarity(
        group_asset,
        group_record,
    )


    check(
        "SOURCE_GROUP_EXACT_CERTIFIES",
        (
            score >= 220
            and
            "source_group_exact"
            in reasons
        ),
        True,
        failed,
    )


    # --------------------------------------------------
    # Canonical URL strips tracking parameters.
    # --------------------------------------------------

    url_asset = {
        "source_url":
            (
                "https://upload.wikimedia.org/"
                "wikipedia/commons/a/a1/file.jpg"
                "?utm_source=test"
            )
    }


    url_record = {
        "source_url":
            (
                "https://upload.wikimedia.org/"
                "wikipedia/commons/a/a1/file.jpg"
            )
    }


    score, reasons = similarity(
        url_asset,
        url_record,
    )


    check(
        "CANONICAL_URL_CERTIFIES",
        (
            score >= 200
            and
            "canonical_url_exact"
            in reasons
        ),
        True,
        failed,
    )


    # --------------------------------------------------
    # Canonical titles.
    # --------------------------------------------------

    title_asset = {
        "title":
            "File:Example Historic Photograph.jpg"
    }


    title_record = {
        "title":
            "Example Historic Photograph"
    }


    score, reasons = similarity(
        title_asset,
        title_record,
    )


    check(
        "CANONICAL_TITLE_CERTIFIES",
        (
            score >= 170
            and
            "canonical_title_exact"
            in reasons
        ),
        True,
        failed,
    )


    print()
    print(
        "FAILED:",
        failed
    )


    if failed:

        print(
            "STATUS: VI1510_1_V2_REGRESSION_HOLD"
        )

        raise SystemExit(
            1
        )


    print(
        "STATUS: VI1510_1_V2_REGRESSION_CERTIFIED"
    )

    print(
        "VI1510.1 V2.2 ADVERSARIAL REGRESSION=PASS"
    )


if __name__ == "__main__":
    main()
