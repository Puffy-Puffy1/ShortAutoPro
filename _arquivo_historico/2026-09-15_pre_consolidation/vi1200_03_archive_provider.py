#!/usr/bin/env python3

import html
import re

from vi1200_01_real_transport import (
    get_json,
)


API = (
    "https://archive.org/"
    "advancedsearch.php"
)


def clean(
    value
):
    if isinstance(
        value,
        list
    ):
        value = " ".join(
            str(item)
            for item in value
        )

    value = html.unescape(
        str(
            value
            or ""
        )
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def search(
    query,
    limit=4
):
    params = [
        (
            "q",
            query
        ),

        (
            "fl[]",
            "identifier"
        ),

        (
            "fl[]",
            "title"
        ),

        (
            "fl[]",
            "description"
        ),

        (
            "fl[]",
            "mediatype"
        ),

        (
            "fl[]",
            "creator"
        ),

        (
            "fl[]",
            "licenseurl"
        ),

        (
            "rows",
            str(
                int(
                    limit
                )
            )
        ),

        (
            "page",
            "1"
        ),

        (
            "output",
            "json"
        ),
    ]


    response = get_json(
        API,
        params
    )


    if not response[
        "ok"
    ]:
        return {
            "ok":
                False,

            "query":
                query,

            "results":
                [],

            "error":
                response.get(
                    "error"
                ),
        }


    docs = (
        response[
            "data"
        ].get(
            "response",
            {}
        ).get(
            "docs",
            []
        )
        or []
    )


    results = []


    for doc in docs:
        identifier = clean(
            doc.get(
                "identifier"
            )
        )

        results.append({
            "provider":
                "INTERNET_ARCHIVE",

            "identifier":
                identifier,

            "title":
                clean(
                    doc.get(
                        "title"
                    )
                ),

            "description":
                clean(
                    doc.get(
                        "description"
                    )
                ),

            "creator":
                clean(
                    doc.get(
                        "creator"
                    )
                ),

            "mediatype":
                clean(
                    doc.get(
                        "mediatype"
                    )
                ),

            "license":
                clean(
                    doc.get(
                        "licenseurl"
                    )
                ),

            "license_url":
                clean(
                    doc.get(
                        "licenseurl"
                    )
                ),

            "remote_url":
                (
                    "https://archive.org/"
                    "details/"
                    + identifier
                    if identifier
                    else ""
                ),

            "metadata_only":
                True,
        })


    return {
        "ok":
            True,

        "query":
            query,

        "results":
            results,

        "count":
            len(
                results
            ),
    }


if __name__ == "__main__":
    print(
        "VI1200 ARCHIVE PROVIDER=PASS"
    )
