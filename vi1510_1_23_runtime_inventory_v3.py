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
    save_json,
)


DENIED_KEYS = {
    "query",
    "queries",
    "search",
    "searches",
    "prompt",
    "topic_query",
    "asset_query",
    "keywords",
    "keyword",
}


def canonical_path(value):
    value = str(value or "").strip()

    if (
        not value
        or value.startswith("http://")
        or value.startswith("https://")
    ):
        return ""

    try:
        return str(
            Path(value)
            .expanduser()
            .resolve()
        )
    except Exception:
        return value


def canonical_url(value):
    value = str(value or "").strip()

    if not value:
        return ""

    try:
        parts = urlsplit(value)

        if parts.scheme.lower() not in {
            "http",
            "https",
        }:
            return ""

        query = [
            (key, item)
            for key, item in parse_qsl(
                parts.query,
                keep_blank_values=True,
            )
            if not key.lower().startswith("utm_")
        ]

        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                unquote(parts.path),
                urlencode(
                    query,
                    doseq=True,
                ),
                "",
            )
        ).rstrip("/")

    except Exception:
        return ""


def first(value, keys):
    if not isinstance(value, dict):
        return ""

    for key in keys:
        item = value.get(key)

        if item not in [
            None,
            "",
        ]:
            return item

    return ""


def direct_identity(value):
    if not isinstance(value, dict):
        return {}

    return {
        "sha256":
            str(
                first(
                    value,
                    [
                        "sha256",
                        "file_sha256",
                    ],
                )
                or ""
            ).strip().lower(),

        "source_group":
            str(
                first(
                    value,
                    [
                        "source_group",
                    ],
                )
                or ""
            ).strip(),

        "source_url":
            str(
                first(
                    value,
                    [
                        "source_url",
                        "remote_url",
                        "media_url",
                        "original_url",
                        "download_url",
                        "final_url",
                        "descriptionurl",
                        "url",
                        "source",
                    ],
                )
                or ""
            ).strip(),

        "title":
            str(
                first(
                    value,
                    [
                        "title",
                        "name",
                        "ObjectName",
                        "filename",
                    ],
                )
                or ""
            ).strip(),

        "provider":
            str(
                first(
                    value,
                    [
                        "provider",
                    ],
                )
                or ""
            ).strip(),

        "license":
            str(
                first(
                    value,
                    [
                        "license",
                        "LicenseShortName",
                        "license_short_name",
                    ],
                )
                or ""
            ).strip(),

        "local_path":
            str(
                first(
                    value,
                    [
                        "local_path",
                        "source_path",
                        "downloaded_path",
                        "path",
                        "asset",
                    ],
                )
                or ""
            ).strip(),
    }


def identity_score(identity):
    score = 0

    if re.fullmatch(
        r"[0-9a-f]{64}",
        identity.get("sha256", ""),
    ):
        score += 500

    if norm(
        identity.get("source_group")
        or ""
    ):
        score += 400

    if canonical_url(
        identity.get("source_url")
    ):
        score += 400

    if canonical_path(
        identity.get("local_path")
    ):
        score += 120

    if len(
        norm(
            identity.get("title")
            or ""
        )
    ) >= 8:
        score += 100

    if identity.get("provider"):
        score += 30

    if identity.get("license"):
        score += 30

    return score


def identity_key(identity):
    return (
        str(
            identity.get("sha256")
            or ""
        ).lower(),

        norm(
            identity.get("source_group")
            or ""
        ),

        canonical_url(
            identity.get("source_url")
        ),

        norm(
            identity.get("title")
            or ""
        ),

        canonical_path(
            identity.get("local_path")
        ),
    )


