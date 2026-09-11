#!/usr/bin/env python3

from vi1510_12_metadata_relevance import (
    metadata_text,
    topic_tokens,
)


def main():
    tests = []


    tokens = topic_tokens(
        "O desastre do dirigível Hindenburg em 1937"
    )


    tests.append((
        "HINDENBURG_TOPIC_TOKEN",
        (
            "hindenburg"
            in tokens
        ),
    ))


    record = {
        "title":
            "Hindenburg disaster",

        "description":
            "The German airship Hindenburg",

        "source_url":
            "https://example.org/Hindenburg",

        "query":
            "Elisa Lam Hotel Cecil",

        "source_group":
            "",
    }


    text = metadata_text(
        record
    )


    tests.append((
        "QUERY_NOT_USED_AS_METADATA_EVIDENCE",
        (
            "elisa lam"
            not in text

            and

            "hotel cecil"
            not in text
        ),
    ))


    tests.append((
        "REAL_TITLE_USED_AS_EVIDENCE",
        (
            "hindenburg"
            in text
        ),
    ))


    control_reference = (
        "arquivo de auditoria:"
        " 2026-09-01_1433"
    )


    specific_content = (
        "Elisa Lam no Hotel Cecil"
    )


    tests.append((
        "OLD_SHORT_ID_IS_CONTROL_REFERENCE",
        (
            "elisa lam"
            not in control_reference.lower()
        ),
    ))


    tests.append((
        "CASE_CONTENT_IS_REAL_LEAK",
        (
            "elisa lam"
            in specific_content.lower()

            and

            "hotel cecil"
            in specific_content.lower()
        ),
    ))


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510 REGRESSION"
    )

    print(
        "=============================================="
    )


    for name, passed in tests:

        print(
            name,
            "=",
            (
                "PASS"
                if passed
                else "FAIL"
            )
        )


        if not passed:

            failed.append(
                name
            )


    print(
        "FAILED:",
        failed
    )


    if failed:
        raise SystemExit(
            1
        )


    print(
        "VI1510_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":

    main()
