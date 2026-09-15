#!/usr/bin/env python3

from vi1000_1_query_gate import (
    license_allowed,
    technical_pass,
    story_entity_hits,
)

from vi1200_04_real_candidate_adapter import (
    adapt,
)

from vi1250_04_candidate_engine import (
    evaluate_candidate_record,
)

from vi1260_01_semantic_roles import (
    scene_requirements,
    candidate_semantics,
)


def safety_basics(
    candidate,
):
    reasons = []


    if not license_allowed(
        candidate.get("license")
    ):
        reasons.append(
            "license_failed"
        )


    if not technical_pass(
        candidate
    ):
        reasons.append(
            "technical_gate_failed"
        )


    if not candidate.get(
        "evidence_text"
    ):
        reasons.append(
            "metadata_evidence_missing"
        )


    if (
        candidate.get(
            "intended_usage"
        )
        == "ILLUSTRATIVE"
        and
        candidate.get(
            "illustration_label"
        )
        is not True
    ):
        reasons.append(
            "illustration_label_missing"
        )


    return reasons


def context_result(
    mode,
    *,
    label,
):
    return {
        "passed":
            True,

        "mode":
            mode,

        "claim_visualized":
            False,

        "overlay_label":
            label,

        "query_used_as_evidence":
            False,

        "reasons":
            [],
    }


def reject(
    reasons,
    semantic=None,
):
    return {
        "passed":
            False,

        "mode":
            "REJECT",

        "claim_visualized":
            False,

        "overlay_label":
            None,

        "query_used_as_evidence":
            False,

        "candidate_semantics":
            semantic or [],

        "reasons":
            sorted(
                set(reasons)
            ),
    }