def walk_dicts(value):
    if isinstance(value, dict):
        yield value

        for key, item in value.items():
            if str(key).lower() in DENIED_KEYS:
                continue

            yield from walk_dicts(item)

    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def best_identity(value):
    candidates = []

    for index, item in enumerate(
        walk_dicts(value)
    ):
        identity = direct_identity(item)
        score = identity_score(identity)

        if score <= 0:
            continue

        candidates.append({
            "identity":
                identity,

            "score":
                score,

            "depth_order":
                index,
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item:
            (
                item["score"],
                -item["depth_order"],
            ),
        reverse=True,
    )

    best = candidates[0]

    if len(candidates) > 1:
        second = candidates[1]

        if (
            second["score"]
            ==
            best["score"]

            and

            identity_key(
                second["identity"]
            )
            !=
            identity_key(
                best["identity"]
            )
        ):
            return None

    return best["identity"]


def selector_values(value):
    if not isinstance(value, dict):
        return set()

    result = set()

    for key in [
        "short_id",
        "topic",
        "topic_id",
        "benchmark",
        "benchmark_id",
        "name",
        "id",
    ]:
        item = value.get(key)

        if item not in [
            None,
            "",
        ]:
            result.add(
                norm(str(item))
            )

    return {
        item
        for item in result
        if item
    }


def scope_matches_run(scopes, run):
    wanted = selector_values(run)

    if not wanted:
        return False

    available = set()

    for scope in scopes:
        available.update(
            selector_values(scope)
        )

    return bool(
        wanted
        &
        available
    )


def looks_like_asset_record(
    value,
):
    """
    Generic structural asset detection.

    No topic/query text is evidence here.
    This only decides whether a dictionary looks like
    an asset/inventory record.
    """

    if not isinstance(
        value,
        dict
    ):
        return False


    keys = {
        str(
            key
        ).lower()

        for key in value.keys()
    }


    denied_only = {
        "query",
        "queries",
        "search",
        "searches",
        "prompt",
        "keywords",
        "keyword",
        "asset_query",
    }


    useful_keys = (
        keys
        -
        denied_only
    )


    if useful_keys & {
        "sha256",
        "file_sha256",
        "source_group",
        "source_url",
        "remote_url",
        "media_url",
        "original_url",
        "download_url",
        "final_url",
        "local_path",
        "source_path",
        "downloaded_path",
        "prepared_asset",
        "selected_asset",
        "selected_source",
    }:

        return True


    for key in useful_keys:

        if any(
            token in key

            for token in [
                "asset",
                "path",
                "image",
                "imagem",
                "video",
                "media",
                "file",
            ]
        ):

            return True


    return False


def find_inventory_lists(
    value,
    *,
    run,
    root_label,
    base_priority,
    require_scope_match,
    ancestry=None,
):
    """
    V3.1

    Discover asset inventories regardless of their
    container key:

        source_assets
        selected_assets
        assets
        media_assets
        visual_assets
        downloaded_assets
        downloads
        inventory
        etc.

    A discovered inventory is still NOT lineage.

    Later stages require exact path/SHA or another
    independent source identity.
    """

    if ancestry is None:
        ancestry = []


    found = []


    if isinstance(
        value,
        dict
    ):

        scopes = (
            ancestry
            +
            [
                value
            ]
        )


        for key, item in value.items():

            key_text = str(
                key
            ).lower()


            if key_text in DENIED_KEYS:
                continue


            if isinstance(
                item,
                list
            ) and item:

                dictionary_items = [
                    row

                    for row in item

                    if isinstance(
                        row,
                        dict
                    )
                ]


                asset_items = [
                    row

                    for row in dictionary_items

                    if looks_like_asset_record(
                        row
                    )
                ]


                if asset_items:

                    matched_scope = (
                        scope_matches_run(
                            scopes,
                            run,
                        )
                    )


                    if (
                        not require_scope_match
                        or
                        matched_scope
                    ):

                        key_bonus = {
                            "source_assets":
                                140,

                            "selected_assets":
                                130,

                            "assets":
                                120,

                            "media_assets":
                                115,

                            "visual_assets":
                                115,

                            "downloaded_assets":
                                110,

                            "downloads":
                                100,

                            "inventory":
                                90,

                            "media":
                                80,

                            "images":
                                80,

                            "videos":
                                80,
                        }.get(
                            key_text,
                            50,
                        )


                        found.append({
                            "assets":
                                asset_items,

                            "priority":
                                base_priority
                                +
                                key_bonus
                                +
                                (
                                    250
                                    if matched_scope
                                    else 0
                                ),

                            "root":
                                (
                                    root_label
                                    +
                                    ":"
                                    +
                                    key_text
                                ),
                        })


            found.extend(
                find_inventory_lists(
                    item,
                    run=run,
                    root_label=root_label,
                    base_priority=base_priority,
                    require_scope_match=require_scope_match,
                    ancestry=scopes,
                )
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            found.extend(
                find_inventory_lists(
                    item,
                    run=run,
                    root_label=root_label,
                    base_priority=base_priority,
                    require_scope_match=require_scope_match,
                    ancestry=ancestry,
                )
            )


    return found


def recover_inventory(
    *,
    run,
    partition=None,
    resolved=None,
    fallback_inventory=None,
):
    pools = []

    roots = []

    if isinstance(
        fallback_inventory,
        dict
    ) and fallback_inventory:
        roots.append(
            (
                "fallback_inventory",
                fallback_inventory,
                700,
                False,
            )
        )

    if isinstance(run, dict):
        roots.append(
            (
                "run",
                run,
                600,
                False,
            )
        )

    if (
        isinstance(partition, dict)
        and partition is not run
    ):
        roots.append(
            (
                "partition",
                partition,
                600,
                False,
            )
        )

    if resolved is not None:
        roots.append(
            (
                "resolved",
                resolved,
                200,
                True,
            )
        )

    for (
        label,
        root,
        priority,
        require_match,
    ) in roots:

        pools.extend(
            find_inventory_lists(
                root,
                run=run,
                root_label=label,
                base_priority=priority,
                require_scope_match=require_match,
            )
        )

    recovered = []
    seen = set()

    for pool in sorted(
        pools,
        key=lambda item:
            item["priority"],
        reverse=True,
    ):
        for source_asset in pool["assets"]:

            if not isinstance(
                source_asset,
                dict
            ):
                continue

            identity = best_identity(
                source_asset
            )

            paths = collect_paths(
                source_asset
            )

            hashes = collect_hashes(
                source_asset
            )

            key = (
                tuple(
                    sorted(paths)
                ),
                tuple(
                    sorted(hashes)
                ),
                identity_key(
                    identity
                    or {}
                ),
            )

            if key in seen:
                continue

            seen.add(key)

            recovered.append({
                "asset":
                    source_asset,

                "identity":
                    identity,

                "paths":
                    paths,

                "hashes":
                    hashes,

                "priority":
                    pool["priority"],

                "root":
                    pool["root"],
            })

    return recovered


def collect_paths(value):
    paths = set()

    for item in walk_dicts(value):
        for key, raw in item.items():

            if not isinstance(raw, str):
                continue

            key_text = str(key).lower()

            if not any(
                word in key_text
                for word in [
                    "path",
                    "asset",
                    "media",
                    "image",
                    "imagem",
                    "video",
                    "file",
                    "input",
                ]
            ):
                continue

            path = canonical_path(raw)

            if path:
                paths.add(path)

    return paths


def collect_hashes(value):
    hashes = set()

    for item in walk_dicts(value):
        for key in [
            "sha256",
            "file_sha256",
        ]:
            digest = str(
                item.get(key)
                or ""
            ).strip().lower()

            if re.fullmatch(
                r"[0-9a-f]{64}",
                digest,
            ):
                hashes.add(digest)

    return hashes


def row_inventory_score(
    row,
    candidate,
):
    score = 0
    reasons = []

    row_path = canonical_path(
        row.get("path")
    )

    row_sha = str(
        row.get("sha256")
        or ""
    ).strip().lower()

    if (
        row_sha
        and
        row_sha in candidate["hashes"]
    ):
        score += 1000
        reasons.append(
            "runtime_inventory_sha256_exact"
        )

    if (
        row_path
        and
        row_path in candidate["paths"]
    ):
        score += 900
        reasons.append(
            "runtime_inventory_path_exact"
        )

    row_group = norm(
        row.get("source_group")
        or ""
    )

    identity = (
        candidate.get("identity")
        or {}
    )

    candidate_group = norm(
        identity.get("source_group")
        or ""
    )

    if (
        row_group
        and
        candidate_group
        and
        row_group == candidate_group
    ):
        score += 500
        reasons.append(
            "runtime_inventory_source_group_exact"
        )

    row_url = canonical_url(
        row.get("source_url")
    )

    candidate_url = canonical_url(
        identity.get("source_url")
    )

    if (
        row_url
        and
        candidate_url
        and
        row_url == candidate_url
    ):
        score += 500
        reasons.append(
            "runtime_inventory_url_exact"
        )

    return (
        score,
        reasons,
    )


def enrich_scene_usage(
    report,
    *,
    run,
    run_dir,
    partition=None,
    resolved=None,
    fallback_inventory=None,
):
    inventory = recover_inventory(
        run=run,
        partition=partition,
        resolved=resolved,
        fallback_inventory=fallback_inventory,
    )

    output = []

    linked = 0
    transported = 0
    ambiguous = 0

    for original in (
        report.get("used_assets")
        or []
    ):
        row = dict(original)

        matches = []

        for index, candidate in enumerate(
            inventory
        ):
            score, reasons = (
                row_inventory_score(
                    row,
                    candidate,
                )
            )

            if score <= 0:
                continue

            matches.append({
                "index":
                    index,

                "score":
                    score,

                "reasons":
                    reasons,

                "candidate":
                    candidate,
            })

        matches.sort(
            key=lambda item:
                (
                    item["score"],
                    item["candidate"]["priority"],
                ),
            reverse=True,
        )

        selected = None

        if matches:
            if (
                len(matches) == 1
                or
                matches[0]["score"]
                >
                matches[1]["score"]
                or
                identity_key(
                    matches[0]["candidate"].get(
                        "identity"
                    )
                    or {}
                )
                ==
                identity_key(
                    matches[1]["candidate"].get(
                        "identity"
                    )
                    or {}
                )
            ):
                selected = matches[0]
            else:
                ambiguous += 1

        if selected is not None:
            candidate = selected["candidate"]

            identity = (
                candidate.get("identity")
                or {}
            )

            linked += 1

            if identity:
                mapping = {
                    "source_group":
                        "source_group",

                    "source_url":
                        "source_url",

                    "title":
                        "title",

                    "provider":
                        "provider",

                    "license":
                        "license",
                }

                copied = 0

                for source_key, row_key in (
                    mapping.items()
                ):
                    value = identity.get(
                        source_key
                    )

                    if (
                        value not in [
                            None,
                            "",
                        ]
                        and
                        not row.get(row_key)
                    ):
                        row[row_key] = value
                        copied += 1

                source_sha = identity.get(
                    "sha256"
                )

                if source_sha:
                    row[
                        "source_sha256"
                    ] = source_sha
                    copied += 1

                source_path = identity.get(
                    "local_path"
                )

                if source_path:
                    row[
                        "source_local_path"
                    ] = source_path
                    copied += 1

                if copied:
                    transported += 1

            row[
                "runtime_inventory_v3"
            ] = {
                "matched":
                    True,

                "score":
                    selected["score"],

                "reasons":
                    selected["reasons"],

                "inventory_root":
                    candidate["root"],

                "provenance_transported":
                    bool(identity),

                "scene_only_used_as_evidence":
                    False,
            }

        else:
            row[
                "runtime_inventory_v3"
            ] = {
                "matched":
                    False,

                "scene_only_used_as_evidence":
                    False,
            }

        output.append(row)

    enriched = dict(report)

    enriched[
        "used_assets"
    ] = output

    enriched[
        "runtime_inventory_v3"
    ] = {
        "inventory_assets":
            len(inventory),

        "used_assets":
            len(output),

        "matched_assets":
            linked,

        "provenance_transported_assets":
            transported,

        "ambiguous_assets":
            ambiguous,

        "scene_only_used_as_evidence":
            False,

        "query_used_as_evidence":
            False,
    }

    save_json(
        Path(run_dir)
        / "runtime_inventory_v3.json",
        enriched[
            "runtime_inventory_v3"
        ],
    )

    save_json(
        Path(run_dir)
        / "scene_usage.json",
        enriched,
    )

    return enriched


def inventory_metadata_records(
    *,
    run,
    partition=None,
    resolved=None,
    fallback_inventory=None,
):
    inventory = recover_inventory(
        run=run,
        partition=partition,
        resolved=resolved,
        fallback_inventory=fallback_inventory,
    )

    records = []

    for item in inventory:
        identity = (
            item.get("identity")
            or {}
        )

        if not identity:
            continue

        source_asset = item["asset"]

        scene = (
            source_asset.get("scene")
            or
            source_asset.get("scene_id")
        )

        evidence_parts = [
            identity.get("title"),
            identity.get("source_group"),
            identity.get("source_url"),
            identity.get("provider"),
            identity.get("license"),
        ]

        records.append({
            "provider":
                identity.get("provider")
                or "",

            "title":
                identity.get("title")
                or "",

            "license":
                identity.get("license")
                or "",

            "artist":
                "",

            "source_group":
                identity.get("source_group")
                or "",

            "source_url":
                identity.get("source_url")
                or "",

            "local_path":
                identity.get("local_path")
                or "",

            "sha256":
                identity.get("sha256")
                or "",

            "scene":
                scene,

            "evidence_text":
                " | ".join(
                    str(value)
                    for value in evidence_parts
                    if value
                ),

            "query_used_as_evidence":
                False,

            "origin":
                (
                    "runtime_inventory_v3:"
                    + item["root"]
                ),
        })

    return records


if __name__ == "__main__":
    print(
        "VI1510.1 V3 RUNTIME INVENTORY MODULE=PASS"
    )

# ======================================================
# VI1510.1 V3.1 COMPACT GENERIC INVENTORY DISCOVERY
# ======================================================

def find_inventory_lists(
    value,
    *,
    run,
    root_label,
    base_priority,
    require_scope_match,
    ancestry=None,
):
    if ancestry is None:
        ancestry = []

    found = []

    if isinstance(value, dict):

        scopes = ancestry + [value]

        for key, item in value.items():

            key_text = str(key).lower()

            if key_text in DENIED_KEYS:
                continue

            if isinstance(item, list) and item:

                assets = []

                for row in item:

                    if not isinstance(row, dict):
                        continue

                    keys = {
                        str(k).lower()
                        for k in row.keys()
                    }

                    useful = keys - DENIED_KEYS

                    if (
                        useful
                        &
                        {
                            "sha256",
                            "file_sha256",
                            "source_group",
                            "source_url",
                            "remote_url",
                            "media_url",
                            "original_url",
                            "local_path",
                            "source_path",
                            "downloaded_path",
                            "prepared_asset",
                            "selected_asset",
                            "selected_source",
                        }
                    ):
                        assets.append(row)
                        continue

                    if any(
                        any(
                            token in k
                            for token in [
                                "asset",
                                "path",
                                "image",
                                "imagem",
                                "video",
                                "media",
                                "file",
                            ]
                        )
                        for k in useful
                    ):
                        assets.append(row)

                if assets:

                    matched = scope_matches_run(
                        scopes,
                        run,
                    )

                    if (
                        not require_scope_match
                        or matched
                    ):

                        bonus = {
                            "source_assets": 140,
                            "selected_assets": 130,
                            "assets": 120,
                            "media_assets": 115,
                            "visual_assets": 115,
                            "downloaded_assets": 110,
                            "downloads": 100,
                            "inventory": 90,
                            "media": 80,
                            "images": 80,
                            "videos": 80,
                        }.get(
                            key_text,
                            50,
                        )

                        found.append({
                            "assets": assets,

                            "priority":
                                base_priority
                                + bonus
                                + (
                                    250
                                    if matched
                                    else 0
                                ),

                            "root":
                                root_label
                                + ":"
                                + key_text,
                        })

            found.extend(
                find_inventory_lists(
                    item,
                    run=run,
                    root_label=root_label,
                    base_priority=base_priority,
                    require_scope_match=require_scope_match,
                    ancestry=scopes,
                )
            )

    elif isinstance(value, list):

        for item in value:

            found.extend(
                find_inventory_lists(
                    item,
                    run=run,
                    root_label=root_label,
                    base_priority=base_priority,
                    require_scope_match=require_scope_match,
                    ancestry=ancestry,
                )
            )

    return found


# ======================================================
# VI1510.1 V4 LIST-AWARE PATH/HASH BRIDGE
# ======================================================

def collect_paths(value):
    """
    Collect path identity from scalar fields AND list fields
    such as V4's `paths`.
    """

    result = set()

    def visit(item, key_hint=""):

        if isinstance(item, dict):

            for key, child in item.items():

                key_text = str(key).lower()

                if key_text in DENIED_KEYS:
                    continue

                visit(
                    child,
                    key_text,
                )

        elif isinstance(item, list):

            for child in item:
                visit(
                    child,
                    key_hint,
                )

        elif isinstance(item, str):

            if not any(
                token in key_hint

                for token in [
                    "path",
                    "paths",
                    "asset",
                    "media",
                    "image",
                    "imagem",
                    "video",
                    "file",
                    "input",
                ]
            ):
                return

            path = canonical_path(item)

            if path:
                result.add(path)

    visit(value)

    return result


def collect_hashes(value):
    """
    Collect SHA256 from scalar and list representations.
    """

    result = set()

    def visit(item, key_hint=""):

        if isinstance(item, dict):

            for key, child in item.items():

                key_text = str(key).lower()

                if key_text in DENIED_KEYS:
                    continue

                visit(
                    child,
                    key_text,
                )

        elif isinstance(item, list):

            for child in item:
                visit(
                    child,
                    key_hint,
                )

        elif isinstance(item, str):

            if key_hint not in {
                "sha256",
                "file_sha256",
                "hash",
                "hashes",
            }:
                return

            digest = item.strip().lower()

            if re.fullmatch(
                r"[0-9a-f]{64}",
                digest,
            ):
                result.add(digest)

    visit(value)

    return result

