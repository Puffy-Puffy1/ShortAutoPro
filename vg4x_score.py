#!/usr/bin/env python3

import os
from collections import Counter

from vg4x_common import (
    ABSTRACT_TERMS,
    DOCUMENTARY_CONCEPTS,
    GENERIC_LIFESTYLE,
    MEDICINE_TERMS,
    avoid_hits,
    base_score,
    candidate_key,
    candidate_text,
    concept_hits,
    geo_conflict,
    geo_hits,
    media_type,
    must_info,
    norm,
    objget,
    provider,
    resolution_bonus,
    scene_text,
    source_group,
    term_hits,
    tokens,
)


_RUNTIME_STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def enabled():
    return (
        os.getenv(
            "SAP_VG4X",
            "1",
        )
        !=
        "0"
    )


def reset_state():

    for key in _RUNTIME_STATE:
        _RUNTIME_STATE[key].clear()


def runtime_state():
    return _RUNTIME_STATE


def note_selection(candidate):

    if candidate is None:
        return

    _RUNTIME_STATE[
        "providers"
    ].append(
        provider(candidate)
    )

    _RUNTIME_STATE[
        "groups"
    ].append(
        source_group(candidate)
    )

    _RUNTIME_STATE[
        "types"
    ].append(
        media_type(candidate)
    )

    _RUNTIME_STATE[
        "keys"
    ].append(
        candidate_key(candidate)
    )


def diversity_adjustment(
    candidate,
    state,
):

    state = (
        state
        if isinstance(state, dict)
        else _RUNTIME_STATE
    )

    p = provider(candidate)
    g = source_group(candidate)
    t = media_type(candidate)
    k = candidate_key(candidate)

    providers = list(
        state.get(
            "providers",
            [],
        )
    )

    groups = list(
        state.get(
            "groups",
            [],
        )
    )

    types = list(
        state.get(
            "types",
            [],
        )
    )

    keys = list(
        state.get(
            "keys",
            [],
        )
    )

    value = 0.0

    pcount = providers.count(p)
    gcount = groups.count(g)

    if providers:

        if providers[-1] == p:
            value -= 14

        if pcount:
            value -= min(
                30,
                pcount * 4,
            )
        else:
            value += 8

    if groups:

        if groups[-1] == g:
            value -= 10

        value -= min(
            20,
            gcount * 3,
        )

    if types:

        if types[-1] == t:
            value -= 4
        else:
            value += 4

    if k in keys:
        value -= 220

    return value


def motion_adjustment(
    candidate,
    scene,
):

    st = scene_text(scene)

    action_terms = (
        "movement",
        "moving",
        "walking",
        "running",
        "driving",
        "flying",
        "explosion",
        "fire",
        "crowd",
        "traffic",
        "chase",
        "movimento",
        "correndo",
        "dirigindo",
        "voando",
        "explosao",
        "incendio",
        "multidao",
        "transito",
    )

    action = any(
        norm(term) in st
        for term in action_terms
    )

    t = media_type(candidate)

    if action and t == "video":
        return 12.0

    if action and t == "photo":
        return -5.0

    return 0.0


