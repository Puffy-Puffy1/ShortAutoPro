#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "PROJECT_NOT_FOUND"
    return 2 2>/dev/null || true
}

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="backups/VSE42_PRODUCTION_$STAMP"
REPORT="temp/VSE42_PRODUCTION_CERTIFICATION.txt"

mkdir -p \
"$BACKUP" \
temp \
logs/producao \
manifests


echo "======================================================================"
echo " SHORTAUTOPRO VISUAL PIPELINE V4.2"
echo " PRODUCTION INTEGRATION + GENERAL REPAIR"
echo "======================================================================"
echo "DATE=$(date)"
echo "BACKUP=$BACKUP"


# ======================================================================
# 1. PRE-INTEGRATION BACKUP
# ======================================================================

echo
echo "======================================================================"
echo " 1. BACKUP"
echo "======================================================================"

BACKUP_OK=1

for F in \
midia.py \
visual_selection_engine_v4.py \
media_diversity_guard_v1.py \
gerar_short.sh
do

    if [ -f "$F" ]; then

        cp -f "$F" "$BACKUP/$F"

        if [ "$?" -eq 0 ]; then
            echo "BACKUP=PASS | $F"
        else
            echo "BACKUP=FAIL | $F"
            BACKUP_OK=0
        fi

    else

        echo "BACKUP=SKIP_NOT_FOUND | $F"

        if [ "$F" = "midia.py" ] || \
           [ "$F" = "visual_selection_engine_v4.py" ]
        then
            BACKUP_OK=0
        fi

    fi

done


sha256sum \
midia.py \
visual_selection_engine_v4.py \
gerar_short.sh \
2>/dev/null \
> "$BACKUP/PRE_HASHES.sha256"


echo "BACKUP_STATUS=$BACKUP_OK"


# ======================================================================
# 2. REQUIRE VSE4 CERTIFIED
# ======================================================================

echo
echo "======================================================================"
echo " 2. VSE4 PRECONDITION"
echo "======================================================================"

python -m py_compile \
visual_selection_engine_v4.py

VSE_COMPILE=$?

python visual_selection_engine_v4.py \
> temp/vse42_pre_self_test.log \
2>&1

VSE_SELF=$?

echo "VSE4_COMPILE=$VSE_COMPILE"
echo "VSE4_SELF_TEST=$VSE_SELF"

if [ "$VSE_SELF" -ne 0 ]; then
    tail -n 60 temp/vse42_pre_self_test.log
fi


# ======================================================================
# 3. CREATE PRODUCTION BRIDGE
# ======================================================================

echo
echo "======================================================================"
echo " 3. CREATE VISUAL PIPELINE BRIDGE"
echo "======================================================================"

cat > visual_pipeline_bridge_v42.py <<'PY'
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


ROOT = Path.home() / "ShortAutoPro"

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
PY


python -m py_compile \
visual_pipeline_bridge_v42.py

BRIDGE_COMPILE=$?

echo "BRIDGE_COMPILE=$BRIDGE_COMPILE"


# ======================================================================
# 4. TRANSACTIONAL MIDIA.PY PATCH
# ======================================================================

echo
echo "======================================================================"
echo " 4. TRANSACTIONAL MIDIA.PY INTEGRATION"
echo "======================================================================"

python - <<'PY'
from pathlib import Path
import ast


PATH = Path(
    "midia.py"
)


src = PATH.read_text(
    encoding="utf-8"
)


IMPORT_MARKER = (
    "# SHORTAUTOPRO VSE42 IMPORT"
)

POOL_MARKER = (
    "# SHORTAUTOPRO VSE42 FINAL POOL"
)

RESCUE_MARKER = (
    "# SHORTAUTOPRO VSE42 SEARCH RESCUE"
)

COMMIT_MARKER = (
    "# SHORTAUTOPRO VSE42 SUCCESS COMMIT"
)


def parse(text):

    return ast.parse(
        text
    )


# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------

