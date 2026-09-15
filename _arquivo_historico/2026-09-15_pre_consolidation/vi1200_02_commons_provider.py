#!/usr/bin/env python3

import html
import re

from vi1200_01_real_transport import (
    get_json,
)


API = (
    "https://commons.wikimedia.org/"
    "w/api.php"
)


def clean_html(
    value
):
    if isinstance(
        value,
        dict
    ):
        value = value.get(
            "value",
            ""
        )

    value = str(
        value
        or ""
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html.unescape(
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def ext_value(
    metadata,
    key
):
    return clean_html(
        (
            metadata.get(
                key
            )
            or {}
        ).get(
            "value",
            ""
        )
    )


def normalize_page(
    page
):
    info_list = (
        page.get(
            "imageinfo"
        )
        or []
    )

    info = (
        info_list[0]
        if info_list
        else {}
    )

    metadata = (
        info.get(
            "extmetadata"
        )
        or {}
    )


    return {
        "provider":
            "WIKIMEDIA_COMMONS",

        "pageid":
            page.get(
                "pageid"
            ),

        "title":
            page.get(
                "title",
                ""
            ),

        "description":
            ext_value(
                metadata,
                "ImageDescription"
            ),

        "object_name":
            ext_value(
                metadata,
                "ObjectName"
            ),

        "categories":
            ext_value(
                metadata,
                "Categories"
            ),

        "artist":
            ext_value(
                metadata,
                "Artist"
            ),

        "credit":
            ext_value(
                metadata,
                "Credit"
            ),

        "license":
            (
                ext_value(
                    metadata,
                    "LicenseShortName"
                )
                or
                ext_value(
                    metadata,
                    "UsageTerms"
                )
            ),

        "license_url":
            ext_value(
                metadata,
                "LicenseUrl"
            ),

        "width":
            info.get(
                "width",
                0
            ),

        "height":
            info.get(
                "height",
                0
            ),

        "mime":
            info.get(
                "mime",
                ""
            ),

        "remote_url":
            info.get(
                "url",
                ""
            ),

        "description_url":
            info.get(
                "descriptionurl",
                ""
            ),

        "metadata_only":
            True,
    }


def search(
    query,
    limit=5
):
    response = get_json(
        API,
        {
            "action":
                "query",

            "format":
                "json",

            "formatversion":
                "2",

            "generator":
                "search",

            "gsrsearch":
                query,

            "gsrnamespace":
                "6",

            "gsrlimit":
                int(
                    limit
                ),

            "gsrwhat":
                "text",

            "prop":
                "imageinfo",

            "iiprop":
                (
                    "url|size|mime|"
                    "extmetadata"
                ),

            "maxlag":
                "5",
        }
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


    pages = (
        response[
            "data"
        ].get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
        or []
    )


    return {
        "ok":
            True,

        "query":
            query,

        "results":
            [
                normalize_page(
                    page
                )
                for page in pages
            ],

        "count":
            len(
                pages
            ),
    }


def exact_titles(
    titles
):
    response = get_json(
        API,
        {
            "action":
                "query",

            "format":
                "json",

            "formatversion":
                "2",

            "titles":
                "|".join(
                    titles
                ),

            "prop":
                "imageinfo",

            "iiprop":
                (
                    "url|size|mime|"
                    "extmetadata"
                ),

            "maxlag":
                "5",
        }
    )


    if not response[
        "ok"
    ]:
        return {
            "ok":
                False,

            "results":
                [],

            "error":
                response.get(
                    "error"
                ),
        }


    pages = (
        response[
            "data"
        ].get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
        or []
    )


    valid = [
        normalize_page(
            page
        )
        for page in pages
        if not page.get(
            "missing"
        )
    ]


    return {
        "ok":
            True,

        "results":
            valid,

        "count":
            len(
                valid
            ),
    }


if __name__ == "__main__":
    print(
        "VI1200 COMMONS PROVIDER=PASS"
    )
