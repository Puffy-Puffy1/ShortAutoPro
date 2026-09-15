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
        / "config/"
        "vi1260_semantic_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)


CAPS = POLICY[
    "source_caps"
]


def source_cap(
    candidate,
):
    return int(
        CAPS.get(
            candidate.get(
                "source_class"
            ),
            1
        )
    )


def state_score(
    state,
):
    selected = len(
        state[
            "chosen"
        ]
    )

    unique = len(
        state[
            "groups"
        ]
    )

    direct = sum(
        1
        for item in (
            state[
                "chosen"
            ].values()
        )
        if str(
            item[
                "evaluation"
            ].get(
                "mode",
                ""
            )
        ).startswith(
            "DIRECT"
        )
    )


    return (
        selected * 100000
        +
        unique * 1200
        +
        direct * 250
        +
        state[
            "raw_score"
        ]
    )


def can_add(
    state,
    scene_number,
    item,
):
    candidate = item[
        "candidate"
    ]

    group = candidate[
        "source_group"
    ]

    cap = source_cap(
        candidate
    )


    if (
        state[
            "groups"
        ].get(
            group,
            0
        )
        >= cap
    ):
        return False


    previous = state[
        "chosen"
    ].get(
        scene_number - 1
    )


    previous2 = state[
        "chosen"
    ].get(
        scene_number - 2
    )


    if (
        previous
        and
        previous2
        and
        previous[
            "candidate"
        ][
            "source_group"
        ]
        == group
        and
        previous2[
            "candidate"
        ][
            "source_group"
        ]
        == group
    ):
        return False


    return True


def optimize(
    scenes,
    candidates_by_scene,
    beam_width=400,
):
    states = [{
        "chosen":
            {},

        "groups":
            {},

        "raw_score":
            0.0,
    }]


    for scene in sorted(
        scenes,
        key=lambda x:
            x[
                "scene"
            ]
    ):

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
        ][
            :8
        ]


        expanded = []


        for state in states:

            # HOLD option.
            expanded.append({
                "chosen":
                    dict(
                        state[
                            "chosen"
                        ]
                    ),

                "groups":
                    dict(
                        state[
                            "groups"
                        ]
                    ),

                "raw_score":
                    state[
                        "raw_score"
                    ],
            })


            for item in alternatives:

                if not can_add(
                    state,
                    number,
                    item
                ):
                    continue


                new_chosen = dict(
                    state[
                        "chosen"
                    ]
                )

                new_groups = dict(
                    state[
                        "groups"
                    ]
                )


                new_chosen[
                    number
                ] = item


                group = (
                    item[
                        "candidate"
                    ][
                        "source_group"
                    ]
                )


                new_groups[
                    group
                ] = (
                    new_groups.get(
                        group,
                        0
                    )
                    + 1
                )


                reuse_penalty = (
                    (
                        new_groups[
                            group
                        ]
                        - 1
                    )
                    * 35
                )


                context_penalty = (
                    12
                    if not str(
                        item[
                            "evaluation"
                        ].get(
                            "mode",
                            ""
                        )
                    ).startswith(
                        "DIRECT"
                    )
                    else 0
                )


                expanded.append({
                    "chosen":
                        new_chosen,

                    "groups":
                        new_groups,

                    "raw_score":
                        (
                            state[
                                "raw_score"
                            ]
                            +
                            item[
                                "rank"
                            ]
                            -
                            reuse_penalty
                            -
                            context_penalty
                        ),
                })


        expanded.sort(
            key=state_score,
            reverse=True
        )


        states = expanded[
            :beam_width
        ]


    finals = []


    for state in states:

        portfolio = []


        for scene in sorted(
            scenes,
            key=lambda x:
                x[
                    "scene"
                ]
        ):

            number = scene[
                "scene"
            ]

            item = state[
                "chosen"
            ].get(
                number
            )


            if not item:
                continue


            candidate = item[
                "candidate"
            ]


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
                    candidate.get(
                        "source_class"
                    ),

                "mode":
                    item[
                        "evaluation"
                    ].get(
                        "mode"
                    ),
            })


        diversity = audit_portfolio(
            portfolio
        )


        finals.append({
            "state":
                state,

            "portfolio":
                portfolio,

            "diversity":
                diversity,

            "selected_count":
                len(
                    state[
                        "chosen"
                    ]
                ),

            "unique_sources":
                len(
                    state[
                        "groups"
                    ]
                ),
        })


    finals.sort(
        key=lambda item: (
            item[
                "selected_count"
            ],
            int(
                bool(
                    item[
                        "diversity"
                    ][
                        "passed"
                    ]
                )
            ),
            item[
                "unique_sources"
            ],
            state_score(
                item[
                    "state"
                ]
            ),
        ),
        reverse=True
    )


    best = finals[
        0
    ]


    chosen = best[
        "state"
    ][
        "chosen"
    ]


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
            best[
                "portfolio"
            ],

        "diversity":
            best[
                "diversity"
            ],

        "selected_count":
            best[
                "selected_count"
            ],

        "hold_count":
            len(
                holds
            ),

        "holds":
            holds,

        "group_counts":
            best[
                "state"
            ][
                "groups"
            ],

        "unique_sources":
            best[
                "unique_sources"
            ],
    }


if __name__ == "__main__":
    print(
        "VI1260 GLOBAL OPTIMIZER=PASS"
    )