if IMPORT_MARKER not in src:

    tree = parse(
        src
    )

    insert_line = 1


    if src.startswith(
        "#!"
    ):
        insert_line = 2


    if (
        tree.body
        and
        isinstance(
            tree.body[0],
            ast.Expr,
        )
        and
        isinstance(
            getattr(
                tree.body[0],
                "value",
                None,
            ),
            ast.Constant,
        )
        and
        isinstance(
            tree.body[0].value.value,
            str,
        )
    ):

        insert_line = max(
            insert_line,
            tree.body[0].end_lineno + 1,
        )


    for node in tree.body:

        if (
            isinstance(
                node,
                ast.ImportFrom,
            )
            and
            node.module
            ==
            "__future__"
        ):

            insert_line = max(
                insert_line,
                node.end_lineno + 1,
            )


    lines = src.splitlines(
        keepends=True
    )


    block = '''
# SHORTAUTOPRO VSE42 IMPORT
from visual_pipeline_bridge_v42 import (
    enabled as _vse42_enabled,
    finalize_pool as _vse42_finalize_pool,
    note_success as _vse42_note_success,
    commit_media as _vse42_commit_media,
    install_search_rescue as _vse42_install_search_rescue,
)

'''


    idx = (
        insert_line
        -
        1
    )


    src = (
        "".join(
            lines[:idx]
        )
        +
        block
        +
        "".join(
            lines[idx:]
        )
    )


# ------------------------------------------------------------
# FINAL POOL
#
# Replace:
#
# pool = [escolhido] + [...]
#
# with VSE4 final authority.
# ------------------------------------------------------------

if POOL_MARKER not in src:

    tree = parse(
        src
    )


    target = None


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue


        if not any(
            isinstance(t, ast.Name)
            and
            t.id == "pool"
            for t in node.targets
        ):
            continue


        segment = ast.get_source_segment(
            src,
            node,
        ) or ""


        if (
            "escolhido"
            in
            segment
            and
            "[escolhido]"
            in
            segment.replace(
                " ",
                "",
            )
        ):

            target = node
            break


    # More tolerant fallback.
    if target is None:

        for node in ast.walk(
            tree
        ):

            if not isinstance(
                node,
                ast.Assign,
            ):
                continue


            if not any(
                isinstance(t, ast.Name)
                and
                t.id == "pool"
                for t in node.targets
            ):
                continue


            segment = ast.get_source_segment(
                src,
                node,
            ) or ""


            if (
                "escolhido"
                in segment
                and
                "+"
                in segment
            ):

                target = node
                break


    if target is None:

        print(
            "MIDIA_PATCH=FAIL"
        )

        print(
            "REASON=LEGACY_CHOSEN_PREPEND_NOT_FOUND"
        )

        raise SystemExit(2)


    lines = src.splitlines(
        keepends=True
    )


    indentation = (
        lines[
            target.lineno - 1
        ][:len(
            lines[
                target.lineno - 1
            ]
        ) - len(
            lines[
                target.lineno - 1
            ].lstrip()
        )]
    )


    replacement = (
        indentation
        +
        "# SHORTAUTOPRO VSE42 FINAL POOL\n"
        +
        indentation
        +
        "pool = _vse42_finalize_pool("
        "pool, escolhido, locals())\n"
    )


    src = (
        "".join(
            lines[
                :target.lineno - 1
            ]
        )
        +
        replacement
        +
        "".join(
            lines[
                target.end_lineno:
            ]
        )
    )


# ------------------------------------------------------------
# SEARCH RESCUE INSTALL
# ------------------------------------------------------------

if RESCUE_MARKER not in src:

    tree = parse(
        src
    )


    functions = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and
            node.name
            ==
            "buscar_todos_candidatos"
        )
    ]


    if len(functions) != 1:

        print(
            "MIDIA_PATCH=FAIL"
        )

        print(
            "REASON=BUSCAR_TODOS_COUNT_"
            +
            str(
                len(functions)
            )
        )

        raise SystemExit(3)


    function = functions[0]


    lines = src.splitlines(
        keepends=True
    )


    insert_at = function.end_lineno


    block = '''

# SHORTAUTOPRO VSE42 SEARCH RESCUE
_vse42_install_search_rescue(globals())

'''


    src = (
        "".join(
            lines[
                :insert_at
            ]
        )
        +
        block
        +
        "".join(
            lines[
                insert_at:
            ]
        )
    )