def evaluate_vi1260(
    scene,
    candidate,
    entities,
):
    requirements = scene_requirements(
        scene,
        entities
    )

    req = set(
        requirements[
            "requirements"
        ]
    )


    semantics = set(
        candidate_semantics(
            candidate,
            entities
        )
    )


    basics = safety_basics(
        candidate
    )


    base = evaluate_candidate_record(
        scene,
        candidate,
        entities
    )


    base_eval = base[
        "evaluation"
    ]


    source_class = (
        base[
            "candidate"
        ].get(
            "source_class"
        )
    )


    story_hits = story_entity_hits(
        candidate,
        entities
    )


    generic = bool(
        candidate.get("generic")
    )


    # --------------------------------------------------
    # MAINTENANCE / STAFF
    # --------------------------------------------------

    if "MAINTENANCE_WORKER" in req:

        if not (
            "MAINTENANCE_WORKER"
            in semantics
            or
            (
                "HOTEL_EMPLOYEE"
                in semantics
                and
                "WORKER"
                in semantics
            )
        ):
            return reject(
                basics
                +
                [
                    "maintenance_worker_visual_required"
                ],
                sorted(semantics)
            )


        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        result = context_result(
            "MAINTENANCE_WORKER_ILLUSTRATION"
            if generic
            else "DIRECT_MAINTENANCE_CONTEXT",

            label=(
                "IMAGEM ILUSTRATIVA"
                if generic
                else "IMAGEM DE CONTEXTO"
            )
        )

        result[
            "candidate_semantics"
        ] = sorted(semantics)

        return result


    # --------------------------------------------------
    # BIPOLAR / MENTAL HEALTH
    # --------------------------------------------------

    if "BIPOLAR" in req:

        if not (
            "BIPOLAR"
            in semantics
            or
            (
                "MENTAL_HEALTH"
                in semantics
                and
                "MEDICAL_CONTEXT"
                in semantics
            )
        ):
            return reject(
                basics
                +
                [
                    "bipolar_or_mental_health_visual_required"
                ],
                sorted(semantics)
            )


        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        result = context_result(
            "MEDICAL_ILLUSTRATION",
            label="IMAGEM ILUSTRATIVA"
        )

        result[
            "candidate_semantics"
        ] = sorted(semantics)

        return result


    # --------------------------------------------------
    # WATER TANK
    # --------------------------------------------------

    if "WATER_TANK" in req:

        if not (
            "WATER_TANK"
            in semantics
            and
            "ROOFTOP"
            in semantics
        ):
            return reject(
                basics
                +
                [
                    "rooftop_water_tank_visual_required"
                ],
                sorted(semantics)
            )


        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        if (
            "VERIFIED_CASE_LOCATION"
            in semantics
            and
            story_hits
        ):
            mode = (
                "DIRECT_CASE_WATER_TANK"
            )

            label = None

            claim_visualized = True

        else:
            mode = (
                "WATER_TANK_ILLUSTRATION"
            )

            label = (
                "IMAGEM ILUSTRATIVA"
            )

            claim_visualized = False


        result = {
            "passed":
                True,

            "mode":
                mode,

            "claim_visualized":
                claim_visualized,

            "overlay_label":
                label,

            "query_used_as_evidence":
                False,

            "candidate_semantics":
                sorted(semantics),

            "reasons":
                [],
        }

        return result


    # --------------------------------------------------
    # SPECIFIC PERSON
    # --------------------------------------------------

    if "SPECIFIC_PERSON" in req:

        if (
            base_eval.get("passed")
            and
            "SPECIFIC_PERSON"
            in semantics
        ):
            result = dict(
                base_eval
            )

            result[
                "mode"
            ] = "DIRECT_SPECIFIC_PERSON"

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            result[
                "query_used_as_evidence"
            ] = False

            return result


        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        # Scene can show the verified story location
        # without pretending it is a portrait.
        if (
            "PRIMARY_LOCATION_MENTIONED"
            in req
            and
            "VERIFIED_CASE_LOCATION"
            in semantics
            and
            story_hits
            and
            source_class
            in {
                "VERIFIED_LOCATION",
                "CASE_ENTITY",
            }
        ):
            result = context_result(
                "CASE_LOCATION_CONTEXT",
                label="IMAGEM DE CONTEXTO"
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            return result


        # A verified case asset linked to the named
        # person can be used as context, but we do not
        # claim it is a portrait.
        if (
            "SPECIFIC_PERSON"
            in semantics
            and
            story_hits
            and
            source_class
            in {
                "CASE_ARCHIVE",
                "CASE_ENTITY",
            }
        ):
            result = context_result(
                "CASE_PERSON_CONTEXT",
                label="IMAGEM DE CONTEXTO"
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            return result


        return reject(
            [
                "specific_person_or_verified_case_context_required"
            ],
            sorted(semantics)
        )


    # --------------------------------------------------
    # ACTION / HIDING
    # --------------------------------------------------

    if "HIDE_BEHAVIOR" in req:

        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        if "HIDE_BEHAVIOR" in semantics:

            result = context_result(
                "ACTION_ILLUSTRATION"
                if generic
                else "CASE_ACTION_CONTEXT",

                label=(
                    "IMAGEM ILUSTRATIVA"
                    if generic
                    else "IMAGEM DE CONTEXTO"
                )
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            return result


        if (
            semantics
            &
            {
                "HALLWAY",
                "ELEVATOR",
                "LOCATION",
                "SURVEILLANCE",
            }
        ):

            result = context_result(
                "ACTION_CONTEXT",
                label=(
                    "IMAGEM ILUSTRATIVA"
                    if generic
                    else "IMAGEM DE CONTEXTO"
                )
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            return result


        return reject(
            [
                "action_context_visual_required"
            ],
            sorted(semantics)
        )


    # --------------------------------------------------
    # DISCUSSION ABOUT EVIDENCE
    # --------------------------------------------------

    if "EVIDENCE_DISCUSSION" in req:

        if base_eval.get("passed"):

            result = dict(
                base_eval
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            result[
                "query_used_as_evidence"
            ] = False

            return result


        if basics:
            return reject(
                basics,
                sorted(semantics)
            )


        if (
            semantics
            &
            {
                "SURVEILLANCE",
                "ELEVATOR",
                "VERIFIED_CASE_LOCATION",
            }
        ):

            result = context_result(
                "EVIDENCE_DISCUSSION_CONTEXT",
                label=(
                    "IMAGEM ILUSTRATIVA"
                    if generic
                    else "IMAGEM DE CONTEXTO"
                )
            )

            result[
                "candidate_semantics"
            ] = sorted(semantics)

            return result


        return reject(
            [
                "evidence_discussion_context_required"
            ],
            sorted(semantics)
        )


    # --------------------------------------------------
    # EXISTING SAFE DIRECT PATH
    # --------------------------------------------------

    if base_eval.get("passed"):

        result = dict(
            base_eval
        )

        result[
            "candidate_semantics"
        ] = sorted(semantics)

        result[
            "query_used_as_evidence"
        ] = False

        return result


    return reject(
        base_eval.get(
            "reasons",
            [
                "base_gate_failed"
            ]
        ),
        sorted(semantics)
    )


def adapt_and_evaluate_vi1260(
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


    # evaluate_candidate_record adds canonical
    # source_group/source_class.
    base = evaluate_candidate_record(
        scene,
        candidate,
        entities
    )

    candidate = base[
        "candidate"
    ]


    evaluation = evaluate_vi1260(
        scene,
        candidate,
        entities
    )


    quality = float(
        candidate.get(
            "quality_score",
            0
        )
    )

    semantic = float(
        candidate.get(
            "semantic_score",
            0
        )
    )

    provenance = float(
        candidate.get(
            "provenance_score",
            0
        )
    )


    mode = evaluation.get(
        "mode",
        "REJECT"
    )


    mode_bonus = {
        "DIRECT":
            30,

        "DIRECT_SPECIFIC_PERSON":
            35,

        "DIRECT_CASE_WATER_TANK":
            35,

        "CASE_PERSON_CONTEXT":
            18,

        "CASE_LOCATION_CONTEXT":
            16,

        "CASE_ACTION_CONTEXT":
            14,

        "EVIDENCE_DISCUSSION_CONTEXT":
            12,

        "ACTION_CONTEXT":
            8,

        "ACTION_ILLUSTRATION":
            5,

        "MEDICAL_ILLUSTRATION":
            10,

        "MAINTENANCE_WORKER_ILLUSTRATION":
            10,

        "DIRECT_MAINTENANCE_CONTEXT":
            15,

        "WATER_TANK_ILLUSTRATION":
            10,
    }.get(
        mode,
        0
    )


    rank = (
        quality * 0.25
        +
        semantic * 0.30
        +
        provenance * 0.30
        +
        mode_bonus
    )


    if not evaluation[
        "passed"
    ]:
        rank = -10000


    return {
        "candidate":
            candidate,

        "evaluation":
            evaluation,

        "rank":
            round(
                rank,
                2
            ),
    }


if __name__ == "__main__":
    print(
        "VI1260 SEMANTIC CANDIDATE GATE=PASS"
    )
