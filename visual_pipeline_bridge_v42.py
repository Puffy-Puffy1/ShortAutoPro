#!/usr/bin/env python3

"""
ShortAutoPro Visual Pipeline Bridge V4.2

Production responsibilities:

1. Put VSE4 after legacy selection.
2. Hard-protect geography.
3. Detect false medical associations.
4. Penalize generic lifestyle stock.
5. Prefer stronger MUST coverage.
6. Diversify provider/source/type.
7. Rescue weak searches.
8. Commit only first successful scene asset.
9. Remove stale sibling jpg/mp4 from same scene.
10. Fail-open through SAP_VSE42=0.
"""

from __future__ import annotations

import functools
import importlib.util
import inspect
import os
from pathlib import Path
from typing import Any


ROOT = Path(os.getenv("SHORTAUTOPRO_BASE", str(Path.home() / "ShortAutoPro"))).resolve()

VSE_PATH = (
    ROOT
    / "visual_selection_engine_v4.py"
)


def _load_vse():

    spec = importlib.util.spec_from_file_location(
        "shortautopro_vse4_runtime",
        VSE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "VSE4 import spec unavailable"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


VSE = _load_vse()


_STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def enabled():

    return (
        os.getenv(
            "SAP_VSE42",
            "1",
        )
        !=
        "0"
    )


def reset_state():

    for key in _STATE:
        _STATE[key].clear()


def _trim_state():

    for key in _STATE:

        if len(_STATE[key]) > 32:
            del _STATE[key][:-32]


def _norm(value):

    fn = getattr(
        VSE,
        "norm",
        None,
    )

    if callable(fn):

        try:
            return fn(value)
        except Exception:
            pass

    return str(
        value or ""
    ).casefold().strip()


def _objget(obj, keys, default=None):

    fn = getattr(
        VSE,
        "objget",
        None,
    )

    if callable(fn):

        try:
            return fn(
                obj,
                keys,
                default,
            )
        except Exception:
            pass


    if not isinstance(
        keys,
        (
            list,
            tuple,
            set,
        ),
    ):
        keys = [keys]


    for key in keys:

        if isinstance(
            obj,
            dict,
        ):

            if key in obj:
                return obj[key]

        else:

            try:
                value = getattr(
                    obj,
                    key,
                    None,
                )

                if value is not None:
                    return value

            except Exception:
                pass


    return default


def _candidate_text(candidate):

    fn = getattr(
        VSE,
        "candidate_text",
        None,
    )

    if callable(fn):

        try:
            return fn(
                candidate
            )
        except Exception:
            pass


    values = []

    for key in (
        "title",
        "name",
        "description",
        "tags",
        "keywords",
        "query",
        "provider",
        "source_group",
    ):

        value = _objget(
            candidate,
            key,
            None,
        )

        if value:
            values.append(
                str(value)
            )


    return " ".join(values).casefold()


def _tokens(value):

    fn = getattr(
        VSE,
        "tokens",
        None,
    )

    if callable(fn):

        try:
            return set(
                fn(value)
            )
        except Exception:
            pass

    return set(
        _norm(value).split()
    )


def _provider(candidate):

    fn = getattr(
        VSE,
        "provider",
        None,
    )

    if callable(fn):

        try:
            return fn(candidate)
        except Exception:
            pass

    return _norm(
        _objget(
            candidate,
            [
                "provider",
                "source",
            ],
            "unknown",
        )
    )


def _source_group(candidate):

    fn = getattr(
        VSE,
        "source_group",
        None,
    )

    if callable(fn):

        try:
            return fn(candidate)
        except Exception:
            pass

    return _provider(
        candidate
    )


def _media_type(candidate):

    fn = getattr(
        VSE,
        "media_type",
        None,
    )

    if callable(fn):

        try:
            return fn(candidate)
        except Exception:
            pass

    return _norm(
        _objget(
            candidate,
            [
                "type",
                "tipo",
                "media_type",
            ],
            "unknown",
        )
    )


def _candidate_key(candidate):

    fn = getattr(
        VSE,
        "candidate_key",
        None,
    )

    if callable(fn):

        try:
            return str(
                fn(candidate)
            )
        except Exception:
            pass


    return (
        _provider(candidate)
        + ":"
        + _media_type(candidate)
        + ":"
        + _candidate_text(candidate)
    )


def _must(candidate, scene):

    fn = getattr(
        VSE,
        "must_tier",
        None,
    )

    if callable(fn):

        try:
            return int(
                fn(
                    candidate,
                    scene,
                )
            )
        except TypeError:

            try:
                return int(
                    fn(candidate)
                )
            except Exception:
                pass

        except Exception:
            pass


    value = _objget(
        candidate,
        [
            "must_tier",
            "must",
            "must_score",
        ],
        0,
    )


    text = str(
        value
    )

    if text.startswith("2"):
        return 2

    if text.startswith("1"):
        return 1

    return 0


def _base(candidate):

    fn = getattr(
        VSE,
        "base_score",
        None,
    )

    if callable(fn):

        try:
            return float(
                fn(candidate)
            )
        except Exception:
            pass


    value = _objget(
        candidate,
        [
            "score",
            "base_score",
            "quality_score",
        ],
        0,
    )

    try:
        return float(value)
    except Exception:
        return 0.0


def _concept_hits(text):

    fn = getattr(
        VSE,
        "concept_hits",
        None,
    )

    if callable(fn):

        try:
            return set(
                fn(text)
            )
        except Exception:
            pass

    return set()


def _geo_hits(text):

    fn = getattr(
        VSE,
        "geo_hits",
        None,
    )

    if callable(fn):

        try:
            return set(
                fn(text)
            )
        except Exception:
            pass

    return set()


def _scene_text(local_context):

    if not isinstance(
        local_context,
        dict,
    ):

        return str(
            local_context or ""
        )


    positive_keys = (
        "busca",
        "query",
        "visual_query",
        "texto",
        "segmento",
        "scene",
        "cena",
        "must_have",
        "location",
        "local",
        "topic",
        "tema",
        "context",
        "narrative",
    )


    parts = []


    def add(value):

        if value is None:
            return

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                parts.append(value)

            return


        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            for item in value:
                add(item)

            return


        if isinstance(
            value,
            dict,
        ):

            for key in positive_keys:

                if key in value:
                    add(
                        value[key]
                    )

            return


        parts.append(
            str(value)
        )


    for key in positive_keys:

        if key in local_context:
            add(
                local_context[key]
            )


    return " ".join(
        parts
    ).strip()


def _diversity_adjust(candidate):

    provider = _provider(
        candidate
    )

    group = _source_group(
        candidate
    )

    media = _media_type(
        candidate
    )

    key = _candidate_key(
        candidate
    )


    penalty = 0.0


    # Exact candidate reuse is extremely undesirable.
    if key in _STATE["keys"]:
        penalty -= 200.0


    providers = _STATE[
        "providers"
    ]

    groups = _STATE[
        "groups"
    ]

    types = _STATE[
        "types"
    ]


    if providers:

        if providers[-1] == provider:
            penalty -= 10.0


        recent_count = sum(
            1
            for item in providers[-4:]
            if item == provider
        )

        penalty -= (
            recent_count
            *
            3.0
        )


    if groups and groups[-1] == group:
        penalty -= 6.0


    if (
        len(types) >= 3
        and
        all(
            item == media
            for item in types[-3:]
        )
    ):
        penalty -= 3.0


    return penalty


def _safety_adjust(
    candidate,
    scene_text,
):

    candidate_text = _candidate_text(
        candidate
    )

    scene_tokens = _tokens(
        scene_text
    )

    candidate_tokens = _tokens(
        candidate_text
    )


    hard = False
    penalty = 0.0
    reasons = []


    # ---------------------------------------------------------
    # GEOGRAPHY
    # ---------------------------------------------------------

    scene_geo = _geo_hits(
        scene_text
    )

    candidate_geo = _geo_hits(
        candidate_text
    )


    if (
        scene_geo
        and
        candidate_geo
        and
        scene_geo.isdisjoint(
            candidate_geo
        )
    ):

        hard = True
        penalty -= 500.0

        reasons.append(
            "GEO_CONTRADICTION"
        )


    # ---------------------------------------------------------
    # FALSE MEDICAL ASSOCIATION
    # ---------------------------------------------------------

    medicine_terms = set()

    for term in getattr(
        VSE,
        "MEDICINE_TERMS",
        set(),
    ):

        medicine_terms.update(
            _tokens(term)
        )


    candidate_medicine = bool(
        candidate_tokens
        &
        medicine_terms
    )

    scene_medicine = bool(
        scene_tokens
        &
        medicine_terms
    )


    documentary_medical_risk = bool(
        _concept_hits(
            scene_text
        )
        &
        {
            "investigation",
            "evidence",
            "forensics",
            "crime_scene",
            "police",
        }
    )


    if (
        candidate_medicine
        and
        not scene_medicine
        and
        documentary_medical_risk
    ):

        hard = True
        penalty -= 350.0

        reasons.append(
            "FALSE_MEDICAL_ASSOCIATION"
        )


    # ---------------------------------------------------------
    # GENERIC STOCK / LIFESTYLE
    # ---------------------------------------------------------

    generic_terms = set()

    for term in getattr(
        VSE,
        "GENERIC_LIFESTYLE",
        set(),
    ):

        generic_terms.update(
            _tokens(term)
        )


    generic_hits = (
        candidate_tokens
        &
        generic_terms
    )


    scene_concepts = _concept_hits(
        scene_text
    )

    candidate_concepts = _concept_hits(
        candidate_text
    )


    strong_documentary = {
        "police",
        "investigation",
        "crime_scene",
        "evidence",
        "forensics",
        "court",
        "prison",
        "law",
        "military",
        "war",
        "laboratory",
        "technology",
        "space",
        "hospital",
        "fire",
        "rescue",
    }


    if (
        generic_hits
        and
        scene_concepts
        &
        strong_documentary
    ):

        shared = (
            scene_concepts
            &
            candidate_concepts
        )


        if not shared:

            penalty -= 45.0

            reasons.append(
                "GENERIC_LIFESTYLE"
            )


    return {
        "hard":
            hard,

        "penalty":
            penalty,

        "reasons":
            reasons,

        "scene_geo":
            scene_geo,

        "candidate_geo":
            candidate_geo,
    }


def _score(
    candidate,
    scene_text,
):

    try:

        raw = VSE.score_candidate(
            candidate,
            scene_text,
            _STATE,
        )

        if not isinstance(
            raw,
            dict,
        ):
            raw = {}

    except Exception as exc:

        raw = {
            "bridge_error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
        }


    hard = bool(
        raw.get(
            "hard_mismatch",
            False,
        )
    )


    effective = raw.get(
        "effective",
        raw.get(
            "effective_score",
            raw.get(
                "score",
                _base(candidate),
            ),
        ),
    )


    try:
        effective = float(
            effective
        )
    except Exception:
        effective = _base(
            candidate
        )


    safety = _safety_adjust(
        candidate,
        scene_text,
    )


    if safety[
        "hard"
    ]:
        hard = True


    diversity = _diversity_adjust(
        candidate
    )


    adjusted = (
        effective
        +
        safety["penalty"]
        +
        diversity
    )


    return {
        "candidate":
            candidate,

        "key":
            _candidate_key(
                candidate
            ),

        "provider":
            _provider(
                candidate
            ),

        "group":
            _source_group(
                candidate
            ),

        "type":
            _media_type(
                candidate
            ),

        "must":
            _must(
                candidate,
                scene_text,
            ),

        "base":
            _base(
                candidate
            ),

        "effective":
            effective,

        "adjusted":
            adjusted,

        "hard":
            hard,

        "reasons":
            list(
                safety["reasons"]
            ),

        "raw":
            raw,
    }


def _flatten(value):

    fn = getattr(
        VSE,
        "flatten_candidates",
        None,
    )

    if callable(fn):

        try:
            return list(
                fn(value)
            )
        except Exception:
            pass


    result = []


    def walk(item):

        if item is None:
            return

        if isinstance(
            item,
            (
                list,
                tuple,
                set,
            ),
        ):

            for child in item:
                walk(child)

            return

        if isinstance(
            item,
            dict,
        ):

            candidate_fields = {
                "url",
                "source_url",
                "download_url",
                "provider",
                "title",
                "score",
                "tipo",
                "type",
                "id",
            }


            if (
                candidate_fields
                &
                set(item.keys())
            ):

                result.append(
                    item
                )

                return


            for child in item.values():
                walk(child)

            return


        result.append(
            item
        )


    walk(value)

    return result


def _unique(candidates):

    result = []
    seen = set()


    for candidate in candidates:

        if candidate is None:
            continue


        key = _candidate_key(
            candidate
        )


        if key in seen:
            continue


        seen.add(
            key
        )

        result.append(
            candidate
        )


    return result


def finalize_pool(
    pool,
    chosen,
    local_context=None,
):

    """
    Final authority immediately before download.

    Policy:
      HARD SAFETY > MUST > SEMANTICS > DIVERSITY.
    """

    candidates = _unique(
        (
            [chosen]
            if chosen is not None
            else []
        )
        +
        _flatten(pool)
    )


    if not candidates:
        return []


    if not enabled():

        if chosen is None:
            return candidates

        chosen_key = _candidate_key(
            chosen
        )

        return (
            [chosen]
            +
            [
                c
                for c in candidates
                if _candidate_key(c)
                !=
                chosen_key
            ]
        )


    scene_text = _scene_text(
        local_context or {}
    )


    reports = [
        _score(
            candidate,
            scene_text,
        )
        for candidate in candidates
    ]


    chosen_report = None

    if chosen is not None:

        chosen_key = _candidate_key(
            chosen
        )

        for report in reports:

            if (
                report["key"]
                ==
                chosen_key
            ):

                chosen_report = report
                break


    safe = [
        report
        for report in reports
        if not report[
            "hard"
        ]
    ]


    ranked = sorted(
        reports,
        key=lambda r: (
            0
            if r["hard"]
            else 1,

            r["must"],

            r["adjusted"],

            r["base"],
        ),
        reverse=True,
    )


    best_safe = (
        max(
            safe,
            key=lambda r: (
                r["must"],
                r["adjusted"],
                r["base"],
            ),
        )
        if safe
        else None
    )


    winner = (
        chosen_report
        if chosen_report is not None
        else ranked[0]
    )


    reason = (
        "REFERENCE_PRESERVED"
    )


    if (
        chosen_report is not None
        and
        chosen_report["hard"]
        and
        best_safe is not None
    ):

        winner = best_safe
        reason = (
            "HARD_MISMATCH_REJECTED"
        )


    elif (
        best_safe is not None
        and
        winner is not None
    ):

        if (
            best_safe["must"]
            >
            winner["must"]
        ):

            winner = best_safe
            reason = (
                "MUST_UPGRADE"
            )


        elif (
            best_safe["must"]
            ==
            winner["must"]
            and
            best_safe["adjusted"]
            >=
            winner["adjusted"]
            +
            8.0
        ):

            winner = best_safe
            reason = (
                "SEMANTIC_OR_DIVERSITY_UPGRADE"
            )


    winner_key = winner[
        "key"
    ]


    ordered = [
        winner[
            "candidate"
        ]
    ]


    for report in ranked:

        if (
            report["key"]
            ==
            winner_key
        ):
            continue

        ordered.append(
            report[
                "candidate"
            ]
        )


    provider_counts = {}

    for report in reports:

        p = report[
            "provider"
        ]

        provider_counts[
            p
        ] = (
            provider_counts.get(
                p,
                0,
            )
            +
            1
        )


    counts_text = ",".join(
        f"{key}:{value}"
        for key, value
        in sorted(
            provider_counts.items()
        )
    )


    print(
        "VSE42_FINAL_GATE=ACTIVE"
    )

    print(
        "VSE42_POOL_PROVIDERS="
        +
        counts_text
    )


    if chosen_report is not None:

        print(
            "VSE42_BEFORE="
            f"{chosen_report['provider']}/"
            f"{chosen_report['type']} "
            f"must={chosen_report['must']} "
            f"effective="
            f"{chosen_report['effective']:.1f} "
            f"adjusted="
            f"{chosen_report['adjusted']:.1f} "
            f"hard="
            f"{chosen_report['hard']}"
        )


    print(
        "VSE42_AFTER="
        f"{winner['provider']}/"
        f"{winner['type']} "
        f"must={winner['must']} "
        f"effective="
        f"{winner['effective']:.1f} "
        f"adjusted="
        f"{winner['adjusted']:.1f} "
        f"hard="
        f"{winner['hard']}"
    )


    print(
        "VSE42_REASON="
        +
        reason
    )


    if winner[
        "reasons"
    ]:

        print(
            "VSE42_SAFETY="
            +
            ",".join(
                winner[
                    "reasons"
                ]
            )
        )


    return ordered


def note_success(candidate):

    if not enabled():
        return


    values = {
        "providers":
            _provider(
                candidate
            ),

        "groups":
            _source_group(
                candidate
            ),

        "types":
            _media_type(
                candidate
            ),

        "keys":
            _candidate_key(
                candidate
            ),
    }


    for key, value in values.items():

        _STATE[
            key
        ].append(
            value
        )


    _trim_state()


    print(
        "VSE42_COMMIT="
        f"{values['providers']}/"
        f"{values['types']}"
    )


def commit_media(path):

    """
    After a successful scene download,
    keep exactly one media file for that scene.
    """

    if not enabled():
        return []


    if not path:
        return []


    try:

        current = Path(
            path
        ).resolve()

    except Exception:
        return []


    if not current.exists():
        return []


    try:

        root = ROOT.resolve()

        if (
            current != root
            and
            root not in current.parents
        ):
            return []

    except Exception:
        return []


    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
    }


    removed = []


    try:

        for sibling in current.parent.iterdir():

            if not sibling.is_file():
                continue


            if sibling == current:
                continue


            if (
                sibling.stem
                !=
                current.stem
            ):
                continue


            if (
                sibling.suffix.casefold()
                not in allowed
            ):
                continue


            try:

                sibling.unlink()

                removed.append(
                    str(sibling)
                )

            except Exception:
                pass

    except Exception:
        pass


    if removed:

        print(
            "VSE42_SIBLING_CLEANUP="
            +
            str(
                len(removed)
            )
        )


    return removed