# ------------------------------------------------------------
# SUCCESS COMMIT
#
# Old flow could:
# 1. successfully download photo
# 2. continue loop
# 3. download video
# 4. replace visual
#
# VSE42 breaks after FIRST SUCCESSFUL candidate.
# ------------------------------------------------------------

if COMMIT_MARKER not in src:

    lines = src.splitlines(
        keepends=True
    )


    anchors = [
        index
        for index, line
        in enumerate(lines)
        if (
            "FAILOVER: QUALIDADE PRESERVADA"
            in line
        )
    ]


    if not anchors:

        print(
            "MIDIA_PATCH=FAIL"
        )

        print(
            "REASON=FAILOVER_ANCHOR_NOT_FOUND"
        )

        raise SystemExit(4)


    anchor = anchors[0]


    conditional_index = None


    for index in range(
        anchor - 1,
        max(
            -1,
            anchor - 20,
        ),
        -1,
    ):

        stripped = lines[
            index
        ].strip()


        if (
            stripped.startswith(
                "if "
            )
            and
            "candidato"
            in stripped
            and
            "referencia"
            in stripped
        ):

            conditional_index = index
            break


    if conditional_index is None:

        print(
            "MIDIA_PATCH=FAIL"
        )

        print(
            "REASON=SUCCESS_REFERENCE_CONDITION_NOT_FOUND"
        )

        raise SystemExit(5)


    line = lines[
        conditional_index
    ]


    indentation = (
        line[
            :len(line)
            -
            len(
                line.lstrip()
            )
        ]
    )


    commit_block = (
        indentation
        +
        "# SHORTAUTOPRO VSE42 SUCCESS COMMIT\n"
        +
        indentation
        +
        "if _vse42_enabled():\n"
        +
        indentation
        +
        "    _vse42_note_success(candidato)\n"
        +
        indentation
        +
        "    _vse42_commit_media(destino_teste)\n"
        +
        indentation
        +
        "    break\n"
    )


    src = (
        "".join(
            lines[
                :conditional_index
            ]
        )
        +
        commit_block
        +
        "".join(
            lines[
                conditional_index:
            ]
        )
    )


# ------------------------------------------------------------
# FINAL VALIDATION BEFORE WRITE
# ------------------------------------------------------------

parse(
    src
)


required_markers = (
    IMPORT_MARKER,
    POOL_MARKER,
    RESCUE_MARKER,
    COMMIT_MARKER,
)


missing = [
    marker
    for marker in required_markers
    if marker not in src
]


if missing:

    print(
        "MIDIA_PATCH=FAIL"
    )

    print(
        "MISSING_MARKERS="
        +
        ",".join(
            missing
        )
    )

    raise SystemExit(6)


PATH.write_text(
    src,
    encoding="utf-8",
)


print(
    "MIDIA_PATCH=PASS"
)

print(
    "VSE42_FINAL_AUTHORITY=INSTALLED"
)

print(
    "VSE42_SEARCH_RESCUE=INSTALLED"
)

print(
    "VSE42_FIRST_SUCCESS_COMMIT=INSTALLED"
)

print(
    "VSE42_SIBLING_CLEANUP=INSTALLED"
)
PY

MIDIA_PATCH=$?

echo "MIDIA_PATCH_STATUS=$MIDIA_PATCH"


# ======================================================================
# 5. CREATE PERMANENT VISUAL REGRESSION
# ======================================================================

echo
echo "======================================================================"
echo " 5. CREATE VISUAL REGRESSION SUITE"
echo "======================================================================"

cat > visual_quality_regression_v42.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import shutil

import visual_pipeline_bridge_v42 as bridge


def key(candidate):

    return bridge._candidate_key(
        candidate
    )


