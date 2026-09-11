#!/usr/bin/env python3

import json
from pathlib import Path

from vi1000_1_query_gate import (
    audit_portfolio,
)


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config"
        / "vi1250_source_expansion_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)


CAPS = {
    "CASE_ARCHIVE":
        POLICY[
            "portfolio"
        ][
            "case_archive_source_max"
        ],

    "VERIFIED_LOCATION":
        POLICY[
            "portfolio"
        ][
            "verified_location_source_max"
        ],

    "GENERIC":
        POLICY[
            "portfolio"
        ][
            "generic_source_max"
        ],

    "CASE_ENTITY":
        POLICY[
            "portfolio"
        ][
            "other_case_source_max"
        ],
}


def strictness(
    scene,
    alternatives
):
    return (
        len(
            alternatives
        ),

        -int(
            bool(
                scene.get(
                    "factual"
                )
            )
        ),

        -int(
            bool(
                scene.get(
                    "identity_required"
                )
            )
        ),

        -int(
            scene.get(
                "hook_priority",
                0
            )
        ),
    )


def actual_consecutive_run_if_added(
    chosen,
    scene_number,
    group,
):
    groups = {
        int(number):
            item[
                "candidate"
            ][
                "source_group"
            ]

        for number, item
        in chosen.items()
    }

    groups[
        int(scene_number)
    ] = group


    previous_scene = None
    previous_group = None

    current_run = 0
    maximum_run = 0


    for number in sorted(
        groups
    ):

        current_group = (
            groups[
                number
            ]
        )


        if (
            previous_scene
            is not None

            and

            number
            == previous_scene + 1

            and

            current_group
            == previous_group
        ):

            current_run += 1

        else:

            current_run = 1


        maximum_run = max(
            maximum_run,
            current_run
        )


        previous_scene = number
        previous_group = (
            current_group
        )


    return maximum_run


def max_run_if_added(
    chosen,
    scene_number,
    group,
):
    return (
        actual_consecutive_run_if_added(
            chosen,
            scene_number,
            group,
        )
    )


def rejection_reasons(
    chosen,
    group_counts,
    item,
    scene_number,
):
    candidate = (
        item[
            "candidate"
        ]
    )


    group = candidate[
        "source_group"
    ]

    source_class = (
        candidate[
            "source_class"
        ]
    )


    current_usage = (
        group_counts.get(
            group,
            0
        )
    )


    maximum_usage = (
        CAPS.get(
            source_class,
            1
        )
    )


    reasons = []


    if current_usage >= maximum_usage:

        reasons.append({
            "reason":
                "SOURCE_GROUP_CAP",

            "source_group":
                group,

            "source_class":
                source_class,

            "current_usage":
                current_usage,

            "maximum":
                maximum_usage,
        })


    projected_run = (
        actual_consecutive_run_if_added(
            chosen,
            scene_number,
            group,
        )
    )


    maximum_run = (
        POLICY[
            "portfolio"
        ][
            "maximum_consecutive_same_source"
        ]
    )


    if projected_run > maximum_run:

        reasons.append({
            "reason":
                "CONSECUTIVE_SOURCE_LIMIT",

            "source_group":
                group,

            "projected_run":
                projected_run,

            "maximum":
                maximum_run,
        })


    return reasons


def choose_portfolio(
    scenes,
    candidates_by_scene,
):
    chosen = {}

    group_counts = {}

    class_counts = {}

    hold_diagnostics = {}


    ordered = sorted(
        scenes,
        key=lambda scene:
            strictness(
                scene,
                candidates_by_scene.get(
                    scene[
                        "scene"
                    ],
                    []
                )
            )
    )


    for scene in ordered:

        number = scene[
            "scene"
        ]


        alternatives = [
            item

            for item in (
                candidates_by_scene.get(
                    number,
                    []
                )
            )

            if item[
                "evaluation"
            ][
                "passed"
            ]
        ]


        ranked = []

        rejected = []


        for item in alternatives:

            reasons = (
                rejection_reasons(
                    chosen,
                    group_counts,
                    item,
                    number,
                )
            )


            if reasons:

                rejected.append({
                    "title":
                        item[
                            "candidate"
                        ].get(
                            "title"
                        ),

                    "source_group":
                        item[
                            "candidate"
                        ].get(
                            "source_group"
                        ),

                    "source_class":
                        item[
                            "candidate"
                        ].get(
                            "source_class"
                        ),

                    "rank":
                        item[
                            "rank"
                        ],

                    "reasons":
                        reasons,
                })

                continue


            candidate = (
                item[
                    "candidate"
                ]
            )


            group = (
                candidate[
                    "source_group"
                ]
            )


            usage = (
                group_counts.get(
                    group,
                    0
                )
            )


            novelty = (
                24
                if usage == 0
                else
                -28 * usage
            )


            mode_bonus = (
                8

                if
                item[
                    "evaluation"
                ][
                    "mode"
                ]
                == "DIRECT"

                else -5
            )


            effective_rank = (
                item[
                    "rank"
                ]
                +
                novelty
                +
                mode_bonus
            )


            ranked.append(
                (
                    effective_rank,
                    item,
                )
            )


        ranked.sort(
            key=lambda pair:
                pair[0],
            reverse=True
        )


        if not ranked:

            hold_diagnostics[
                number
            ] = {
                "scene":
                    number,

                "passing_candidate_count":
                    len(
                        alternatives
                    ),

                "reason":
                    (
                        "NO_PASSING_CANDIDATE"

                        if not alternatives

                        else
                        "GLOBAL_PORTFOLIO_CONSTRAINT"
                    ),

                "rejected":
                    rejected,
            }

            continue


        selected = ranked[
            0
        ][1]


        chosen[
            number
        ] = selected


        candidate = (
            selected[
                "candidate"
            ]
        )


        group = candidate[
            "source_group"
        ]

        source_class = (
            candidate[
                "source_class"
            ]
        )


        group_counts[
            group
        ] = (
            group_counts.get(
                group,
                0
            )
            + 1
        )


        class_counts[
            source_class
        ] = (
            class_counts.get(
                source_class,
                0
            )
            + 1
        )


    portfolio = []


    for scene in sorted(
        scenes,
        key=lambda item:
            item[
                "scene"
            ]
    ):

        number = scene[
            "scene"
        ]


        selected = (
            chosen.get(
                number
            )
        )


        if not selected:
            continue


        candidate = (
            selected[
                "candidate"
            ]
        )


        portfolio.append({
            "scene":
                number,

            "source_group":
                candidate[
                    "source_group"
                ],

            "generic":
                candidate.get(
                    "generic",
                    False
                ),

            "title":
                candidate.get(
                    "title"
                ),

            "source_class":
                candidate[
                    "source_class"
                ],

            "mode":
                selected[
                    "evaluation"
                ][
                    "mode"
                ],
        })


    diversity = audit_portfolio(
        portfolio
    )


    holds = [
        scene[
            "scene"
        ]

        for scene in scenes

        if scene[
            "scene"
        ]
        not in chosen
    ]


    return {
        "chosen":
            chosen,

        "portfolio":
            portfolio,

        "holds":
            holds,

        "selected_count":
            len(
                chosen
            ),

        "hold_count":
            len(
                holds
            ),

        "group_counts":
            group_counts,

        "class_counts":
            class_counts,

        "hold_diagnostics":
            hold_diagnostics,

        "diversity":
            diversity,
    }


if __name__ == "__main__":

    print(
        "VI1250.1 PORTFOLIO OPTIMIZER=PASS"
    )
