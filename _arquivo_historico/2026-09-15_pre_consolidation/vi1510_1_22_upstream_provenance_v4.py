#!/usr/bin/env python3

import json
import re

from pathlib import Path

from vi1510_01_common import (
    BASE,
    norm,
)


DENIED = {
    "query",
    "queries",
    "search",
    "searches",
    "prompt",
    "keywords",
    "keyword",
    "asset_query",
    "topic_query",
}


PATH_WORDS = {
    "path",
    "asset",
    "image",
    "imagem",
    "media",
    "video",
    "file",
    "input",
}


def canonical_path(value):
    value = str(
        value
        or ""
    ).strip()

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


def direct_paths(value):
    result = set()

    if not isinstance(
        value,
        dict
    ):
        return result

    for key, item in value.items():

        if not isinstance(
            item,
            str
        ):
            continue

        key_text = str(
            key
        ).lower()

        if not any(
            word in key_text
            for word in PATH_WORDS
        ):
            continue

        path = canonical_path(
            item
        )

        if path:
            result.add(path)

    return result


def direct_hashes(value):
    result = set()

    if not isinstance(
        value,
        dict
    ):
        return result

    for key in [
        "sha256",
        "file_sha256",
    ]:
        digest = str(
            value.get(key)
            or ""
        ).strip().lower()

        if re.fullmatch(
            r"[0-9a-f]{64}",
            digest,
        ):
            result.add(digest)

    return result


def first(value, keys):
    if not isinstance(
        value,
        dict
    ):
        return ""

    for key in keys:
        item = value.get(key)

        if item not in [
            None,
            "",
        ]:
            return item

    return ""


def identity(value):
    if not isinstance(
        value,
        dict
    ):
        return {}

    return {
        "source_group":
            str(
                first(
                    value,
                    ["source_group"],
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
                    ["provider"],
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
                    ],
                )
                or ""
            ).strip(),

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
    }


def strong_identity(item):
    return bool(
        item.get("source_group")
        or
        item.get("source_url")
        or
        (
            re.fullmatch(
                r"[0-9a-f]{64}",
                item.get("sha256", ""),
            )
            and
            (
                item.get("provider")
                or
                item.get("license")
                or
                item.get("title")
            )
        )
    )


def nested_identities(value, depth=0):
    if depth > 5:
        return []

    found = []

    if isinstance(
        value,
        dict
    ):

        item = identity(
            value
        )

        if strong_identity(
            item
        ):
            found.append(
                item
            )

        for key, child in value.items():

            if str(
                key
            ).lower() in DENIED:
                continue

            found.extend(
                nested_identities(
                    child,
                    depth + 1,
                )
            )

    elif isinstance(
        value,
        list
    ):

        for child in value:
            found.extend(
                nested_identities(
                    child,
                    depth + 1,
                )
            )

    dedup = {}

    for item in found:

        key = (
            norm(
                item.get(
                    "source_group"
                )
                or ""
            ),
            str(
                item.get(
                    "source_url"
                )
                or ""
            ).lower(),
            str(
                item.get(
                    "sha256"
                )
                or ""
            ).lower(),
            norm(
                item.get(
                    "title"
                )
                or ""
            ),
        )

        dedup[
            key
        ] = item

    return list(
        dedup.values()
    )


def walk_dicts(value):
    if isinstance(
        value,
        dict
    ):

        yield value

        for key, child in value.items():

            if str(
                key
            ).lower() in DENIED:
                continue

            yield from walk_dicts(
                child
            )

    elif isinstance(
        value,
        list
    ):

        for child in value:
            yield from walk_dicts(
                child
            )


def extract_candidates(data, origin):
    result = []

    for node in walk_dicts(
        data
    ):

        paths = direct_paths(
            node
        )

        hashes = direct_hashes(
            node
        )

        if (
            not paths
            and
            not hashes
        ):
            continue

        identities = nested_identities(
            node
        )

        if len(
            identities
        ) != 1:
            continue

        source = identities[
            0
        ]

        if not strong_identity(
            source
        ):
            continue

        result.append({
            "scene":
                node.get(
                    "scene"
                )
                or
                node.get(
                    "scene_id"
                ),

            "paths":
                sorted(paths),

            "hashes":
                sorted(hashes),

            "selected_source":
                source,

            "origin":
                str(origin),

            "query_used_as_evidence":
                False,

            "scene_only_used_as_evidence":
                False,
        })

    return result


def in_window(path, start, end):
    try:
        mtime = path.stat().st_mtime

        return (
            start
            <=
            mtime
            <=
            end
        )

    except Exception:
        return False


