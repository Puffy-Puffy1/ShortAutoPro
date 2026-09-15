#!/usr/bin/env python3

import os

import visual_selection_engine_v4 as vse


_STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def _append_unique_history(
    bucket,
    value,
):

    if not value:
        return

    bucket.append(
        value
    )

    del bucket[:-16]


def note_committed(
    candidate,
):

    _append_unique_history(
        _STATE["providers"],
        vse.provider(candidate),
    )

    _append_unique_history(
        _STATE["groups"],
        vse.source_group(candidate),
    )

    _append_unique_history(
        _STATE["types"],
        vse.media_type(candidate),
    )

    _append_unique_history(
        _STATE["keys"],
        vse.candidate_key(candidate),
    )


def _context_from_locals(
    local_vars,
):

    parts = []

    preferred = (
        "scene",
        "cena",
        "scene_data",
        "cena_atual",
        "texto",
        "narracao",
        "narration",
        "busca",
        "query",
        "visual_query",
        "must_have",
        "location",
        "local",
    )


    for name in preferred:

        if name not in local_vars:
            continue

        value = local_vars.get(
            name
        )

        if value is None:
            continue

        if isinstance(
            value,
            (
                str,
                dict,
                list,
                tuple,
                set,
            ),
        ):
            parts.append(
                value
            )


    if not parts:

        # Conservative fallback:
        # use only semantically named locals.
        for name, value in local_vars.items():

            lname = str(name).casefold()

            if not any(
                marker in lname
                for marker in (
                    "scene",
                    "cena",
                    "busca",
                    "query",
                    "must",
                    "location",
                    "texto",
                    "narr",
                )
            ):
                continue

            if isinstance(
                value,
                (
                    str,
                    dict,
                    list,
                    tuple,
                    set,
                ),
            ):
                parts.append(
                    value
                )


    return {
        "texto":
            " | ".join(
                vse.candidate_text(x)
                for x in parts
                if vse.candidate_text(x)
            )
    }


def _candidate_list(
    pool,
    reference,
):

    all_items = []

    if reference is not None:
        all_items.append(
            reference
        )

    all_items.extend(
        vse.flatten_candidates(
            pool
        )
    )

    result = []
    seen = set()

    for candidate in all_items:

        key = vse.candidate_key(
            candidate
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(
            candidate
        )

    return result


def choose_from_locals(
    pool,
    reference,
    local_vars,
):

    if (
        os.getenv(
            "SAP_VSE4_RUNTIME",
            "1",
        )
        !=
        "1"
    ):
        return reference, {
            "reason":
                "DISABLED"
        }


    scene = _context_from_locals(
        local_vars
    )

    candidates = _candidate_list(
        pool,
        reference,
    )

    if not candidates:
        return reference, {
            "reason":
                "EMPTY_POOL"
        }


    scored = []

    for candidate in candidates:

        try:

            result = vse.score_candidate(
                candidate,
                scene,
                _STATE,
            )

        except Exception as exc:

            print(
                "VSE42_SCORE_FAIL_OPEN="
                f"{type(exc).__name__}:"
                f"{exc}"
            )

            continue

        scored.append(
            (
                candidate,
                result,
            )
        )


    if not scored:
        return reference, {
            "reason":
                "NO_SCORABLE_CANDIDATES"
        }


    reference_result = None

    reference_key = (
        vse.candidate_key(reference)
        if reference is not None
        else None
    )


    for candidate, result in scored:

        if (
            reference_key
            and
            vse.candidate_key(candidate)
            ==
            reference_key
        ):
            reference_result = result
            break


    def order(item):

        candidate, result = item

        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )

        must = vse.must_tier(
            candidate,
            scene,
        )

        effective = float(
            result.get(
                "effective",
                -1000000,
            )
        )

        return (
            not hard,
            must,
            effective,
        )


    ranked = sorted(
        scored,
        key=order,
        reverse=True,
    )


    best_candidate, best_result = (
        ranked[0]
    )


    if reference is None:

        return best_candidate, {
            "reason":
                "NO_REFERENCE",

            "best":
                best_result,
        }


    if reference_result is None:

        return best_candidate, {
            "reason":
                "REFERENCE_NOT_SCORABLE",

            "best":
                best_result,
        }


    ref_hard = bool(
        reference_result.get(
            "hard_mismatch",
            False,
        )
    )

    best_hard = bool(
        best_result.get(
            "hard_mismatch",
            False,
        )
    )


    ref_must = vse.must_tier(
        reference,
        scene,
    )

    best_must = vse.must_tier(
        best_candidate,
        scene,
    )


    ref_effective = float(
        reference_result.get(
            "effective",
            -1000000,
        )
    )

    best_effective = float(
        best_result.get(
            "effective",
            -1000000,
        )
    )


    # Truth dominates MUST.
    if ref_hard and not best_hard:

        reason = (
            "REPLACE_HARD_MISMATCH"
        )

        winner = best_candidate


    # Never voluntarily replace safe candidate with hard mismatch.
    elif best_hard:

        reason = (
            "KEEP_SAFE_REFERENCE"
        )

        winner = reference


    # Better MUST tier.
    elif best_must > ref_must:

        reason = (
            "UPGRADE_MUST"
        )

        winner = best_candidate


    # Never downgrade MUST unless reference is factually wrong.
    elif best_must < ref_must:

        reason = (
            "PRESERVE_MUST_TIER"
        )

        winner = reference


    # Same tier: require material improvement.
    elif (
        best_effective
        >=
        ref_effective + 8.0
    ):

        reason = (
            "SAME_TIER_QUALITY_UPGRADE"
        )

        winner = best_candidate


    else:

        reason = (
            "REFERENCE_STILL_BEST"
        )

        winner = reference


    telemetry = {

        "reason":
            reason,

        "reference_must":
            ref_must,

        "best_must":
            best_must,

        "reference_effective":
            ref_effective,

        "best_effective":
            best_effective,

        "reference_hard":
            ref_hard,

        "best_hard":
            best_hard,

        "pool_size":
            len(candidates),
    }


    print(
        "VSE42_RUNTIME_DECISION="
        f"{reason}"
    )

    print(
        "VSE42_REFERENCE="
        f"must={ref_must} "
        f"effective={ref_effective:.1f} "
        f"hard={ref_hard}"
    )

    print(
        "VSE42_BEST="
        f"must={best_must} "
        f"effective={best_effective:.1f} "
        f"hard={best_hard}"
    )


    return winner, telemetry


def state_snapshot():

    return {
        key:
            list(value)
        for key, value
        in _STATE.items()
    }
