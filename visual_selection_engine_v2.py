#!/usr/bin/env python3

import os
import re

from collections import Counter, deque
from pathlib import Path


_ENABLED = os.environ.get(
    "SAP_VSE_V2",
    "1",
).strip().lower() not in {
    "0",
    "false",
    "off",
    "no",
}


_PROVIDER_WINDOW = int(
    os.environ.get(
        "SAP_VSE_PROVIDER_WINDOW",
        "8",
    )
)


_GROUP_WINDOW = int(
    os.environ.get(
        "SAP_VSE_GROUP_WINDOW",
        "10",
    )
)


_KEY_WINDOW = int(
    os.environ.get(
        "SAP_VSE_KEY_WINDOW",
        "16",
    )
)


_TYPE_WINDOW = int(
    os.environ.get(
        "SAP_VSE_TYPE_WINDOW",
        "8",
    )
)


_PROVIDER_HISTORY = deque(
    maxlen=_PROVIDER_WINDOW
)

_GROUP_HISTORY = deque(
    maxlen=_GROUP_WINDOW
)

_KEY_HISTORY = deque(
    maxlen=_KEY_WINDOW
)

_TYPE_HISTORY = deque(
    maxlen=_TYPE_WINDOW
)


def enabled():
    return _ENABLED


def _num(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _first(data, keys, default=""):
    if not isinstance(data, dict):
        return default

    for key in keys:
        value = data.get(key)

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return default


def _text(value):
    if value is None:
        return ""

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        value = " ".join(
            str(x)
            for x in value
        )

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip().lower()


def candidate_provider(candidate):
    value = _first(
        candidate,
        [
            "provider",
            "fonte",
            "source_provider",
            "platform",
        ],
    )

    return _text(
        value
    )


def candidate_group(candidate):
    return _text(
        _first(
            candidate,
            [
                "source_group",
                "group",
                "collection",
                "collection_id",
            ],
        )
    )


def candidate_key(candidate):
    return _text(
        _first(
            candidate,
            [
                "sha256",
                "source_url",
                "page_url",
                "url",
                "download_url",
                "id",
                "asset_id",
            ],
        )
    )


def media_type(candidate):
    value = _text(
        _first(
            candidate,
            [
                "tipo",
                "type",
                "media_type",
                "kind",
            ],
        )
    )

    if any(
        token in value
        for token in [
            "video",
            "vídeo",
            "mp4",
            "webm",
            "mov",
        ]
    ):
        return "video"

    if any(
        token in value
        for token in [
            "foto",
            "photo",
            "image",
            "imagem",
            "jpg",
            "png",
            "webp",
        ]
    ):
        return "photo"

    url = _text(
        _first(
            candidate,
            [
                "url",
                "source_url",
            ],
        )
    )

    if re.search(
        r"\.(mp4|webm|mov)(?:$|\?)",
        url,
    ):
        return "video"

    if re.search(
        r"\.(jpg|jpeg|png|webp)(?:$|\?)",
        url,
    ):
        return "photo"

    return "unknown"


def query_text(candidate):
    parts = []

    for key in [
        "query",
        "search",
        "visual_query",
        "asset_query",
        "keyword",
        "keywords",
        "scene_query",
    ]:
        value = candidate.get(
            key
        ) if isinstance(
            candidate,
            dict
        ) else None

        if value:
            parts.append(
                _text(value)
            )

    return " ".join(
        parts
    )


def asset_text(candidate):
    parts = []

    for key in [
        "title",
        "name",
        "description",
        "alt",
        "tags",
        "category",
        "categories",
        "caption",
    ]:
        value = candidate.get(
            key
        ) if isinstance(
            candidate,
            dict
        ) else None

        if value:
            parts.append(
                _text(value)
            )

    return " ".join(
        parts
    )


def reset_history():
    _PROVIDER_HISTORY.clear()
    _GROUP_HISTORY.clear()
    _KEY_HISTORY.clear()
    _TYPE_HISTORY.clear()


def history_snapshot():
    return {
        "providers":
            list(
                _PROVIDER_HISTORY
            ),

        "groups":
            list(
                _GROUP_HISTORY
            ),

        "keys":
            list(
                _KEY_HISTORY
            ),

        "types":
            list(
                _TYPE_HISTORY
            ),
    }


def note_selected(candidate):
    if not isinstance(
        candidate,
        dict,
    ):
        return False

    provider = candidate_provider(
        candidate
    )

    group = candidate_group(
        candidate
    )

    key = candidate_key(
        candidate
    )

    kind = media_type(
        candidate
    )

    if provider:
        _PROVIDER_HISTORY.append(
            provider
        )

    if group:
        _GROUP_HISTORY.append(
            group
        )

    if key:
        _KEY_HISTORY.append(
            key
        )

    if kind != "unknown":
        _TYPE_HISTORY.append(
            kind
        )

    return True


def must_info(candidate):
    if not isinstance(
        candidate,
        dict,
    ):
        return 0, 0, 0.0


    hits = int(
        _num(
            _first(
                candidate,
                [
                    "must_hits",
                    "required_hits",
                    "must_match_count",
                ],
                0,
            ),
            0,
        )
    )


    total = int(
        _num(
            _first(
                candidate,
                [
                    "must_total",
                    "total_must",
                    "required_count",
                    "must_count",
                ],
                0,
            ),
            0,
        )
    )


    if total <= 0:

        raw = _first(
            candidate,
            [
                "must",
                "must_terms",
                "required",
                "required_terms",
            ],
            None,
        )

        if isinstance(
            raw,
            (
                list,
                tuple,
                set,
            ),
        ):
            total = len(
                raw
            )


    if total <= 0 and (
        "must_hits"
        in candidate
    ):
        total = max(
            2,
            hits,
        )


    if total <= 0:
        return hits, 0, 0.0


    ratio = min(
        1.0,
        hits
        /
        max(
            total,
            1,
        ),
    )

    return (
        hits,
        total,
        ratio,
    )


def must_tier(candidate):
    hits, total, ratio = (
        must_info(
            candidate
        )
    )

    if total <= 0:
        return 2

    if hits >= total:
        return 4

    if ratio >= 0.75:
        return 3

    if ratio >= 0.50:
        return 2

    if hits > 0:
        return 1

    return 0


def avoid_hits(candidate):
    if not isinstance(
        candidate,
        dict,
    ):
        return 0

    raw = _first(
        candidate,
        [
            "avoid_hits",
            "negative_hits",
            "forbidden_hits",
        ],
        0,
    )

    if isinstance(
        raw,
        (
            list,
            tuple,
            set,
        ),
    ):
        return len(
            raw
        )

    return int(
        _num(
            raw,
            0,
        )
    )


def base_score(
    candidate,
    scorer=None,
):
    if callable(
        scorer
    ):
        try:
            return float(
                scorer(
                    candidate
                )
            )
        except Exception:
            pass


    return _num(
        _first(
            candidate,
            [
                "score",
                "final_score",
                "real_score",
                "ranking_score",
                "semantic_score",
                "combined_score",
            ],
            0,
        ),
        0,
    )


def resolution_adjustment(
    candidate
):
    width = int(
        _num(
            _first(
                candidate,
                [
                    "width",
                    "largura",
                ],
                0,
            )
        )
    )

    height = int(
        _num(
            _first(
                candidate,
                [
                    "height",
                    "altura",
                ],
                0,
            )
        )
    )


    if (
        width <= 0
        or
        height <= 0
    ):
        return 0.0


    short_edge = min(
        width,
        height,
    )


    if short_edge < 360:
        return -70.0

    if short_edge < 480:
        return -45.0

    if short_edge < 720:
        return -22.0

    if short_edge >= 1080:
        return 8.0

    return 3.0


_PERSON_WORDS = {
    "woman",
    "man",
    "person",
    "portrait",
    "model",
    "face",
    "smiling",
    "girl",
    "boy",
    "people",
}


_OBJECT_INTENT = {
    "document",
    "report",
    "paper",
    "gavel",
    "building",
    "window",
    "city",
    "skyline",
    "room",
    "police tape",
    "magnifying glass",
    "flashlight",
    "gate",
    "apartment",
    "courthouse",
    "forensic",
    "desk",
}


_PERSON_INTENT = {
    "father",
    "mother",
    "woman",
    "man",
    "person",
    "interview",
    "testimony",
    "face",
}


def semantic_mismatch_penalty(
    candidate
):
    query = query_text(
        candidate
    )

    asset = asset_text(
        candidate
    )


    if not query or not asset:
        return 0.0


    penalty = 0.0


    object_intent = any(
        token in query
        for token in _OBJECT_INTENT
    )


    person_intent = any(
        token in query
        for token in _PERSON_INTENT
    )


    person_asset = any(
        token in asset
        for token in _PERSON_WORDS
    )


    if (
        object_intent
        and
        person_asset
        and
        not person_intent
    ):
        penalty += 55.0


    if (
        any(
            x in query
            for x in [
                "night",
                "dark",
                "shadow",
            ]
        )
        and
        any(
            x in asset
            for x in [
                "sunny",
                "bright beach",
                "daylight beach",
            ]
        )
    ):
        penalty += 32.0


    if (
        any(
            x in query
            for x in [
                "document",
                "report",
                "paper",
                "autopsy",
                "forensic",
            ]
        )
        and
        any(
            x in asset
            for x in [
                "pill",
                "pills",
                "medicine",
                "tablet computer",
                "smartphone",
            ]
        )
    ):
        penalty += 52.0


    if (
        any(
            x in query
            for x in [
                "building",
                "city",
                "skyline",
                "apartment",
                "courthouse",
            ]
        )
        and
        any(
            x in asset
            for x in [
                "forest",
                "beach",
                "mountain trail",
                "flower field",
            ]
        )
    ):
        penalty += 45.0


    return penalty


def diversity_adjustment(
    candidate
):
    provider = candidate_provider(
        candidate
    )

    group = candidate_group(
        candidate
    )

    key = candidate_key(
        candidate
    )


    providers = Counter(
        _PROVIDER_HISTORY
    )

    groups = Counter(
        _GROUP_HISTORY
    )


    adjustment = 0.0


    if provider:

        count = providers[
            provider
        ]

        adjustment -= (
            count
            *
            18.0
        )


        if (
            _PROVIDER_HISTORY
            and
            provider
            ==
            _PROVIDER_HISTORY[-1]
        ):
            adjustment -= 26.0


        if (
            len(
                _PROVIDER_HISTORY
            )
            >= 2
            and
            provider
            not in
            _PROVIDER_HISTORY
        ):
            adjustment += 12.0


    if group:

        adjustment -= (
            groups[group]
            *
            34.0
        )


        if (
            _GROUP_HISTORY
            and
            group
            ==
            _GROUP_HISTORY[-1]
        ):
            adjustment -= 46.0


    if (
        key
        and
        key in
        _KEY_HISTORY
    ):
        adjustment -= 180.0


    return adjustment


def motion_adjustment(
    candidate
):
    kind = media_type(
        candidate
    )


    if kind == "unknown":
        return 0.0


    if not _TYPE_HISTORY:

        return (
            7.0
            if kind == "video"
            else 0.0
        )


    videos = sum(
        1
        for item in
        _TYPE_HISTORY
        if item == "video"
    )


    ratio = (
        videos
        /
        len(
            _TYPE_HISTORY
        )
    )


    target = _num(
        os.environ.get(
            "SAP_VSE_VIDEO_TARGET",
            "0.42",
        ),
        0.42,
    )


    adjustment = 0.0


    if kind == "video":

        if ratio < target:
            adjustment += 9.0
        else:
            adjustment -= 8.0


    elif kind == "photo":

        if ratio > target:
            adjustment += 7.0


    if (
        _TYPE_HISTORY
        and
        kind
        ==
        _TYPE_HISTORY[-1]
    ):
        adjustment -= 5.0

    else:
        adjustment += 3.0


    return adjustment


def quality_breakdown(
    candidate,
    scorer=None,
):
    tier = must_tier(
        candidate
    )

    hits, total, ratio = (
        must_info(
            candidate
        )
    )

    avoid = avoid_hits(
        candidate
    )

    base = base_score(
        candidate,
        scorer,
    )


    tier_bonus = {
        4: 85.0,
        3: 45.0,
        2: 5.0,
        1: -45.0,
        0: -130.0,
    }.get(
        tier,
        0.0,
    )


    avoid_adjust = (
        -48.0
        *
        avoid
    )


    mismatch = (
        semantic_mismatch_penalty(
            candidate
        )
    )


    resolution = (
        resolution_adjustment(
            candidate
        )
    )


    diversity = (
        diversity_adjustment(
            candidate
        )
    )


    motion = (
        motion_adjustment(
            candidate
        )
    )


    effective = (
        base
        +
        tier_bonus
        +
        avoid_adjust
        -
        mismatch
        +
        resolution
        +
        diversity
        +
        motion
    )


    return {
        "tier":
            tier,

        "must_hits":
            hits,

        "must_total":
            total,

        "must_ratio":
            ratio,

        "avoid_hits":
            avoid,

        "base":
            base,

        "tier_bonus":
            tier_bonus,

        "mismatch_penalty":
            mismatch,

        "resolution_adjustment":
            resolution,

        "diversity_adjustment":
            diversity,

        "motion_adjustment":
            motion,

        "effective_score":
            effective,
    }


def rank_key(
    candidate,
    scorer=None,
):
    info = quality_breakdown(
        candidate,
        scorer,
    )

    return (
        info[
            "tier"
        ],

        -info[
            "avoid_hits"
        ],

        -info[
            "mismatch_penalty"
        ],

        info[
            "effective_score"
        ],
    )


def rerank(
    candidates,
    scorer=None,
):
    if not _ENABLED:
        return candidates

    if not isinstance(
        candidates,
        list,
    ):
        return candidates


    if (
        len(
            candidates
        )
        <= 1
    ):
        return candidates


    if not all(
        isinstance(
            item,
            dict,
        )
        for item in
        candidates
    ):
        return candidates


    indexed = list(
        enumerate(
            candidates
        )
    )


    indexed.sort(
        key=lambda row: (
            rank_key(
                row[1],
                scorer,
            ),
            -row[0],
        ),
        reverse=True,
    )


    return [
        candidate
        for _,
        candidate
        in indexed
    ]


def _candidate_list_from_inputs(
    args,
    kwargs,
):
    for value in args:

        if (
            isinstance(
                value,
                list,
            )
            and
            value
            and
            all(
                isinstance(
                    item,
                    dict,
                )
                for item in
                value
            )
        ):
            return value


    for value in kwargs.values():

        if (
            isinstance(
                value,
                list,
            )
            and
            value
            and
            all(
                isinstance(
                    item,
                    dict,
                )
                for item in
                value
            )
        ):
            return value


    return []


def _selected_candidate(
    result
):
    if isinstance(
        result,
        dict,
    ):
        return result


    if isinstance(
        result,
        tuple,
    ):

        for value in result:

            if isinstance(
                value,
                dict,
            ):
                return value


    return None


def _replace_selected(
    result,
    replacement,
):
    if isinstance(
        result,
        dict,
    ):
        return replacement


    if isinstance(
        result,
        tuple,
    ):

        output = list(
            result
        )

        for index, value in enumerate(
            output
        ):

            if isinstance(
                value,
                dict,
            ):

                output[
                    index
                ] = replacement

                return tuple(
                    output
                )


    return result


def guard_selector_result(
    result,
    args,
    kwargs,
    scorer=None,
):
    if not _ENABLED:
        return result


    candidates = (
        _candidate_list_from_inputs(
            args,
            kwargs,
        )
    )


    if not candidates:
        return result


    selected = (
        _selected_candidate(
            result
        )
    )


    if not selected:
        return result


    ranked = rerank(
        list(
            candidates
        ),
        scorer,
    )


    if not ranked:
        return result


    best = ranked[0]


    chosen_info = (
        quality_breakdown(
            selected,
            scorer,
        )
    )


    best_info = (
        quality_breakdown(
            best,
            scorer,
        )
    )


    # Absolute rule:
    # motion/documentary preference cannot downgrade MUST tier.
    if (
        best_info[
            "tier"
        ]
        >
        chosen_info[
            "tier"
        ]
    ):
        return _replace_selected(
            result,
            best,
        )


    delta = _num(
        os.environ.get(
            "SAP_VSE_OVERRIDE_DELTA",
            "45",
        ),
        45,
    )


    if (
        best_info[
            "tier"
        ]
        ==
        chosen_info[
            "tier"
        ]
        and
        best_info[
            "effective_score"
        ]
        >
        chosen_info[
            "effective_score"
        ]
        +
        delta
    ):
        return _replace_selected(
            result,
            best,
        )


    return result


def _transform_output(
    result,
    scorer=None,
):
    if isinstance(
        result,
        list,
    ):
        return rerank(
            result,
            scorer,
        )


    if isinstance(
        result,
        dict,
    ):

        changed = False
        output = dict(
            result
        )

        for key in [
            "candidates",
            "candidatos",
            "items",
            "results",
            "media",
            "assets",
        ]:

            value = output.get(
                key
            )

            if (
                isinstance(
                    value,
                    list,
                )
                and
                value
                and
                all(
                    isinstance(
                        x,
                        dict,
                    )
                    for x in
                    value
                )
            ):

                output[
                    key
                ] = rerank(
                    value,
                    scorer,
                )

                changed = True


        return (
            output
            if changed
            else result
        )


    return result


def _find_candidate(
    args,
    kwargs,
):
    for key in [
        "candidate",
        "candidato",
        "asset",
        "item",
        "media",
    ]:

        value = kwargs.get(
            key
        )

        if isinstance(
            value,
            dict,
        ):
            return value


    for value in args:

        if isinstance(
            value,
            dict,
        ):
            return value


    return {}


def install(
    namespace
):
    state = namespace.get(
        "_SAP_VISUAL_SELECTION_ENGINE_V2"
    )


    if isinstance(
        state,
        dict,
    ):
        return False


    scorer = namespace.get(
        "score_real_5_2"
    )


    wrapped = []


    for name in [
        "buscar_todos_candidatos",
        "preparar_candidatos",
        "ordenar_failover_5_2",
    ]:

        original = namespace.get(
            name
        )


        if not callable(
            original
        ):
            continue


        backup_name = (
            "_sap_vse_v2_original_"
            +
            name
        )


        namespace[
            backup_name
        ] = original


        def make_rank_wrapper(
            function_name,
            original_name,
        ):

            def wrapper(
                *args,
                **kwargs,
            ):

                result = namespace[
                    original_name
                ](
                    *args,
                    **kwargs,
                )


                transformed = (
                    _transform_output(
                        result,
                        scorer,
                    )
                )


                namespace[
                    "_SAP_VSE_V2_LAST_RANK_STAGE"
                ] = function_name


                return transformed


            return wrapper


        namespace[
            name
        ] = make_rank_wrapper(
            name,
            backup_name,
        )


        wrapped.append(
            name
        )


    for name in [
        "escolher_documental_prioritario",
        "escolher_com_movimento",
    ]:

        original = namespace.get(
            name
        )


        if not callable(
            original
        ):
            continue


        backup_name = (
            "_sap_vse_v2_original_"
            +
            name
        )


        namespace[
            backup_name
        ] = original


        def make_selector_wrapper(
            function_name,
            original_name,
        ):

            def wrapper(
                *args,
                **kwargs,
            ):

                result = namespace[
                    original_name
                ](
                    *args,
                    **kwargs,
                )


                guarded = (
                    guard_selector_result(
                        result,
                        args,
                        kwargs,
                        scorer,
                    )
                )


                namespace[
                    "_SAP_VSE_V2_LAST_SELECTOR"
                ] = function_name


                return guarded


            return wrapper


        namespace[
            name
        ] = make_selector_wrapper(
            name,
            backup_name,
        )


        wrapped.append(
            name
        )


    downloader = namespace.get(
        "baixar_candidato_5_2"
    )


    if callable(
        downloader
    ):

        backup_name = (
            "_sap_vse_v2_original_"
            "baixar_candidato_5_2"
        )


        namespace[
            backup_name
        ] = downloader


        def baixar_candidato_5_2(
            *args,
            **kwargs,
        ):

            result = namespace[
                backup_name
            ](
                *args,
                **kwargs,
            )


            success = bool(
                isinstance(
                    result,
                    tuple,
                )
                and
                len(
                    result
                )
                >= 1
                and
                result[
                    0
                ]
            )


            if success:

                candidate = _find_candidate(
                    args,
                    kwargs,
                )

                note_selected(
                    candidate
                )


                namespace[
                    "_SAP_VSE_V2_LAST_ACCEPTED"
                ] = {
                    "provider":
                        candidate_provider(
                            candidate
                        ),

                    "source_group":
                        candidate_group(
                            candidate
                        ),

                    "media_type":
                        media_type(
                            candidate
                        ),

                    "must":
                        must_info(
                            candidate
                        ),
                }


            return result


        namespace[
            "baixar_candidato_5_2"
        ] = baixar_candidato_5_2


        wrapped.append(
            "baixar_candidato_5_2"
        )


    namespace[
        "_SAP_VISUAL_SELECTION_ENGINE_V2"
    ] = {
        "enabled":
            _ENABLED,

        "wrapped":
            wrapped,

        "must_tier_priority":
            True,

        "provider_diversity":
            True,

        "source_group_diversity":
            True,

        "semantic_mismatch_guard":
            True,

        "resolution_quality":
            True,

        "photo_video_balance":
            True,

        "motion_cannot_downgrade_must":
            True,

        "hard_blocking":
            False,
    }


    return bool(
        wrapped
    )


if __name__ == "__main__":

    print(
        "SHORTAUTOPRO VISUAL SELECTION ENGINE V2"
    )

    print(
        "ENABLED=",
        _ENABLED,
    )