def collect_source_assets(
    run,
    roots=None,
):
    start = float(
        run[
            "window_start"
        ]
    )

    end = float(
        run[
            "window_end"
        ]
    )

    short_id = str(
        run.get(
            "short_id"
        )
        or ""
    )

    if roots is None:
        roots = [
            BASE / "roteiros",
            BASE / "manifests",
            BASE / "temp",
            BASE / "logs",
        ]

    candidates = []

    for root in roots:

        root = Path(
            root
        )

        if not root.exists():
            continue

        for path in root.rglob(
            "*.json"
        ):

            lower = str(
                path
            ).lower()

            if any(
                marker in lower

                for marker in [
                    "/vi1400/",
                    "/vi1500/",
                    "/vi1510/",
                ]
            ):
                continue

            sid_match = bool(
                short_id
                and
                short_id in str(path)
            )

            if not (
                sid_match
                or
                in_window(
                    path,
                    start,
                    end,
                )
            ):
                continue

            try:
                data = json.loads(
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                )
            except Exception:
                continue

            candidates.extend(
                extract_candidates(
                    data,
                    path,
                )
            )

    dedup = {}

    for item in candidates:

        source = item[
            "selected_source"
        ]

        key = (
            tuple(
                item[
                    "paths"
                ]
            ),
            tuple(
                item[
                    "hashes"
                ]
            ),
            norm(
                source.get(
                    "source_group"
                )
                or ""
            ),
            str(
                source.get(
                    "source_url"
                )
                or ""
            ).lower(),
        )

        dedup[
            key
        ] = item

    return list(
        dedup.values()
    )


def attach_source_assets(
    rows,
):
    output = []

    for original in rows:

        row = dict(
            original
        )

        assets = collect_source_assets(
            row
        )

        row[
            "source_assets"
        ] = assets

        row[
            "upstream_provenance_v4"
        ] = {
            "source_assets":
                len(
                    assets
                ),

            "query_used_as_evidence":
                False,

            "scene_only_used_as_evidence":
                False,
        }

        output.append(
            row
        )

    return output


if __name__ == "__main__":
    print(
        "VI1510.1 V4 UPSTREAM PROVENANCE MODULE=PASS"
    )

# ======================================================
# VI1510.1 V4 STRICT ASSET-BINDING OVERRIDE
# ======================================================

def _vi1510_v4_binding_paths(value):
    """
    Paths that identify the asset used/prepared by a scene.

    local_path/source_path belong to source provenance and
    cannot, by themselves, create an asset->source binding.
    """

    result = set()

    if not isinstance(value, dict):
        return result

    denied = {
        "local_path",
        "source_path",
        "original_path",
        "source_file",
        "original_file",
    }

    for key, item in value.items():

        if not isinstance(item, str):
            continue

        key_text = str(key).lower()

        if key_text in denied:
            continue

        valid = (
            key_text in {
                "path",
                "asset",
                "asset_path",
                "prepared_asset",
                "prepared_path",
                "selected_asset",
                "selected_asset_path",
                "downloaded_path",
                "image",
                "image_path",
                "imagem",
                "media",
                "media_path",
                "video",
                "video_path",
                "file",
                "file_path",
                "input",
                "input_path",
            }
            or
            (
                any(
                    token in key_text
                    for token in [
                        "prepared_asset",
                        "selected_asset",
                        "asset_path",
                        "media_path",
                        "image_path",
                        "video_path",
                    ]
                )
            )
        )

        if not valid:
            continue

        path = canonical_path(item)

        if path:
            result.add(path)

    return result


def extract_candidates(data, origin):
    """
    V4 strict extraction.

    A provenance record is emitted only when one structural
    object contains:

      asset-side path
          +
      exactly one independent source identity in its subtree.

    A selected_source.local_path alone is NOT an asset binding.
    """

    result = []

    for node in walk_dicts(data):

        paths = _vi1510_v4_binding_paths(
            node
        )

        if not paths:
            continue

        hashes = direct_hashes(
            node
        )

        identities = nested_identities(
            node
        )

        if len(identities) != 1:
            continue

        source = identities[0]

        if not strong_identity(source):
            continue

        result.append({
            "scene":
                node.get("scene")
                or
                node.get("scene_id"),

            "paths":
                sorted(paths),

            "hashes":
                sorted(hashes),

            "selected_source":
                source,

            "origin":
                str(origin),

            "binding_method":
                "structural_asset_path_plus_unique_source",

            "query_used_as_evidence":
                False,

            "scene_only_used_as_evidence":
                False,
        })

    return result

