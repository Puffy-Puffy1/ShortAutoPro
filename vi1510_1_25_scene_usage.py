#!/usr/bin/env python3

import json
import re

from pathlib import Path

from vi1510_01_common import (
    ROOT,
    in_window,
    norm,
    save_json,
    sha256_file,
)


MEDIA_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".webm",
    ".mp4",
    ".pdf",
}


ASSET_KEYS = {
    "asset",
    "image",
    "imagem",
    "media",
    "media_path",
    "image_path",
    "video_path",
    "local_path",
    "selected_asset",
    "selected_media",
    "source_path",
}


def resolve_local_path(
    value,
):
    if not isinstance(
        value,
        str
    ):
        return None


    value = value.strip()


    if not value:
        return None


    candidates = [
        Path(
            value
        ).expanduser(),

        ROOT
        / value,
    ]


    for path in candidates:

        try:

            if (
                path.exists()

                and

                path.is_file()

                and

                path.suffix.lower()
                in MEDIA_SUFFIXES
            ):

                return path.resolve()


        except Exception:
            pass


    return None


def scene_number(
    scene,
    fallback,
):
    for key in [
        "scene",
        "scene_id",
        "id",
        "number",
        "index",
    ]:

        value = scene.get(
            key
        )


        try:

            number = int(
                value
            )


            if (
                1
                <= number
                <= 30
            ):

                return number


        except Exception:
            pass


    return fallback



# VI1510.1 V2.6 SCENE PROVENANCE CAPTURE

def _vi1510_v26_canonical_path(
    value,
):
    value = str(
        value
        or ""
    ).strip()

    if (
        not value
        or
        value.startswith(
            (
                "http://",
                "https://",
            )
        )
    ):
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
        return value


def _vi1510_v26_identity(
    value,
):
    if not isinstance(
        value,
        dict
    ):
        return {}


    def first(
        keys,
    ):
        for key in keys:

            item = value.get(
                key
            )

            if item not in [
                None,
                "",
            ]:
                return item

        return ""


    source_url = first([
        "source_url",
        "remote_url",
        "media_url",
        "original_url",
        "download_url",
        "final_url",
        "descriptionurl",
        "url",
        "source",
    ])


    local_path = first([
        "local_path",
        "source_path",
        "downloaded_path",
        "path",
        "asset",
    ])


    return {
        "source_group":
            str(
                first([
                    "source_group",
                ])
                or ""
            ).strip(),

        "source_url":
            str(
                source_url
                or ""
            ).strip(),

        "title":
            str(
                first([
                    "title",
                    "name",
                    "ObjectName",
                    "filename",
                ])
                or ""
            ).strip(),

        "provider":
            str(
                first([
                    "provider",
                ])
                or ""
            ).strip(),

        "license":
            str(
                first([
                    "license",
                    "LicenseShortName",
                    "license_short_name",
                ])
                or ""
            ).strip(),

        "source_sha256":
            str(
                first([
                    "sha256",
                    "file_sha256",
                ])
                or ""
            ).strip().lower(),

        "source_local_path":
            str(
                local_path
                or ""
            ).strip(),
    }


def _vi1510_v26_strong_identity(
    identity,
):
    title = norm(
        identity.get(
            "title"
        )
        or ""
    )

    return bool(
        identity.get(
            "source_group"
        )

        or

        identity.get(
            "source_url"
        )

        or

        (
            len(
                identity.get(
                    "source_sha256"
                )
                or ""
            )
            ==
            64
        )

        or

        (
            len(
                title
            )
            >=
            8

            and

            (
                identity.get(
                    "provider"
                )
                or
                identity.get(
                    "license"
                )
                or
                identity.get(
                    "source_local_path"
                )
            )
        )
    )


def _vi1510_v26_identity_key(
    identity,
):
    return (
        str(
            identity.get(
                "source_sha256"
            )
            or ""
        ).lower(),

        norm(
            identity.get(
                "source_group"
            )
            or ""
        ),

        str(
            identity.get(
                "source_url"
            )
            or ""
        ).strip().lower(),

        norm(
            identity.get(
                "title"
            )
            or ""
        ),

        _vi1510_v26_canonical_path(
            identity.get(
                "source_local_path"
            )
        ),
    )


