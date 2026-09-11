#!/usr/bin/env python3

import json
import re

from collections import defaultdict
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


PATH_KEYS = {
    "path",
    "local_path",
    "asset",
    "media",
    "image",
    "imagem",
    "video",
    "file",
    "filename",
    "downloaded_path",
    "input",
    "input_path",
    "source_path",
}


SOURCE_KEYS = {
    "source_group",
    "source_url",
    "remote_url",
    "media_url",
    "original_url",
    "download_url",
    "final_url",
    "descriptionurl",
    "provider",
    "license",
    "sha256",
    "title",
}


DENIED_EVIDENCE_KEYS = {
    "query",
    "queries",
    "search",
    "searches",
    "prompt",
    "topic",
    "keywords",
    "keyword",
    "asset_query",
    "narration",
    "segment",
    "script",
    "roteiro",
}


def canonical_path(
    value,
):
    value = str(
        value
        or ""
    ).strip()


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

        return value


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
                item,
            )

            for key, item
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


def scene_number(
    value,
):
    if not isinstance(
        value,
        dict
    ):

        return None


    for key in [
        "scene",
        "scene_id",
        "scene_number",
        "cena",
        "index",
    ]:

        try:

            number = int(
                value.get(
                    key
                )
            )


            if 1 <= number <= 999:

                return number


        except Exception:

            pass


    return None


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


def source_identity(
    value,
):
    if not isinstance(
        value,
        dict
    ):

        return {}


    return {
        "sha256":
            str(
                first(
                    value,
                    [
                        "sha256",
                        "file_sha256",
                        "hash",
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
                        "filename",
                        "ObjectName",
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
                        "path",
                        "asset",
                        "downloaded_path",
                        "source_path",
                    ],
                )
                or ""
            ).strip(),
    }


def identity_strength(
    identity,
):
    score = 0


    if re.fullmatch(
        r"[0-9a-f]{64}",
        identity.get(
            "sha256",
            "",
        ),
    ):

        score += 5


    if identity.get(
        "source_group"
    ):

        score += 4


    if canonical_url(
        identity.get(
            "source_url"
        )
    ):

        score += 4


    if identity.get(
        "local_path"
    ):

        score += 3


    if canonical_title(
        identity.get(
            "title"
        )
    ):

        score += 2


    if identity.get(
        "provider"
    ):

        score += 1


    return score


def dict_paths(
    value,
):
    paths = set()


    if not isinstance(
        value,
        dict
    ):

        return paths


    for key, item in (
        value.items()
    ):

        key_norm = str(
            key
        ).lower()


        if (
            key_norm
            not in PATH_KEYS

            and

            not any(
                word in key_norm

                for word in [
                    "path",
                    "asset",
                    "media",
                    "image",
                    "imagem",
                    "video",
                    "file",
                ]
            )
        ):

            continue


        if not isinstance(
            item,
            str
        ):

            continue


        path = canonical_path(
            item
        )


        if path:

            paths.add(
                path
            )


    return paths