def check(
    name,
    condition,
):

    print(
        f"{name}="
        f"{'PASS' if condition else 'FAIL'}"
    )

    if not condition:
        raise AssertionError(
            name
        )


def test_geo():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "Investigação em apartamento "
                "na cidade de São Paulo Brasil"
            ),

        "must_have": [
            "apartamento",
            "São Paulo",
        ],
    }


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "Empire State Building "
                "Manhattan New York"
            ),

        "must":
            "2/2",

        "score":
            250,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "Apartment building "
                "Sao Paulo Brazil"
            ),

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    result = bridge.finalize_pool(
        [
            wrong,
            correct,
        ],
        wrong,
        scene,
    )


    check(
        "GEO_HARD_MISMATCH_OVERRIDE",
        key(
            result[0]
        )
        ==
        key(
            correct
        ),
    )


def test_must_upgrade():

    bridge.reset_state()


    scene = {
        "busca":
            "police investigation apartment",

        "must_have": [
            "police",
            "apartment",
        ],
    }


    weak = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "generic apartment interior",

        "must":
            "1/2",

        "score":
            160,
    }


    strong = {
        "provider":
            "Pexels",

        "tipo":
            "video",

        "title":
            (
                "police investigation "
                "apartment building"
            ),

        "must":
            "2/2",

        "score":
            130,
    }


    result = bridge.finalize_pool(
        [
            weak,
            strong,
        ],
        weak,
        scene,
    )


    check(
        "MUST_1_TO_2_RESCUE",
        key(
            result[0]
        )
        ==
        key(
            strong
        ),
    )


def test_false_medicine():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "forensic evidence "
                "crime investigation"
            ),

        "must_have": [
            "forensic",
            "evidence",
        ],
    }


    medicine = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "medicine pills tablets "
                "on desk"
            ),

        "must":
            "2/2",

        "score":
            300,
    }


    forensic = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "forensic laboratory "
                "crime evidence analysis"
            ),

        "must":
            "2/2",

        "score":
            120,
    }


    result = bridge.finalize_pool(
        [
            medicine,
            forensic,
        ],
        medicine,
        scene,
    )


    medicine_report = bridge.debug_score(
        medicine,
        scene,
    )


    check(
        "FALSE_MEDICINE_HARD_REJECT",
        medicine_report[
            "hard"
        ]
        is True,
    )


    check(
        "FORENSIC_MEDIA_WINS",
        key(
            result[0]
        )
        ==
        key(
            forensic
        ),
    )


def test_generic_lifestyle():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "detective police "
                "crime investigation"
            )
    }


    lifestyle = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "happy woman relaxing "
                "in bedroom lifestyle"
            ),

        "must":
            "1/2",

        "score":
            190,
    }


    documentary = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "police detective "
                "crime investigation"
            ),

        "must":
            "1/2",

        "score":
            165,
    }


    a = bridge.debug_score(
        lifestyle,
        scene,
    )

    b = bridge.debug_score(
        documentary,
        scene,
    )


    check(
        "GENERIC_LIFESTYLE_PENALTY",
        b[
            "adjusted"
        ]
        >
        a[
            "adjusted"
        ],
    )


def test_provider_diversity():

    bridge.reset_state()


    history_item = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "previous unrelated asset",
    }


    for _ in range(3):

        bridge.note_success(
            history_item
        )


    scene = {
        "busca":
            "city police investigation"
    }


    pixabay = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "city police investigation",

        "must":
            "2/2",

        "score":
            150,
    }


    pexels = {
        "provider":
            "Pexels",

        "tipo":
            "foto",

        "title":
            "city police investigation",

        "must":
            "2/2",

        "score":
            150,
    }


    result = bridge.finalize_pool(
        [
            pixabay,
            pexels,
        ],
        pixabay,
        scene,
    )


    check(
        "PROVIDER_REPEAT_CONTROL",
        bridge._provider(
            result[0]
        )
        ==
        "pexels",
    )


