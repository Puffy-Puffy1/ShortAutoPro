#!/usr/bin/env python3

from vi1000_1_semantic_core import (
    norm,
)

from vi1000_1_query_gate import (
    evaluate_candidate,
    license_allowed,
    technical_pass,
    story_entity_hits,
)

from vi1200_04_real_candidate_adapter import (
    adapt,
)

from vi1200_06_visual_precision import (
    evaluate_visual_precision,
    scene_visual_intents,
)


STRONG_INTENTS = {
    "ELEVATOR",
    "HALLWAY",
    "ROOFTOP",
    "SURVEILLANCE",
    "MEDICATION",
    "WATER_TANK",
}


def canonical_source_group(
    candidate
):
    title = norm(
        candidate.get(
            "title"
        )
    )


    if (
        "elisa lam elevator video"
        in title
    ):
        return (
            "CASE:"
            "ELISA_LAM_ELEVATOR_VIDEO"
        )


    if (
        "hotel cecil la"
        in title
    ):
        return (
            "CASE:"
            "HOTEL_CECIL_FACADE"
        )


    provider = str(
        candidate.get(
            "provider"
        )
        or "UNKNOWN"
    )


    raw = (
        candidate.get(
            "raw_metadata"
        )
        or {}
    )


    identity = (
        raw.get(
            "pageid"
        )
        or
        raw.get(
            "identifier"
        )
        or
        candidate.get(
            "candidate_id"
        )
        or
        candidate.get(
            "title"
        )
    )


    return (
        provider
        + ":"
        + str(
            identity
        )
    )


def source_class(
    candidate
):
    group = canonical_source_group(
        candidate
    )


    if (
        group
        ==
        "CASE:ELISA_LAM_ELEVATOR_VIDEO"
    ):
        return "CASE_ARCHIVE"


    if (
        group
        ==
        "CASE:HOTEL_CECIL_FACADE"
    ):
        return "VERIFIED_LOCATION"


    if candidate.get(
        "generic"
    ):
        return "GENERIC"


    return "CASE_ENTITY"


def direct_evaluation(
    scene,
    candidate,
    entities
):
    truth = evaluate_candidate(
        scene,
        candidate,
        entities
    )


    visual = (
        evaluate_visual_precision(
            scene,
            candidate
        )
    )


    passed = (
        truth[
            "passed"
        ]
        and
        visual[
            "passed"
        ]
    )


    return {
        "passed":
            passed,

        "mode":
            "DIRECT",

        "claim_visualized":
            True,

        "context_label":
            None,

        "truth":
            truth,

        "visual":
            visual,

        "reasons":
            sorted(
                set(
                    truth[
                        "reasons"
                    ]
                    +
                    visual[
                        "reasons"
                    ]
                )
            ),
    }


def contextual_fallback(
    scene,
    candidate,
    entities
):
    role = str(
        scene.get(
            "role"
        )
        or ""
    ).upper()


    intents = scene_visual_intents(
        scene
    )


    cta = bool(
        scene.get(
            "cta"
        )
    )


    ordinary_context = (
        role == "CONTEXT"
        and
        not (
            intents
            &
            STRONG_INTENTS
        )
    )


    inferred_location_context = (
        role == "LOCATION"
        and
        scene.get(
            "factual"
        )
        is not True
        and
        scene.get(
            "location_scope"
        )
        in {
            "SPECIFIC_LOCATION_INFERRED_STORY_CONTEXT",
            "NONE",
        }
        and
        not (
            intents
            &
            STRONG_INTENTS
        )
    )


    final_context = (
        cta
        and
        role
        in {
            "DOCUMENT",
            "CONTEXT",
            "LOCATION",
        }
    )


    if not (
        ordinary_context
        or
        inferred_location_context
        or
        final_context
    ):
        return {
            "passed":
                False,

            "mode":
                "CONTEXT_NOT_ALLOWED",

            "reasons": [
                "contextual_fallback_not_allowed"
            ],
        }


    if not license_allowed(
        candidate.get(
            "license"
        )
    ):
        return {
            "passed":
                False,

            "mode":
                "CONTEXT_NOT_DEPICTING_CLAIM",

            "reasons": [
                "context_license_failed"
            ],
        }


    if not technical_pass(
        candidate
    ):
        return {
            "passed":
                False,

            "mode":
                "CONTEXT_NOT_DEPICTING_CLAIM",

            "reasons": [
                "context_technical_gate_failed"
            ],
        }


    hits = story_entity_hits(
        candidate,
        entities
    )


    if not hits:
        return {
            "passed":
                False,

            "mode":
                "CONTEXT_NOT_DEPICTING_CLAIM",

            "reasons": [
                "context_story_entity_missing"
            ],
        }


    if (
        candidate.get(
            "intended_usage"
        )
        != "CASE_SPECIFIC"
    ):
        return {
            "passed":
                False,

            "mode":
                "CONTEXT_NOT_DEPICTING_CLAIM",

            "reasons": [
                "context_must_be_case_specific"
            ],
        }


    return {
        "passed":
            True,

        "mode":
            (
                "FINAL_CTA_CONTEXT"
                if final_context
                else
                "CONTEXT_NOT_DEPICTING_CLAIM"
            ),

        "claim_visualized":
            False,

        "context_label":
            "IMAGEM DE CONTEXTO",

        "entity_hits":
            hits,

        "reasons":
            [],
    }


def score(
    candidate,
    evaluation
):
    if not evaluation[
        "passed"
    ]:
        return -10000.0


    base = (
        float(
            candidate.get(
                "quality_score",
                0
            )
        )
        * 0.20

        +

        float(
            candidate.get(
                "semantic_score",
                0
            )
        )
        * 0.30

        +

        float(
            candidate.get(
                "provenance_score",
                0
            )
        )
        * 0.30
    )


    if (
        evaluation[
            "mode"
        ]
        == "DIRECT"
    ):

        visual_score = (
            evaluation[
                "visual"
            ][
                "precision_score"
            ]
        )


        base += (
            visual_score
            * 0.20
        )

        base += 20


    else:
        base += 5


    if (
        candidate.get(
            "intended_usage"
        )
        == "CASE_SPECIFIC"
    ):
        base += 12


    return round(
        base,
        2
    )


def evaluate_candidate_record(
    scene,
    candidate,
    entities
):
    direct = direct_evaluation(
        scene,
        candidate,
        entities
    )


    if direct[
        "passed"
    ]:

        final = direct

    else:

        context = contextual_fallback(
            scene,
            candidate,
            entities
        )


        if context[
            "passed"
        ]:

            context[
                "direct_failure_reasons"
            ] = direct[
                "reasons"
            ]

            final = context

        else:

            final = {
                "passed":
                    False,

                "mode":
                    "REJECT",

                "reasons":
                    sorted(
                        set(
                            direct[
                                "reasons"
                            ]
                            +
                            context.get(
                                "reasons",
                                []
                            )
                        )
                    ),

                "direct":
                    direct,

                "context":
                    context,
            }


    candidate[
        "source_group"
    ] = canonical_source_group(
        candidate
    )


    candidate[
        "source_class"
    ] = source_class(
        candidate
    )


    return {
        "candidate":
            candidate,

        "evaluation":
            final,

        "rank":
            score(
                candidate,
                final
            ),
    }


def adapt_and_evaluate(
    raw,
    scene,
    entities,
    query="",
):
    candidate = adapt(
        raw,
        scene,
        entities,
        search_query=query
    )


    return evaluate_candidate_record(
        scene,
        candidate,
        entities
    )


if __name__ == "__main__":
    print(
        "VI1250 CANDIDATE ENGINE=PASS"
    )