def _vi1510_v26_walk(
    value,
    depth=0,
):
    if depth > 7:
        return

    if isinstance(
        value,
        dict
    ):

        yield (
            value,
            depth,
        )

        for key, item in value.items():

            key_text = str(
                key
            ).lower()

            if any(
                denied
                in key_text

                for denied in [
                    "query",
                    "search",
                    "prompt",
                    "topic",
                    "keyword",
                    "narration",
                    "segment",
                    "script",
                    "roteiro",
                ]
            ):
                continue

            yield from _vi1510_v26_walk(
                item,
                depth + 1,
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            yield from _vi1510_v26_walk(
                item,
                depth + 1,
            )


def _vi1510_v26_dict_has_asset(
    value,
    asset_path,
):
    if not isinstance(
        value,
        dict
    ):
        return False


    wanted = (
        _vi1510_v26_canonical_path(
            asset_path
        )
    )


    if not wanted:
        return False


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
            word
            in key_text

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


        candidate = (
            _vi1510_v26_canonical_path(
                item
            )
        )


        if (
            candidate
            and
            candidate
            ==
            wanted
        ):
            return True


    return False


def _vi1510_v26_scene_provenance(
    scene,
    asset_path,
):
    """
    Capture provenance while the collector still has
    direct access to the full scene object.

    Safe strategies:
      1. source identity in the same dict as asset path;
      2. exactly one independent source identity inside
         the scene subtree.

    Scene number alone is never evidence.
    Query/search/topic text is never evidence.
    """

    candidates = []


    for value, depth in (
        _vi1510_v26_walk(
            scene
        )
    ):

        identity = (
            _vi1510_v26_identity(
                value
            )
        )


        if not _vi1510_v26_strong_identity(
            identity
        ):
            continue


        path_match = (
            _vi1510_v26_dict_has_asset(
                value,
                asset_path,
            )
        )


        score = (
            1000
            if path_match
            else 0
        )


        if identity.get(
            "source_sha256"
        ):
            score += 400


        if identity.get(
            "source_url"
        ):
            score += 350


        if identity.get(
            "source_group"
        ):
            score += 300


        if identity.get(
            "title"
        ):
            score += 100


        if identity.get(
            "provider"
        ):
            score += 50


        if identity.get(
            "license"
        ):
            score += 50


        score -= (
            depth
            * 10
        )


        candidates.append({
            "identity":
                identity,

            "score":
                score,

            "path_match":
                path_match,
        })


    dedup = {}


    for candidate in candidates:

        key = _vi1510_v26_identity_key(
            candidate[
                "identity"
            ]
        )


        if not any(
            key
        ):
            continue


        previous = dedup.get(
            key
        )


        if (
            previous is None
            or
            candidate[
                "score"
            ]
            >
            previous[
                "score"
            ]
        ):

            dedup[
                key
            ] = candidate


    candidates = sorted(
        dedup.values(),
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    )


    direct = [
        item

        for item in candidates

        if item[
            "path_match"
        ]
    ]


    selected = None

    method = None


    if len(
        direct
    ) == 1:

        selected = direct[
            0
        ]

        method = (
            "same_dict_asset_source"
        )


    elif len(
        candidates
    ) == 1:

        selected = candidates[
            0
        ]

        method = (
            "unique_scene_source"
        )


    if selected is None:

        return {
            "scene_provenance": {
                "status":
                    (
                        "AMBIGUOUS"
                        if candidates
                        else "NOT_FOUND"
                    ),

                "candidate_count":
                    len(
                        candidates
                    ),

                "scene_only_used_as_evidence":
                    False,

                "query_used_as_evidence":
                    False,
            }
        }


    identity = selected[
        "identity"
    ]


    result = {
        "scene_provenance": {
            "status":
                "CAPTURED",

            "method":
                method,

            "score":
                selected[
                    "score"
                ],

            "scene_only_used_as_evidence":
                False,

            "query_used_as_evidence":
                False,
        }
    }


    for key in [
        "source_group",
        "source_url",
        "title",
        "provider",
        "license",
        "source_sha256",
        "source_local_path",
    ]:

        value = identity.get(
            key
        )


        if value not in [
            None,
            "",
        ]:

            result[
                key
            ] = value


    return result


def extract_scene_sets(
    value,
    origin,
):
    found = []


    if isinstance(
        value,
        dict
    ):

        scenes = value.get(
            "scenes"
        )


        if isinstance(
            scenes,
            list
        ):

            rows = []


            for index, scene in enumerate(
                scenes,
                1
            ):

                if not isinstance(
                    scene,
                    dict
                ):
                    continue


                paths = []


                for key in ASSET_KEYS:

                    path = resolve_local_path(
                        scene.get(
                            key
                        )
                    )


                    if path:

                        paths.append(
                            path
                        )


                if not paths:

                    for key, item in scene.items():

                        key_text = str(
                            key
                        ).lower()


                        if not any(
                            word
                            in key_text

                            for word in [
                                "asset",
                                "media",
                                "image",
                                "imagem",
                            ]
                        ):
                            continue


                        path = resolve_local_path(
                            item
                        )


                        if path:

                            paths.append(
                                path
                            )


                for path in paths:

                    rows.append({
                        "scene":
                            scene_number(
                                scene,
                                index
                            ),

                        "path":
                            str(
                                path
                            ),

                        "origin":
                            str(
                                origin
                            ),

                        "narration":
                            str(
                                scene.get(
                                    "narration"
                                )
                                or
                                scene.get(
                                    "segment"
                                )
                                or
                                ""
                            ),
                    })

                    rows[-1].update(
                        _vi1510_v26_scene_provenance(
                            scene,
                            path,
                        )
                    )


            if rows:

                found.append(
                    rows
                )


        for item in value.values():

            found.extend(
                extract_scene_sets(
                    item,
                    origin
                )
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            found.extend(
                extract_scene_sets(
                    item,
                    origin
                )
            )


    return found


def topic_anchor_score(
    topic,
    file_text,
):
    tokens = {
        token

        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9]+",
            norm(
                topic
            )
        )

        if len(
            token
        ) >= 5
    }


    return sum(
        token
        in norm(
            file_text
        )

        for token
        in tokens
    )