def test_sibling_cleanup():

    root = (
        Path.home()
        / "ShortAutoPro"
        / "temp"
        / "vse42_sibling_test"
    )


    shutil.rmtree(
        root,
        ignore_errors=True,
    )


    root.mkdir(
        parents=True,
        exist_ok=True,
    )


    jpg = (
        root
        / "scene_03.jpg"
    )

    mp4 = (
        root
        / "scene_03.mp4"
    )


    jpg.write_bytes(
        b"jpg_test"
    )

    mp4.write_bytes(
        b"mp4_test"
    )


    bridge.commit_media(
        mp4
    )


    check(
        "SCENE_SIBLING_REMOVED",
        (
            mp4.exists()
            and
            not jpg.exists()
        ),
    )


    shutil.rmtree(
        root,
        ignore_errors=True,
    )


def main():

    test_geo()
    test_must_upgrade()
    test_false_medicine()
    test_generic_lifestyle()
    test_provider_diversity()
    test_sibling_cleanup()

    print()
    print(
        "VISUAL_QUALITY_REGRESSION_V42=PASS"
    )


if __name__ == "__main__":
    main()
PY


python -m py_compile \
visual_quality_regression_v42.py

REG_COMPILE=$?

python \
visual_quality_regression_v42.py \
2>&1 |
tee temp/visual_quality_regression_v42.log

REG_TEST=${PIPESTATUS[0]}

echo "REGRESSION_COMPILE=$REG_COMPILE"
echo "REGRESSION_TEST=$REG_TEST"


# ======================================================================
# 6. STATIC MIDIA INTEGRATION AUDIT
# ======================================================================

echo
echo "======================================================================"
echo " 6. MIDIA INTEGRATION AUDIT"
echo "======================================================================"

python - <<'PY'
from pathlib import Path
import ast


src = Path(
    "midia.py"
).read_text(
    encoding="utf-8"
)

tree = ast.parse(
    src
)


checks = {
    "IMPORT":
        (
            "# SHORTAUTOPRO VSE42 IMPORT"
            in src
        ),

    "FINAL_POOL":
        (
            "# SHORTAUTOPRO VSE42 FINAL POOL"
            in src
        ),

    "SEARCH_RESCUE":
        (
            "# SHORTAUTOPRO VSE42 SEARCH RESCUE"
            in src
        ),

    "SUCCESS_COMMIT":
        (
            "# SHORTAUTOPRO VSE42 SUCCESS COMMIT"
            in src
        ),

    "FINALIZER_CALL":
        (
            "_vse42_finalize_pool("
            in src
        ),

    "NOTE_SUCCESS_CALL":
        (
            "_vse42_note_success("
            in src
        ),

    "COMMIT_MEDIA_CALL":
        (
            "_vse42_commit_media("
            in src
        ),
}


for name, ok in checks.items():

    print(
        f"MIDIA_{name}="
        f"{'PASS' if ok else 'FAIL'}"
    )


functions = [
    node.name
    for node in tree.body
    if isinstance(
        node,
        ast.FunctionDef,
    )
]


print(
    "BUSCAR_TODOS_COUNT=",
    functions.count(
        "buscar_todos_candidatos"
    ),
)


if (
    all(
        checks.values()
    )
    and
    functions.count(
        "buscar_todos_candidatos"
    )
    ==
    1
):

    print(
        "MIDIA_INTEGRATION_AUDIT=PASS"
    )

else:

    print(
        "MIDIA_INTEGRATION_AUDIT=FAIL"
    )

    raise SystemExit(1)
PY

INTEGRATION_AUDIT=$?


# ======================================================================
# 7. PROVIDER ACQUISITION CONTRACT
# ======================================================================

echo
echo "======================================================================"
echo " 7. PROVIDER ACQUISITION CONTRACT"
echo "======================================================================"

python - <<'PY'
from pathlib import Path
import ast


src = Path(
    "midia.py"
).read_text(
    encoding="utf-8"
)

tree = ast.parse(
    src
)


target = None