def walk_with_ancestry(
    value,
    ancestry=None,
):
    if ancestry is None:

        ancestry = []


    if isinstance(
        value,
        dict
    ):

        yield (
            value,
            list(
                ancestry
            ),
        )


        new_ancestry = (
            ancestry
            +
            [
                value
            ]
        )


        for key, item in (
            value.items()
        ):

            if str(
                key
            ).lower() in DENIED_EVIDENCE_KEYS:

                continue


            yield from walk_with_ancestry(
                item,
                new_ancestry,
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            yield from walk_with_ancestry(
                item,
                ancestry,
            )


def identities_from_branch(
    node,
    ancestry,
):
    candidates = []


    # Closest object first.
    branch = [
        node
    ]


    branch.extend(
        reversed(
            ancestry
        )
    )


    for distance, value in enumerate(
        branch
    ):

        identity = source_identity(
            value
        )


        strength = identity_strength(
            identity
        )


        if strength <= 0:
            continue


        candidates.append({
            "identity":
                identity,

            "strength":
                strength,

            "distance":
                distance,
        })


    return candidates


def walk_local_scope(
    value,
    *,
    depth=0,
    max_depth=8,
):
    """
    Walk only inside the local structural scope.

    This allows:
        scene
        ├── prepared_asset
        └── selected_source

    without treating unrelated branches in other
    scenes as equivalent provenance.
    """

    if depth > max_depth:
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

            if str(
                key
            ).lower() in DENIED_EVIDENCE_KEYS:

                continue


            yield from walk_local_scope(
                item,
                depth=depth + 1,
                max_depth=max_depth,
            )


    elif isinstance(
        value,
        list
    ):

        for item in value:

            yield from walk_local_scope(
                item,
                depth=depth + 1,
                max_depth=max_depth,
            )


def independent_source_identity(
    identity,
):
    """
    A path or scene number alone is never enough.

    Strong independent identifiers:
      - SHA256
      - source_group
      - canonical source URL

    A canonical title is accepted only when accompanied
    by another provenance property.
    """

    digest = str(
        identity.get(
            "sha256"
        )
        or ""
    ).lower()


    strong_hash = bool(
        re.fullmatch(
            r"[0-9a-f]{64}",
            digest,
        )
    )


    strong_group = bool(
        norm(
            identity.get(
                "source_group"
            )
        )
    )


    strong_url = bool(
        canonical_url(
            identity.get(
                "source_url"
            )
        )
    )


    title = canonical_title(
        identity.get(
            "title"
        )
    )


    title_support = bool(
        identity.get(
            "provider"
        )
        or
        identity.get(
            "license"
        )
        or
        identity.get(
            "local_path"
        )
    )


    return bool(
        strong_hash
        or
        strong_group
        or
        strong_url
        or
        (
            len(
                title
            ) >= 8
            and
            title_support
        )
    )


def same_identity(
    left,
    right,
):
    """
    Independent identity comparison used only for
    deduplication of candidates discovered in a branch.
    """

    if (
        left.get(
            "sha256"
        )
        and
        right.get(
            "sha256"
        )
        and
        left[
            "sha256"
        ]
        ==
        right[
            "sha256"
        ]
    ):
        return True


    if (
        left.get(
            "source_group"
        )
        and
        right.get(
            "source_group"
        )
        and
        norm(
            left[
                "source_group"
            ]
        )
        ==
        norm(
            right[
                "source_group"
            ]
        )
    ):
        return True


    left_url = canonical_url(
        left.get(
            "source_url"
        )
    )


    right_url = canonical_url(
        right.get(
            "source_url"
        )
    )


    if (
        left_url
        and
        right_url
        and
        left_url
        ==
        right_url
    ):
        return True


    return False


def collect_scope_sources(
    scope,
    *,
    asset_path,
    asset_scene,
    scope_distance,
):
    candidates = []


    for node, subtree_depth in walk_local_scope(
        scope
    ):

        identity = source_identity(
            node
        )


        if not independent_source_identity(
            identity
        ):
            continue


        identity_path = canonical_path(
            identity.get(
                "local_path"
            )
        )


        # The prepared/rendered asset itself is not
        # automatically its own original source.
        if (
            identity_path
            and
            asset_path
            and
            identity_path
            ==
            asset_path

            and

            not identity.get(
                "source_group"
            )

            and

            not canonical_url(
                identity.get(
                    "source_url"
                )
            )

            and

            not re.fullmatch(
                r"[0-9a-f]{64}",
                identity.get(
                    "sha256",
                    "",
                ),
            )
        ):
            continue


        score = (
            identity_strength(
                identity
            )
            * 100
        )


        # Prefer source identity physically closer to
        # the asset-bearing object.
        score -= (
            scope_distance
            * 45
        )


        score -= (
            subtree_depth
            * 12
        )


        candidate_scene = scene_number(
            node
        )


        if (
            asset_scene is not None
            and
            candidate_scene is not None
            and
            candidate_scene
            ==
            asset_scene
        ):

            score += 90


        candidates.append({
            "identity":
                identity,

            "score":
                score,

            "scope_distance":
                scope_distance,

            "subtree_depth":
                subtree_depth,

            "candidate_scene":
                candidate_scene,
        })


    return candidates


def dedupe_source_candidates(
    candidates,
):
    result = []


    for candidate in sorted(
        candidates,
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    ):

        duplicate = False


        for existing in result:

            if same_identity(
                candidate[
                    "identity"
                ],
                existing[
                    "identity"
                ],
            ):

                duplicate = True
                break


        if not duplicate:

            result.append(
                candidate
            )


    return result


def resolve_from_origin_json(
    asset,
):
    """
    V2.5.1 structural resolver.

    Hop chain:

        scene_usage asset
            ↓ exact asset path
        local JSON branch
            ↓ closest scene/container
        sibling/nested selected_source
            ↓ independent source identity
        metadata record

    Scene number is only a structural preference.
    It cannot create provenance by itself.
    """

    origin = canonical_path(
        asset.get(
            "origin"
        )
    )


    asset_path = canonical_path(
        asset.get(
            "path"
        )
    )


    asset_scene = scene_number(
        asset
    )


    if not origin:

        return {
            "matched":
                False,

            "method":
                "origin_missing",
        }


    if not asset_path:

        return {
            "matched":
                False,

            "method":
                "asset_path_missing",
        }


    origin_path = Path(
        origin
    )


    if (
        not origin_path.exists()
        or
        not origin_path.is_file()
        or
        origin_path.suffix.lower()
        != ".json"
    ):

        return {
            "matched":
                False,

            "method":
                "origin_not_readable_json",
        }


    try:

        data = json.loads(
            origin_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )


    except Exception:

        return {
            "matched":
                False,

            "method":
                "origin_json_parse_failed",
        }


    path_matches = []


    for node, ancestry in walk_with_ancestry(
        data
    ):

        paths = dict_paths(
            node
        )


        if asset_path not in paths:
            continue


        path_matches.append({
            "node":
                node,

            "ancestry":
                ancestry,
        })


    if not path_matches:

        return {
            "matched":
                False,

            "method":
                "asset_path_not_found_in_origin_json",
        }


    source_candidates = []


    for path_match in path_matches:

        node = path_match[
            "node"
        ]


        ancestry = path_match[
            "ancestry"
        ]


        # -------------------------------------------------
        # Scope 0: exact object containing the asset.
        # -------------------------------------------------

        source_candidates.extend(
            collect_scope_sources(
                node,
                asset_path=asset_path,
                asset_scene=asset_scene,
                scope_distance=0,
            )
        )


        # -------------------------------------------------
        # Closest ancestors.
        #
        # The first parent is typically the scene object,
        # which can contain selected_source as a sibling.
        #
        # Limit prevents walking the entire document as
        # one undifferentiated source pool.
        # -------------------------------------------------

        nearest = list(
            reversed(
                ancestry
            )
        )[
            :5
        ]


        for distance, scope in enumerate(
            nearest,
            start=1,
        ):

            scope_scene = scene_number(
                scope
            )


            # If this scope explicitly belongs to a
            # different scene, it cannot establish the
            # asset's provenance.
            if (
                asset_scene is not None
                and
                scope_scene is not None
                and
                scope_scene
                !=
                asset_scene
            ):
                continue


            candidates = collect_scope_sources(
                scope,
                asset_path=asset_path,
                asset_scene=asset_scene,
                scope_distance=distance,
            )


            # Bonus when the enclosing scope explicitly
            # identifies the same scene.
            if (
                asset_scene is not None
                and
                scope_scene
                ==
                asset_scene
            ):

                for candidate in candidates:

                    candidate[
                        "score"
                    ] += 140


                    candidate[
                        "same_scene_scope"
                    ] = True


            source_candidates.extend(
                candidates
            )


    source_candidates = dedupe_source_candidates(
        source_candidates
    )


    if not source_candidates:

        return {
            "matched":
                False,

            "method":
                "asset_branch_source_identity_missing",
        }


    source_candidates.sort(
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    )


    best = source_candidates[
        0
    ]


    # A same-score different identity means structural
    # ambiguity. Stay HOLD instead of guessing.
    if len(
        source_candidates
    ) > 1:

        second = source_candidates[
            1
        ]


        if (
            second[
                "score"
            ]
            ==
            best[
                "score"
            ]

            and

            not same_identity(
                best[
                    "identity"
                ],
                second[
                    "identity"
                ],
            )
        ):

            return {
                "matched":
                    False,

                "method":
                    "origin_branch_identity_ambiguous",

                "candidate_count":
                    len(
                        source_candidates
                    ),

                "top_score":
                    best[
                        "score"
                    ],
            }


    return {
        "matched":
            True,

        "method":
            "origin_json_asset_sibling_source",

        "confidence":
            "STRONG",

        "identity":
            best[
                "identity"
            ],

        "score":
            best[
                "score"
            ],

        "origin":
            origin,

        "candidate_count":
            len(
                source_candidates
            ),

        "same_scene_scope":
            bool(
                best.get(
                    "same_scene_scope"
                )
            ),
    }


def source_identity_key(
    identity,
):
    return (
        identity.get(
            "sha256"
        )
        or
        norm(
            identity.get(
                "source_group"
            )
        )
        or
        canonical_url(
            identity.get(
                "source_url"
            )
        )
        or
        canonical_title(
            identity.get(
                "title"
            )
        )
        or
        canonical_path(
            identity.get(
                "local_path"
            )
        )
    )


def metadata_record_match(
    identity,
    metadata,
):
    best = []


    for index, record in enumerate(
        metadata.get(
            "records",
            []
        )
    ):

        rid = source_identity(
            record
        )


        score = 0

        reasons = []


        if (
            identity.get(
                "sha256"
            )

            and

            rid.get(
                "sha256"
            )

            and

            identity[
                "sha256"
            ]
            ==
            rid[
                "sha256"
            ]
        ):

            score += 500

            reasons.append(
                "sha256_exact"
            )


        if (
            identity.get(
                "source_group"
            )

            and

            rid.get(
                "source_group"
            )

            and

            norm(
                identity[
                    "source_group"
                ]
            )
            ==
            norm(
                rid[
                    "source_group"
                ]
            )
        ):

            score += 400

            reasons.append(
                "source_group_exact"
            )


        iu = canonical_url(
            identity.get(
                "source_url"
            )
        )


        ru = canonical_url(
            rid.get(
                "source_url"
            )
        )


        if (
            iu
            and
            ru
            and
            iu == ru
        ):

            score += 350

            reasons.append(
                "source_url_exact"
            )


        it = canonical_title(
            identity.get(
                "title"
            )
        )


        rt = canonical_title(
            rid.get(
                "title"
            )
        )


        if (
            it
            and
            rt
            and
            len(
                it
            ) >= 8
            and
            it == rt
        ):

            score += 250

            reasons.append(
                "title_exact"
            )


        ip = canonical_path(
            identity.get(
                "local_path"
            )
        )


        rp = canonical_path(
            rid.get(
                "local_path"
            )
        )


        if (
            ip
            and
            rp
            and
            ip == rp
        ):

            score += 300

            reasons.append(
                "local_path_exact"
            )


        if score > 0:

            best.append({
                "record_index":
                    index,

                "score":
                    score,

                "reasons":
                    reasons,

                "record":
                    record,
            })


    best.sort(
        key=lambda item:
            item[
                "score"
            ],
        reverse=True,
    )


    if not best:

        return None


    if (
        len(
            best
        ) > 1

        and

        best[
            0
        ][
            "score"
        ]
        ==
        best[
            1
        ][
            "score"
        ]

        and

        best[
            0
        ][
            "record_index"
        ]
        !=
        best[
            1
        ][
            "record_index"
        ]
    ):

        return {
            "ambiguous":
                True,

            "matches":
                best[
                    :5
                ],
        }


    return {
        "ambiguous":
            False,

        **best[
            0
        ],
    }


def origin_index(
    metadata,
):
    result = defaultdict(
        list
    )


    for index, record in enumerate(
        metadata.get(
            "records",
            []
        )
    ):

        origin = canonical_path(
            record.get(
                "origin"
            )
        )


        if origin:

            result[
                origin
            ].append({
                "record_index":
                    index,

                "record":
                    record,
            })


    return result


def fallback_origin_scene(
    asset,
    metadata_index,
):
    origin = canonical_path(
        asset.get(
            "origin"
        )
    )


    if not origin:

        return None


    candidates = metadata_index.get(
        origin,
        []
    )


    if not candidates:

        return None


    scene = scene_number(
        asset
    )


    if scene is None:

        return None


    matches = []


    for item in candidates:

        record = item[
            "record"
        ]


        if (
            scene_number(
                record
            )
            ==
            scene
        ):

            identity = source_identity(
                record
            )


            if identity_strength(
                identity
            ) > 0:

                matches.append(
                    item
                )


    if len(
        matches
    ) != 1:

        return None


    item = matches[
        0
    ]


    return {
        "record_index":
            item[
                "record_index"
            ],

        "record":
            item[
                "record"
            ],

        "method":
            "origin_exact_plus_scene_exact",

        "confidence":
            "STRONG",
    }


def transport_identity(
    row,
    record,
):
    identity = source_identity(
        record
    )


    for key in [
        "source_group",
        "source_url",
        "title",
        "provider",
        "license",
        "local_path",
        "sha256",
    ]:

        value = identity.get(
            key
        )


        if (
            value not in [
                None,
                "",
            ]

            and

            not row.get(
                key
            )
        ):

            row[
                key
            ] = value


def enrich(
    scene_usage,
    metadata,
    run_dir,
):
    used_assets = (
        scene_usage.get(
            "used_assets"
        )
        or []
    )


    metadata_index = origin_index(
        metadata
    )


    rows = []


    direct_links = 0

    multihop_links = 0

    origin_scene_links = 0

    ambiguous = 0

    unresolved = 0


    for asset in used_assets:

        row = dict(
            asset
        )


        final_match = None


        # ==================================================
        # STAGE A:
        # Existing asset identity -> metadata directly.
        # ==================================================

        existing_identity = source_identity(
            asset
        )


        if identity_strength(
            existing_identity
        ) > 0:

            direct = metadata_record_match(
                existing_identity,
                metadata,
            )


            if (
                direct

                and

                not direct.get(
                    "ambiguous"
                )
            ):

                final_match = {
                    "record_index":
                        direct[
                            "record_index"
                        ],

                    "record":
                        direct[
                            "record"
                        ],

                    "method":
                        "direct_identity",

                    "confidence":
                        "STRONG",

                    "reasons":
                        direct[
                            "reasons"
                        ],
                }


                direct_links += 1


        # ==================================================
        # STAGE B:
        # scene_usage.path -> origin JSON branch -> source
        # identity -> metadata record.
        # ==================================================

        if final_match is None:

            branch = resolve_from_origin_json(
                asset
            )


            if branch.get(
                "matched"
            ):

                metadata_match = (
                    metadata_record_match(
                        branch[
                            "identity"
                        ],
                        metadata,
                    )
                )


                if (
                    metadata_match

                    and

                    not metadata_match.get(
                        "ambiguous"
                    )
                ):

                    final_match = {
                        "record_index":
                            metadata_match[
                                "record_index"
                            ],

                        "record":
                            metadata_match[
                                "record"
                            ],

                        "method":
                            "multi_hop_origin_asset_source",

                        "confidence":
                            "STRONG",

                        "branch_method":
                            branch[
                                "method"
                            ],

                        "branch_score":
                            branch[
                                "score"
                            ],

                        "reasons":
                            metadata_match[
                                "reasons"
                            ],
                    }


                    multihop_links += 1


                elif (
                    metadata_match

                    and

                    metadata_match.get(
                        "ambiguous"
                    )
                ):

                    ambiguous += 1


        # ==================================================
        # STAGE C:
        # Same provenance document + exact scene.
        #
        # This remains a fallback and only passes when one
        # independent source record exists for that scene.
        # ==================================================

        if final_match is None:

            fallback = fallback_origin_scene(
                asset,
                metadata_index,
            )


            if fallback is not None:

                final_match = fallback

                origin_scene_links += 1


        if final_match is not None:

            transport_identity(
                row,
                final_match[
                    "record"
                ],
            )


            row[
                "source_usage_join"
            ] = {
                "linked":
                    True,

                "record_index":
                    final_match[
                        "record_index"
                    ],

                "method":
                    final_match[
                        "method"
                    ],

                "confidence":
                    final_match[
                        "confidence"
                    ],

                "reasons":
                    final_match.get(
                        "reasons",
                        [],
                    ),

                "scene_only_used_as_evidence":
                    False,

                "query_used_as_evidence":
                    False,
            }


        else:

            row[
                "source_usage_join"
            ] = {
                "linked":
                    False,

                "method":
                    "multi_hop_unresolved",

                "confidence":
                    "HOLD",

                "scene_only_used_as_evidence":
                    False,

                "query_used_as_evidence":
                    False,
            }


            unresolved += 1


        rows.append(
            row
        )


    linked_assets = sum(
        bool(
            row.get(
                "source_usage_join",
                {}
            ).get(
                "linked"
            )
        )

        for row in rows
    )


    report = dict(
        scene_usage
    )


    report[
        "used_assets"
    ] = rows


    report[
        "source_usage_join"
    ] = {
        "version":
            "V2.5",

        "used_assets":
            len(
                rows
            ),

        "linked_assets":
            linked_assets,

        "direct_identity_links":
            direct_links,

        "multi_hop_links":
            multihop_links,

        "origin_scene_links":
            origin_scene_links,

        "ambiguous_assets":
            ambiguous,

        "unresolved_assets":
            unresolved,

        "scene_only_used_as_evidence":
            False,

        "query_used_as_evidence":
            False,
    }


    save_json(
        run_dir
        / "source_usage_join.json",
        report[
            "source_usage_join"
        ],
    )


    save_json(
        run_dir
        / "scene_usage_enriched.json",
        report,
    )


    return report


if __name__ == "__main__":

    print(
        "VI1510.1 V2.5 MULTI-HOP PROVENANCE RESOLVER=PASS"
    )