def collect(
    run,
    fallback_inventory,
    run_dir,
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

    short_id = (
        run.get(
            "short_id"
        )
        or ""
    )


    candidates = []


    roots = [
        ROOT
        / "roteiros",

        ROOT
        / "manifests",

        ROOT
        / "temp",

        ROOT
        / "logs",
    ]


    for base in roots:

        if not base.exists():
            continue


        for path in base.rglob(
            "*.json"
        ):

            lower = str(
                path
            ).lower()


            if any(
                marker
                in lower

                for marker in [
                    "/vi1400/",
                    "/vi1500/",
                    "/vi1510/",
                ]
            ):
                continue


            sid_match = (
                bool(
                    short_id
                )

                and

                short_id
                in str(
                    path
                )
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

                raw_text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )


                data = json.loads(
                    raw_text
                )


            except Exception:
                continue


            for scene_set in extract_scene_sets(
                data,
                path
            ):

                hashes = {}


                for row in scene_set:

                    try:

                        digest = sha256_file(
                            row[
                                "path"
                            ]
                        )


                    except Exception:
                        continue


                    hashes[
                        digest
                    ] = row


                count = len(
                    hashes
                )


                if count == 0:
                    continue


                score = (
                    count
                    *
                    10
                )


                if (
                    5
                    <= count
                    <= 16
                ):

                    score += 35


                if sid_match:

                    score += 60


                score += (
                    topic_anchor_score(
                        run.get(
                            "topic"
                        ),
                        raw_text
                    )
                    *
                    12
                )


                candidates.append({
                    "origin":
                        str(
                            path
                        ),

                    "rows":
                        list(
                            hashes.values()
                        ),

                    "unique":
                        count,

                    "score":
                        score,
                })


    candidates.sort(
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    )


    if candidates:

        best = candidates[
            0
        ]


        mode = (
            "EXPLICIT_SCENE_USAGE"
        )


        rows = best[
            "rows"
        ]


        origin = best[
            "origin"
        ]


    else:

        mode = (
            "FALLBACK_WINDOW_INVENTORY"
        )


        origin = None


        rows = [
            {
                "scene":
                    item.get(
                        "scene"
                    ),

                "path":
                    item[
                        "path"
                    ],

                "origin":
                    None,

                "narration":
                    "",
            }

            for item
            in fallback_inventory.get(
                "source_assets",
                []
            )
        ]


    final_rows = []


    for row in rows:

        path = Path(
            row[
                "path"
            ]
        )


        try:

            final_rows.append({
                **row,

                "path":
                    str(
                        path.resolve()
                    ),

                "sha256":
                    sha256_file(
                        path
                    ),

                "bytes":
                    path.stat().st_size,

                "mtime":
                    path.stat().st_mtime,

                "suffix":
                    path.suffix.lower(),
            })


        except Exception:
            pass


    dedup = {}


    for row in final_rows:

        dedup[
            row[
                "sha256"
            ]
        ] = row


    final_rows = list(
        dedup.values()
    )


    report = {
        "mode":
            mode,

        "origin":
            origin,

        "used_assets":
            final_rows,

        "used_asset_count":
            len(
                final_rows
            ),

        "unique_used_assets":
            len({
                row[
                    "sha256"
                ]

                for row
                in final_rows
            }),

        "candidate_scene_sets":
            [
                {
                    "origin":
                        item[
                            "origin"
                        ],

                    "unique":
                        item[
                            "unique"
                        ],

                    "score":
                        item[
                            "score"
                        ],
                }

                for item
                in candidates[
                    :10
                ]
            ],
    }


    save_json(
        run_dir
        / "scene_usage.json",
        report
    )


    return report


# ======================================================
# VI1510.1 V2.1 COLLECT COMPATIBILITY WRAPPER
# ======================================================

_vi1510_1_v2_original_collect = collect


def collect(
    run,
    run_dir,
    fallback_inventory=None,
):
    """
    Compatibility wrapper for the V2 generalized
    dispatcher.

    fallback_inventory is optional because some
    partitions resolve their own inventory from the run.
    """

    if fallback_inventory is None:
        fallback_inventory = {}


    return _vi1510_1_v2_original_collect(
        run,
        fallback_inventory,
        run_dir,
    )


# ======================================================
# VI1510.1 V2.3 PROVENANCE BRIDGE WRAPPER
# ======================================================

from vi1510_1_25_provenance_bridge import (
    enrich_scene_usage as _vi1510_v23_enrich_scene_usage,
)


_vi1510_v23_previous_collect = collect


def collect(
    run,
    run_dir,
    fallback_inventory=None,
):
    """
    Preserve the previous scene-usage collector, then
    transport independently matched provenance identity
    into each used asset.
    """

    if fallback_inventory is None:
        fallback_inventory = {}


    report = _vi1510_v23_previous_collect(
        run,
        run_dir,
        fallback_inventory=fallback_inventory,
    )


    return _vi1510_v23_enrich_scene_usage(
        report,
        run,
        fallback_inventory,
    )


# ======================================================
# VI1510.1 V3 RUNTIME INVENTORY SCENE WRAPPER
# ======================================================

from vi1510_1_23_runtime_inventory_v3 import (
    enrich_scene_usage as _vi1510_v3_enrich_scene_usage,
)


_vi1510_v3_previous_scene_collect = collect


def collect(
    run,
    run_dir,
    fallback_inventory=None,
    resolved=None,
    partition=None,
):
    report = _vi1510_v3_previous_scene_collect(
        run,
        run_dir,
        fallback_inventory=fallback_inventory,
    )

    return _vi1510_v3_enrich_scene_usage(
        report,
        run=run,
        run_dir=run_dir,
        partition=partition,
        resolved=resolved,
        fallback_inventory=fallback_inventory,
    )