def _best_safe_must(
    candidates,
    scene_text,
):

    best = 0


    for candidate in candidates:

        report = _score(
            candidate,
            scene_text,
        )


        if report[
            "hard"
        ]:
            continue


        best = max(
            best,
            report[
                "must"
            ],
        )


    return best


def install_search_rescue(namespace):

    """
    Wrap buscar_todos_candidatos.

    Only makes extra searches when:
      - current pool has no safe MUST 2
      - simplificar_busca exists
      - alternate query is genuinely different

    Kill switch:
      SAP_VSE42_RESCUE=0
    """

    function = namespace.get(
        "buscar_todos_candidatos"
    )


    if not callable(
        function
    ):
        return False


    if getattr(
        function,
        "_sap_vse42_wrapped",
        False,
    ):
        return True


    original = function


    try:
        signature = inspect.signature(
            original
        )
    except Exception:
        return False


    @functools.wraps(
        original
    )
    def wrapper(
        *args,
        **kwargs,
    ):

        result = original(
            *args,
            **kwargs,
        )


        if (
            not enabled()
            or
            os.getenv(
                "SAP_VSE42_RESCUE",
                "1",
            )
            ==
            "0"
        ):
            return result


        if not isinstance(
            result,
            (
                list,
                tuple,
            ),
        ):
            return result


        candidates = _unique(
            _flatten(
                result
            )
        )


        try:

            bound = signature.bind_partial(
                *args,
                **kwargs,
            )

        except Exception:
            return result


        arguments = bound.arguments


        search_name = None

        for name in (
            "busca",
            "query",
            "termo",
            "search",
        ):

            if name in arguments:

                search_name = name
                break


        if search_name is None:
            return result


        search_value = arguments[
            search_name
        ]


        must = None

        for name in (
            "must_have",
            "must",
            "obrigatorios",
        ):

            if name in arguments:

                must = arguments[
                    name
                ]

                break


        scene_context = {
            "busca":
                search_value,

            "must_have":
                must,
        }


        scene_text = _scene_text(
            scene_context
        )


        before_tier = _best_safe_must(
            candidates,
            scene_text,
        )


        if before_tier >= 2:
            return result


        simplifier = namespace.get(
            "simplificar_busca"
        )


        if not callable(
            simplifier
        ):
            return result


        try:

            alternate = simplifier(
                search_value,
                must,
            )

        except Exception:

            return result


        alternate_queries = []


        if isinstance(
            alternate,
            str,
        ):

            alternate_queries = [
                alternate
            ]


        elif isinstance(
            alternate,
            (
                list,
                tuple,
                set,
            ),
        ):

            alternate_queries = [
                str(item)
                for item in alternate
                if item
            ]


        original_norm = _norm(
            search_value
        )


        alternate_queries = [
            query.strip()
            for query in alternate_queries
            if (
                query
                and
                _norm(query)
                !=
                original_norm
            )
        ]


        alternate_queries = (
            alternate_queries[
                :2
            ]
        )


        if not alternate_queries:
            return result


        merged = list(
            candidates
        )


        print(
            "VSE42_MUST_RESCUE=START "
            f"tier={before_tier}"
        )


        for query in alternate_queries:

            print(
                "VSE42_MUST_RESCUE_QUERY="
                +
                query
            )


            try:

                alt_bound = (
                    signature.bind_partial(
                        *args,
                        **kwargs,
                    )
                )

                alt_bound.arguments[
                    search_name
                ] = query


                extra = original(
                    *alt_bound.args,
                    **alt_bound.kwargs,
                )


                merged.extend(
                    _flatten(
                        extra
                    )
                )

                merged = _unique(
                    merged
                )


                tier = _best_safe_must(
                    merged,
                    scene_text,
                )


                if tier >= 2:

                    print(
                        "VSE42_MUST_RESCUE=SUCCESS"
                    )

                    break


            except Exception as exc:

                print(
                    "VSE42_MUST_RESCUE_QUERY_ERROR="
                    f"{type(exc).__name__}"
                )


        merged = _unique(
            merged
        )


        if isinstance(
            result,
            tuple,
        ):
            return tuple(
                merged
            )


        return merged


    wrapper._sap_vse42_wrapped = True
    wrapper._sap_vse42_original = original


    namespace[
        "buscar_todos_candidatos"
    ] = wrapper


    print(
        "VSE42_SEARCH_RESCUE=INSTALLED"
    )


    return True


def debug_score(
    candidate,
    local_context,
):

    return _score(
        candidate,
        _scene_text(
            local_context
        ),
    )


__all__ = [
    "enabled",
    "reset_state",
    "finalize_pool",
    "note_success",
    "commit_media",
    "install_search_rescue",
    "debug_score",
]