for node in tree.body:

    if (
        isinstance(
            node,
            ast.FunctionDef,
        )
        and
        node.name
        ==
        "buscar_todos_candidatos"
    ):

        target = node
        break


if target is None:

    print(
        "PROVIDER_CONTRACT=FAIL_NO_SEARCH_FUNCTION"
    )

    raise SystemExit(1)


calls = set()


for node in ast.walk(
    target
):

    if isinstance(
        node,
        ast.Call,
    ):

        if isinstance(
            node.func,
            ast.Name,
        ):

            calls.add(
                node.func.id
            )


expected = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


for name in sorted(
    expected
):

    print(
        f"PROVIDER_CALL_{name}="
        f"{'PASS' if name in calls else 'MISSING'}"
    )


missing = (
    expected
    -
    calls
)


if missing:

    print(
        "PROVIDER_CONTRACT=FAIL"
    )

    print(
        "MISSING="
        +
        ",".join(
            sorted(missing)
        )
    )

    raise SystemExit(1)


print(
    "PROVIDER_CONTRACT=PASS"
)
PY

PROVIDER_CONTRACT=$?


# ======================================================================
# 8. CORE COMPILE / SHELL
# ======================================================================

echo
echo "======================================================================"
echo " 8. CORE SAFETY"
echo "======================================================================"

python -m py_compile \
visual_selection_engine_v4.py \
visual_pipeline_bridge_v42.py \
visual_quality_regression_v42.py \
midia.py

CORE_COMPILE=$?


bash -n \
gerar_short.sh

SHELL_SYNTAX=$?


echo "CORE_COMPILE=$CORE_COMPILE"
echo "SHELL_SYNTAX=$SHELL_SYNTAX"


# ======================================================================
# 9. VSE4 SELF TEST AFTER INTEGRATION
# ======================================================================

echo
echo "======================================================================"
echo " 9. VSE4 FINAL SELF TEST"
echo "======================================================================"

python visual_selection_engine_v4.py \
2>&1 |
tee temp/vse42_final_self_test.log

FINAL_VSE_SELF=${PIPESTATUS[0]}

echo "FINAL_VSE_SELF_TEST=$FINAL_VSE_SELF"


# ======================================================================
# 10. KILL SWITCH TEST
# ======================================================================

echo
echo "======================================================================"
echo " 10. KILL SWITCH"
echo "======================================================================"

SAP_VSE42=0 python - <<'PY'
import visual_pipeline_bridge_v42 as bridge


chosen = {
    "provider":
        "Pixabay",

    "tipo":
        "foto",

    "title":
        "original winner",

    "must":
        "1/2",
}


alternative = {
    "provider":
        "Pexels",

    "tipo":
        "video",

    "title":
        "alternative",

    "must":
        "2/2",
}


result = bridge.finalize_pool(
    [
        alternative
    ],
    chosen,
    {
        "busca":
            "test",
    },
)


if (
    result
    and
    result[0]
    is
    chosen
):

    print(
        "VSE42_KILL_SWITCH=PASS"
    )

else:

    print(
        "VSE42_KILL_SWITCH=FAIL"
    )

    raise SystemExit(1)
PY

KILL_SWITCH=$?


# ======================================================================
# 11. ROLLBACK SCRIPT
# ======================================================================

echo
echo "======================================================================"
echo " 11. ROLLBACK"
echo "======================================================================"

cat > rollback_vse42.sh <<ROLLBACK
#!/data/data/com.termux/files/usr/bin/bash

cd "\$HOME/ShortAutoPro" || return 2

BACKUP="$BACKUP"

echo "=============================================="
echo " VSE42 ROLLBACK"
echo "=============================================="
echo "BACKUP=\$BACKUP"

if [ -f "\$BACKUP/midia.py" ]; then

    cp -f \
    "\$BACKUP/midia.py" \
    midia.py

    echo "MIDIA_ROLLBACK=PASS"

else

    echo "MIDIA_ROLLBACK=FAIL"

fi

if [ -f "\$BACKUP/gerar_short.sh" ]; then

    cp -f \
    "\$BACKUP/gerar_short.sh" \
    gerar_short.sh