def score_candidate(
    candidate,
    scene,
    state=None,
):

    st = scene_text(scene)
    ct = candidate_text(candidate)

    stokens = tokens(st)
    ctokens = tokens(ct)

    scon = concept_hits(st)
    ccon = concept_hits(ct)

    sgeo = geo_hits(st)
    cgeo = geo_hits(ct)

    must = must_info(
        candidate,
        scene,
    )

    avoid = avoid_hits(
        candidate,
        scene,
    )

    hard = False
    reasons = []

    semantic = 0.0

    # --------------------------------------------------------
    # TOKEN / CONCEPT RELEVANCE
    # --------------------------------------------------------

    common_tokens = (
        stokens
        &
        ctokens
    )

    common_concepts = (
        scon
        &
        ccon
    )

    semantic += min(
        32,
        len(common_tokens) * 4,
    )

    semantic += (
        len(common_concepts)
        * 20
    )

    # --------------------------------------------------------
    # MUST
    # --------------------------------------------------------

    if must["tier"] == 2:
        semantic += 80

    elif must["tier"] == 1:
        semantic += 35

    else:
        if must["total"]:
            semantic -= 20

    # --------------------------------------------------------
    # GEO
    # --------------------------------------------------------

    geo_bad = geo_conflict(
        sgeo,
        cgeo,
    )

    if geo_bad:

        hard = True

        reasons.append(
            "GEO_CONTRADICTION"
        )

        semantic -= 450

    elif (
        sgeo
        and cgeo
        and (
            sgeo
            &
            cgeo
        )
    ):
        semantic += 35

    # --------------------------------------------------------
    # MEDICINE FALSE ASSOCIATION
    # --------------------------------------------------------

    medicine = term_hits(
        ct,
        MEDICINE_TERMS,
    )

    scene_documentary = bool(
        scon
        &
        DOCUMENTARY_CONCEPTS
    )

    scene_has_medicine = (
        "medicine"
        in scon
    )

    medicine_false = bool(
        medicine
        and scene_documentary
        and not scene_has_medicine
    )

    if medicine_false:

        semantic -= 180

        reasons.append(
            "FALSE_MEDICINE_ASSOCIATION"
        )

        if not common_concepts:
            hard = True

    # --------------------------------------------------------
    # GENERIC LIFESTYLE
    # --------------------------------------------------------

    lifestyle = term_hits(
        ct,
        GENERIC_LIFESTYLE,
    )

    lifestyle_false = bool(
        lifestyle
        and scene_documentary
    )

    if lifestyle_false:

        semantic -= min(
            160,
            45 * len(lifestyle),
        )

        reasons.append(
            "GENERIC_LIFESTYLE"
        )

        if (
            len(lifestyle) >= 2
            and not common_concepts
        ):
            hard = True

    # --------------------------------------------------------
    # ABSTRACT / DECORATIVE
    # --------------------------------------------------------

    abstract = term_hits(
        ct,
        ABSTRACT_TERMS,
    )

    if (
        abstract
        and scene_documentary
        and not common_concepts
    ):
        semantic -= 90

        reasons.append(
            "ABSTRACT_DECORATIVE"
        )

    # --------------------------------------------------------
    # AVOID
    # --------------------------------------------------------

    if avoid:

        semantic -= (
            len(avoid)
            * 75
        )

        reasons.append(
            "AVOID_HIT"
        )

    # --------------------------------------------------------
    # BASE / TECHNICAL / DIVERSITY
    # --------------------------------------------------------

    base = base_score(candidate)

    # Legacy score auxilia, mas não domina
    # semântica e segurança.
    base_component = max(
        -40,
        min(
            65,
            base * 0.28,
        ),
    )

    technical = resolution_bonus(
        candidate
    )

    diversity = diversity_adjustment(
        candidate,
        state,
    )

    motion = motion_adjustment(
        candidate,
        scene,
    )

    effective = (
        semantic
        +
        base_component
        +
        technical
        +
        diversity
        +
        motion
    )

    return {
        "candidate": candidate,

        "provider":
            provider(candidate),

        "source_group":
            source_group(candidate),

        "media_type":
            media_type(candidate),

        "key":
            candidate_key(candidate),

        "base":
            base,

        "base_component":
            base_component,

        "semantic":
            semantic,

        "technical":
            technical,

        "diversity":
            diversity,

        "motion":
            motion,

        "effective":
            effective,

        "must_hits":
            must["hits"],

        "must_total":
            must["total"],

        "must_ratio":
            must["ratio"],

        "must_tier":
            must["tier"],

        "scene_geo":
            sorted(sgeo),

        "candidate_geo":
            sorted(cgeo),

        "geo_mismatch":
            geo_bad,

        "concept_overlap":
            sorted(common_concepts),

        "token_overlap":
            sorted(common_tokens),

        "avoid_hits":
            list(avoid),

        "medicine_false":
            medicine_false,

        "lifestyle_false":
            lifestyle_false,

        "hard_mismatch":
            bool(hard),

        "hard_reasons":
            reasons,
    }


def rank_candidates(
    candidates,
    scene,
    state=None,
):

    scored = [
        score_candidate(
            candidate,
            scene,
            state,
        )
        for candidate in candidates
        if candidate is not None
    ]

    scored.sort(
        key=lambda row: (
            1
            if not row[
                "hard_mismatch"
            ]
            else 0,

            row[
                "must_tier"
            ],

            row[
                "effective"
            ],
        ),
        reverse=True,
    )

    return scored


def choose_best(
    candidates,
    scene,
    reference=None,
    state=None,
):

    ranked = rank_candidates(
        candidates,
        scene,
        state,
    )

    if not ranked:
        return (
            reference,
            ranked,
            {
                "override": False,
                "reason": "EMPTY_POOL",
            },
        )

    best = ranked[0]

    if reference is None:
        return (
            best["candidate"],
            ranked,
            {
                "override": True,
                "reason": "NO_REFERENCE",
            },
        )

    ref = score_candidate(
        reference,
        scene,
        state,
    )

    # Hard mismatch nunca deve vencer
    # uma alternativa não-hard.
    if (
        ref["hard_mismatch"]
        and not best["hard_mismatch"]
    ):
        return (
            best["candidate"],
            ranked,
            {
                "override": True,
                "reason":
                    "REFERENCE_HARD_MISMATCH",
                "before": ref,
                "after": best,
            },
        )

    # Nunca substitui referência segura
    # por candidato hard.
    if (
        not ref["hard_mismatch"]
        and best["hard_mismatch"]
    ):
        return (
            reference,
            ranked,
            {
                "override": False,
                "reason":
                    "BEST_IS_HARD_MISMATCH",
                "before": ref,
                "after": ref,
            },
        )

    # MUST maior pode substituir.
    if (
        best["must_tier"]
        >
        ref["must_tier"]
    ):

        if (
            best["effective"]
            >=
            ref["effective"] - 25
        ):
            return (
                best["candidate"],
                ranked,
                {
                    "override": True,
                    "reason":
                        "BETTER_MUST_TIER",
                    "before": ref,
                    "after": best,
                },
            )

    # Nunca downgrade de MUST.
    if (
        best["must_tier"]
        <
        ref["must_tier"]
    ):
        return (
            reference,
            ranked,
            {
                "override": False,
                "reason":
                    "MUST_DOWNGRADE_BLOCKED",
                "before": ref,
                "after": ref,
            },
        )

    try:
        margin = float(
            os.getenv(
                "SAP_VG4X_MARGIN",
                "8",
            )
        )
    except ValueError:
        margin = 8.0

    if (
        best["effective"]
        >=
        ref["effective"]
        +
        margin
    ):
        return (
            best["candidate"],
            ranked,
            {
                "override": True,
                "reason":
                    "SAME_TIER_QUALITY_GAIN",
                "before": ref,
                "after": best,
            },
        )

    return (
        reference,
        ranked,
        {
            "override": False,
            "reason":
                "REFERENCE_PRESERVED",
            "before": ref,
            "after": ref,
        },
    )
