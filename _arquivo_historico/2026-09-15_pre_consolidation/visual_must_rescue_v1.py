#!/usr/bin/env python3

from visual_selection_engine_v2 import (
    quality_breakdown,
)


def needs_rescue(
    candidate,
    scorer=None,
):
    if not isinstance(
        candidate,
        dict,
    ):
        return False


    info = quality_breakdown(
        candidate,
        scorer,
    )


    total = info[
        "must_total"
    ]


    if total <= 0:
        return False


    return (
        info[
            "tier"
        ]
        <=
        2
    )


def better_than(
    new_candidate,
    old_candidate,
    scorer=None,
):
    if not isinstance(
        new_candidate,
        dict,
    ):
        return False


    if not isinstance(
        old_candidate,
        dict,
    ):
        return True


    new = quality_breakdown(
        new_candidate,
        scorer,
    )


    old = quality_breakdown(
        old_candidate,
        scorer,
    )


    if (
        new[
            "tier"
        ]
        >
        old[
            "tier"
        ]
    ):
        return True


    if (
        new[
            "tier"
        ]
        <
        old[
            "tier"
        ]
    ):
        return False


    if (
        new[
            "avoid_hits"
        ]
        >
        old[
            "avoid_hits"
        ]
    ):
        return False


    if (
        new[
            "mismatch_penalty"
        ]
        >
        old[
            "mismatch_penalty"
        ]
    ):
        return False


    return (
        new[
            "effective_score"
        ]
        >
        old[
            "effective_score"
        ]
        +
        8.0
    )


def summary(
    candidate,
    scorer=None,
):
    if not isinstance(
        candidate,
        dict,
    ):
        return "NONE"


    info = quality_breakdown(
        candidate,
        scorer,
    )


    return (
        f"{candidate.get('fonte', '?')}/"
        f"{candidate.get('tipo', '?')} "
        f"must="
        f"{info['must_hits']}/"
        f"{info['must_total']} "
        f"tier={info['tier']} "
        f"effective="
        f"{info['effective_score']:.1f}"
    )