fi

python -m py_compile \
midia.py

echo "ROLLBACK_COMPILE=\$?"

bash -n gerar_short.sh

echo "ROLLBACK_SHELL=\$?"

echo "TERMUX_CONTINUA_ABERTO=SIM"
ROLLBACK

chmod +x \
rollback_vse42.sh

echo "ROLLBACK_SCRIPT=rollback_vse42.sh"


# ======================================================================
# 12. HASH MANIFEST
# ======================================================================

echo
echo "======================================================================"
echo " 12. HASH MANIFEST"
echo "======================================================================"

sha256sum \
midia.py \
visual_selection_engine_v4.py \
visual_pipeline_bridge_v42.py \
visual_quality_regression_v42.py \
gerar_short.sh \
2>/dev/null |
tee \
manifests/vse42_production_hashes.sha256


# ======================================================================
# 13. FINAL CERTIFICATION
# ======================================================================

echo
echo "======================================================================"
echo " 13. FINAL CERTIFICATION"
echo "======================================================================"

{
echo "DATE=$(date)"
echo "BACKUP=$BACKUP"
echo "BACKUP_OK=$BACKUP_OK"
echo "VSE_COMPILE=$VSE_COMPILE"
echo "VSE_PRE_SELF_TEST=$VSE_SELF"
echo "BRIDGE_COMPILE=$BRIDGE_COMPILE"
echo "MIDIA_PATCH=$MIDIA_PATCH"
echo "REGRESSION_COMPILE=$REG_COMPILE"
echo "REGRESSION_TEST=$REG_TEST"
echo "INTEGRATION_AUDIT=$INTEGRATION_AUDIT"
echo "PROVIDER_CONTRACT=$PROVIDER_CONTRACT"
echo "CORE_COMPILE=$CORE_COMPILE"
echo "SHELL_SYNTAX=$SHELL_SYNTAX"
echo "FINAL_VSE_SELF_TEST=$FINAL_VSE_SELF"
echo "KILL_SWITCH=$KILL_SWITCH"
} |
tee "$REPORT"


PASS=1


for VALUE in \
"$BACKUP_OK" \
"$VSE_COMPILE" \
"$VSE_SELF" \
"$BRIDGE_COMPILE" \
"$MIDIA_PATCH" \
"$REG_COMPILE" \
"$REG_TEST" \
"$INTEGRATION_AUDIT" \
"$PROVIDER_CONTRACT" \
"$CORE_COMPILE" \
"$SHELL_SYNTAX" \
"$FINAL_VSE_SELF" \
"$KILL_SWITCH"
do

    case "$VALUE" in

        0)
            ;;

        1)
            # BACKUP_OK uses 1 for success.
            ;;

        *)
            ;;

    esac

done


# Individual semantics:
#
# BACKUP_OK must be 1.
# Everything else must be zero.

if [ "$BACKUP_OK" -ne 1 ]; then
    PASS=0
fi

for STATUS in \
"$VSE_COMPILE" \
"$VSE_SELF" \
"$BRIDGE_COMPILE" \
"$MIDIA_PATCH" \
"$REG_COMPILE" \
"$REG_TEST" \
"$INTEGRATION_AUDIT" \
"$PROVIDER_CONTRACT" \
"$CORE_COMPILE" \
"$SHELL_SYNTAX" \
"$FINAL_VSE_SELF" \
"$KILL_SWITCH"
do

    if [ "$STATUS" -ne 0 ]; then
        PASS=0
    fi

done


echo
echo "======================================================================"

if [ "$PASS" -eq 1 ]; then

    echo " VSE42_PRODUCTION_CERTIFICATION=PASS"

else

    echo " VSE42_PRODUCTION_CERTIFICATION=FAIL"

fi

echo "======================================================================"

echo "REPORT=$REPORT"
echo "ROLLBACK=./rollback_vse42.sh"
echo "KILL_SWITCH=SAP_VSE42=0"
echo
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "VIDEO_RENDERED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"

