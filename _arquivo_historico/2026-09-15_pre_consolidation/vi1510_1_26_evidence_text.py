#!/usr/bin/env python3

import html
import re
import unicodedata


DENIED_KEY_PARTS = {
    "query",
    "queries",
    "search",
    "searches",
    "prompt",
    "topic",
    "keyword",
    "keywords",
    "asset_query",
    "visual",
    "narration",
    "segment",
    "headline",
    "emphasis",
    "script",
    "roteiro",
    "request",
}


PATH_ONLY_KEYS = {
    "asset",
    "path",
    "local_path",
    "downloaded_path",
    "output",
    "destination",
}


def clean(
    value,
):
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


    value = re.sub(
        r"\s+",
        " ",
        value
    )


    return value.strip()


def key_denied(
    key,
):
    key = str(
        key
    ).lower()


    return (
        key in DENIED_KEY_PARTS

        or

        key in PATH_ONLY_KEYS

        or

        any(
            (
                "_"
                +
                part
            )
            in key

            for part
            in DENIED_KEY_PARTS
        )
    )


def collect_values(
    value,
    *,
    parent_key="",
):
    values = []


    if isinstance(
        value,
        dict
    ):

        for key, item in value.items():

            if key_denied(
                key
            ):
                continue


            values.extend(
                collect_values(
                    item,
                    parent_key=str(
                        key
                    ),
                )
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            values.extend(
                collect_values(
                    item,
                    parent_key=parent_key,
                )
            )


    elif isinstance(
        value,
        (
            str,
            int,
            float,
        )
    ):

        text = clean(
            value
        )


        if (
            text

            and

            len(
                text
            ) >= 2
        ):

            values.append(
                text[
                    :1200
                ]
            )


    return values


def evidence_blob(
    value,
):
    unique = []

    seen = set()


    for item in collect_values(
        value
    ):

        key = item.lower()


        if key in seen:
            continue


        seen.add(
            key
        )


        unique.append(
            item
        )


    return " | ".join(
        unique
    )[
        :12000
    ]


def folded(
    value,
):
    value = unicodedata.normalize(
        "NFKD",
        str(
            value
            or ""
        )
    )


    value = "".join(
        character

        for character in value

        if not unicodedata.combining(
            character
        )
    )


    value = value.lower()


    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )


    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()
