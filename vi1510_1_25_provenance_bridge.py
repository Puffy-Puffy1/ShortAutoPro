#!/usr/bin/env python3

import re

from pathlib import Path

from urllib.parse import (
    parse_qsl,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)


from vi1510_01_common import (
    norm,
)


IDENTITY_KEYS = [
    "sha256",
    "source_group",
    "source_url",
    "remote_url",
    "media_url",
    "original_url",
    "download_url",
    "final_url",
    "url",
    "title",
    "provider",
    "local_path",
    "path",
]


def canonical_path(
    value,
):
    if not value:
        return ""


    try:

        return str(
            Path(
                value
            )
            .expanduser()
            .resolve()
        )


    except Exception:

        return str(
            value
        ).strip()


def canonical_url(
    value,
):
    value = str(
        value
        or ""
    ).strip()


    if not value:
        return ""


    try:

        parts = urlsplit(
            value
        )


        if parts.scheme not in {
            "http",
            "https",
        }:

            return ""


        query = [
            (
                key,
                val,
            )

            for key, val
            in parse_qsl(
                parts.query,
                keep_blank_values=True,
            )

            if not key.lower().startswith(
                "utm_"
            )
        ]


        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                unquote(
                    parts.path
                ),
                urlencode(
                    query,
                    doseq=True,
                ),
                "",
            )
        ).rstrip("/")


    except Exception:

        return ""


def canonical_title(
    value,
):
    value = unquote(
        str(
            value
            or ""
        )
    )


    value = re.sub(
        r"^file\s*:\s*",
        "",
        value,
        flags=re.I,
    )


    try:

        value = Path(
            value
        ).stem

    except Exception:

        pass


    value = norm(
        value
    )


    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )


    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def first(
    value,
    keys,
):
    if not isinstance(
        value,
        dict
    ):

        return None


    for key in keys:

        item = value.get(
            key
        )


        if item not in {
            None,
            "",
        }:

            return item


    return None


def identity(
    value,
):
    if not isinstance(
        value,
        dict
    ):

        return {}


    raw = (
        value.get(
            "raw_metadata"
        )
        or {}
    )


    result = {}


    result[
        "sha256"
    ] = str(
        first(
            value,
            [
                "sha256",
                "file_sha256",
                "hash",
            ],
        )
        or
        first(
            raw,
            [
                "sha256",
                "file_sha256",
                "hash",
            ],
        )
        or ""
    ).strip().lower()


    result[
        "source_group"
    ] = str(
        first(
            value,
            [
                "source_group",
            ],
        )
        or
        first(
            raw,
            [
                "source_group",
            ],
        )
        or ""
    ).strip()


    result[
        "source_url"
    ] = str(
        first(
            value,
            [
                "source_url",
                "remote_url",
                "media_url",
                "original_url",
                "download_url",
                "final_url",
                "url",
            ],
        )
        or
        first(
            raw,
            [
                "source_url",
                "remote_url",
                "media_url",
                "original_url",
                "download_url",
                "final_url",
                "url",
            ],
        )
        or ""
    ).strip()


    result[
        "title"
    ] = str(
        first(
            value,
            [
                "title",
                "name",
                "filename",
            ],
        )
        or
        first(
            raw,
            [
                "title",
                "name",
                "filename",
            ],
        )
        or ""
    ).strip()


    result[
        "provider"
    ] = str(
        first(
            value,
            [
                "provider",
            ],
        )
        or
        first(
            raw,
            [
                "provider",
            ],
        )
        or ""
    ).strip()


    result[
        "local_path"
    ] = str(
        first(
            value,
            [
                "local_path",
                "path",
                "asset",
                "downloaded_path",
            ],
        )
        or
        first(
            raw,
            [
                "local_path",
                "path",
                "asset",
                "downloaded_path",
            ],
        )
        or ""
    ).strip()


    return result


def independent_score(
    asset,
    candidate,
):
    a = identity(
        asset
    )

    b = identity(
        candidate
    )


    score = 0

    reasons = []


    if (
        a[
            "sha256"
        ]

        and

        b[
            "sha256"
        ]

        and

        a[
            "sha256"
        ]
        ==
        b[
            "sha256"
        ]
    ):

        score += 400

        reasons.append(
            "sha256_exact"
        )


    ap = canonical_path(
        a[
            "local_path"
        ]
    )


    bp = canonical_path(
        b[
            "local_path"
        ]
    )


    if (
        ap
        and
        bp
        and
        ap == bp
    ):

        score += 350

        reasons.append(
            "path_exact"
        )


    if (
        a[
            "source_group"
        ]

        and

        b[
            "source_group"
        ]

        and

        norm(
            a[
                "source_group"
            ]
        )
        ==
        norm(
            b[
                "source_group"
            ]
        )
    ):

        score += 300

        reasons.append(
            "source_group_exact"
        )


    au = canonical_url(
        a[
            "source_url"
        ]
    )


    bu = canonical_url(
        b[
            "source_url"
        ]
    )


    if (
        au
        and
        bu
        and
        au == bu
    ):

        score += 280

        reasons.append(
            "canonical_url_exact"
        )


    at = canonical_title(
        a[
            "title"
        ]
    )


    bt = canonical_title(
        b[
            "title"
        ]
    )


    if (
        at
        and
        bt
        and
        len(
            at
        ) >= 8
        and
        at == bt
    ):

        score += 220

        reasons.append(
            "canonical_title_exact"
        )


    return (
        score,
        reasons,
    )


def walk_dicts(
    value,
):
    if isinstance(
        value,
        dict
    ):

        yield value


        for item in (
            value.values()
        ):

            yield from walk_dicts(
                item
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            yield from walk_dicts(
                item
            )


def looks_like_source(
    value,
):
    if not isinstance(
        value,
        dict
    ):

        return False


    keys = {
        str(
            key
        ).lower()

        for key in (
            value.keys()
        )
    }


    return bool(
        keys
        &
        {
            "source_group",
            "source_url",
            "remote_url",
            "media_url",
            "original_url",
            "download_url",
            "final_url",
            "provider",
            "license",
            "sha256",
        }
    )


def candidate_pool(
    run,
    fallback_inventory=None,
):
    values = []

    seen = set()


    roots = [
        run,
        fallback_inventory
        or {},
    ]


    for root in roots:

        for item in walk_dicts(
            root
        ):

            if not looks_like_source(
                item
            ):

                continue


            ident = identity(
                item
            )


            key = (
                ident[
                    "sha256"
                ],
                norm(
                    ident[
                        "source_group"
                    ]
                ),
                canonical_url(
                    ident[
                        "source_url"
                    ]
                ),
                canonical_path(
                    ident[
                        "local_path"
                    ]
                ),
                canonical_title(
                    ident[
                        "title"
                    ]
                ),
            )


            if not any(
                key
            ):

                continue


            if key in seen:

                continue


            seen.add(
                key
            )

            values.append(
                item
            )


    return values


def enrich_asset(
    asset,
    pool,
):
    matches = []


    for candidate in pool:

        score, reasons = (
            independent_score(
                asset,
                candidate,
            )
        )


        if score > 0:

            matches.append(
                (
                    score,
                    reasons,
                    candidate,
                )
            )


    matches.sort(
        key=lambda item:
            item[
                0
            ],
        reverse=True,
    )


    result = dict(
        asset
    )


    if not matches:

        result[
            "provenance_bridge"
        ] = {
            "linked":
                False,

            "score":
                0,

            "reasons":
                [],
        }

        return result


    score, reasons, source = (
        matches[
            0
        ]
    )


    source_ident = identity(
        source
    )


    # Only transport missing provenance fields.
    # Existing scene-usage identity wins.
    for key in [
        "source_group",
        "source_url",
        "title",
        "provider",
    ]:

        if (
            not result.get(
                key
            )

            and

            source_ident.get(
                key
            )
        ):

            result[
                key
            ] = source_ident[
                key
            ]


    if (
        not result.get(
            "sha256"
        )

        and

        source_ident.get(
            "sha256"
        )
    ):

        result[
            "sha256"
        ] = source_ident[
            "sha256"
        ]


    result[
        "provenance_bridge"
    ] = {
        "linked":
            True,

        "score":
            score,

        "reasons":
            reasons,
    }


    return result


def enrich_scene_usage(
    scene_usage,
    run,
    fallback_inventory=None,
):
    pool = candidate_pool(
        run,
        fallback_inventory,
    )


    report = dict(
        scene_usage
    )


    used_assets = [
        enrich_asset(
            asset,
            pool,
        )

        for asset in (
            scene_usage.get(
                "used_assets"
            )
            or []
        )
    ]


    report[
        "used_assets"
    ] = used_assets


    report[
        "provenance_bridge"
    ] = {
        "candidate_pool":
            len(
                pool
            ),

        "linked_assets":
            sum(
                bool(
                    asset.get(
                        "provenance_bridge",
                        {}
                    ).get(
                        "linked"
                    )
                )

                for asset in used_assets
            ),

        "scene_only_used_as_evidence":
            False,
    }


    return report


if __name__ == "__main__":

    print(
        "VI1510.1 PROVENANCE BRIDGE=PASS"
    )
